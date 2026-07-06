from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.api.routes import auth, transactions, referrals, admin, bot
from app.services.seed import seed_admin


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
    allow_origins=settings.cors_origins,
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
