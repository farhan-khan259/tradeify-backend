from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import inspect, text

import random
from typing import Dict, List

from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.api.routes import auth, transactions, referrals, admin, bot
from app.services.seed import seed_admin

# In-memory state for demo accounts (persist for process lifetime)
accounts: Dict[str, Dict] = {}
# Active websocket connections per account
ws_connections: Dict[str, List[WebSocket]] = {}


def generate_new_block() -> List[str]:
    block = ["W"] * 7 + ["L"] * 3
    random.shuffle(block)
    return block


def get_or_create_account(account_id: str) -> Dict:
    if account_id not in accounts:
        accounts[account_id] = {
            "balance": 1158.0,
            "total_wins": 0,
            "total_losses": 0,
            "remaining_outcomes": [],
        }
    return accounts[account_id]


def broadcast_update(account_id: str, message: Dict) -> None:
    conns = ws_connections.get(account_id) or []
    for ws in list(conns):
        try:
            # schedule async send to avoid blocking
            import asyncio

            asyncio.create_task(ws.send_json(message))
        except Exception:
            try:
                conns.remove(ws)
            except ValueError:
                pass


def _ensure_runtime_columns() -> None:
    inspector = inspect(engine)

    transaction_columns = {column["name"] for column in inspector.get_columns("transactions")}
    user_columns = {column["name"] for column in inspector.get_columns("users")}

    statements: list[str] = []
    if "screenshot_data" not in transaction_columns:
        statements.append("ALTER TABLE transactions ADD COLUMN screenshot_data TEXT")
    if "account_name" not in transaction_columns:
        statements.append("ALTER TABLE transactions ADD COLUMN account_name VARCHAR(120)")
    if "wallet_address" not in transaction_columns:
        statements.append("ALTER TABLE transactions ADD COLUMN wallet_address VARCHAR(255)")
    if "network" not in transaction_columns:
        statements.append("ALTER TABLE transactions ADD COLUMN network VARCHAR(50)")
    if "password_reset_otp" not in user_columns:
        statements.append("ALTER TABLE users ADD COLUMN password_reset_otp VARCHAR(12)")
    if "password_reset_expires_at" not in user_columns:
        statements.append("ALTER TABLE users ADD COLUMN password_reset_expires_at TIMESTAMP WITH TIME ZONE")

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Demo convenience: auto-create tables and seed an admin on startup.
    # For Supabase, you can instead run db/schema.sql and set AUTO_CREATE_TABLES=false.
    if settings.AUTO_CREATE_TABLES:
        Base.metadata.create_all(bind=engine)
    _ensure_runtime_columns()
    db = SessionLocal()
    try:
        seed_admin(db)
    finally:
        db.close()
    yield


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": settings.PROJECT_NAME}


api = settings.API_V1_PREFIX
app.include_router(auth.router, prefix=api)
app.include_router(transactions.router, prefix=api)
app.include_router(referrals.router, prefix=api)
app.include_router(admin.router, prefix=api)
app.include_router(bot.router, prefix=api)


# Pydantic models for account endpoints
class TradeRequest(BaseModel):
    stake: float


class TradeResponse(BaseModel):
    outcome: str
    profit: float
    new_balance: float


class AccountStatus(BaseModel):
    balance: float
    wins: int
    losses: int
    remaining_trades_in_block: int


@app.post("/accounts/{account_id}/trade", response_model=TradeResponse)
def account_trade(account_id: str, req: TradeRequest):
    acct = get_or_create_account(account_id)
    stake = float(req.stake)
    if stake <= 0:
        raise HTTPException(status_code=400, detail="Stake must be > 0")
    if acct["balance"] < stake:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    # Ensure a block exists
    if not acct["remaining_outcomes"]:
        acct["remaining_outcomes"].extend(generate_new_block())

    outcome = acct["remaining_outcomes"].pop(0)

    if outcome == "W":
        profit = round(stake * 0.90, 2)
        acct["balance"] = round(acct["balance"] + profit, 2)
        acct["total_wins"] += 1
    else:
        profit = round(-stake, 2)
        acct["balance"] = round(acct["balance"] + profit, 2)
        acct["total_losses"] += 1

    # Broadcast to websockets if any
    try:
        broadcast_update(account_id, {"outcome": outcome, "profit": profit, "balance": acct["balance"]})
    except Exception:
        pass

    return TradeResponse(outcome=outcome, profit=profit, new_balance=acct["balance"])


@app.get("/accounts/{account_id}/status", response_model=AccountStatus)
def account_status(account_id: str):
    acct = get_or_create_account(account_id)
    return AccountStatus(
        balance=acct["balance"],
        wins=acct["total_wins"],
        losses=acct["total_losses"],
        remaining_trades_in_block=len(acct["remaining_outcomes"]),
    )


@app.websocket("/ws/{account_id}")
async def websocket_endpoint(websocket: WebSocket, account_id: str):
    await websocket.accept()
    ws_connections.setdefault(account_id, []).append(websocket)
    try:
        while True:
            # keep the connection alive; we don't expect messages from client
            await websocket.receive_text()
    except WebSocketDisconnect:
        try:
            ws_connections[account_id].remove(websocket)
        except Exception:
            pass
