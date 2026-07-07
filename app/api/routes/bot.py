import random
from collections import deque
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.bot import BotTradeRequest, BotTradeResponse
from app.services.trading_engine import trading_engine

router = APIRouter(prefix="/bot", tags=["bot"])

WIN_PROFIT_RATE = 1.90
_user_sessions: dict[int, dict] = {}
_user_pending_trades: dict[int, dict] = {}


def compute_trade_delta(amount: float, win: bool) -> float:
    """Calculate trade delta (profit/loss)"""
    if win:
        # Return the payout: original stake + 90% profit = 190% of stake
        return round(amount * WIN_PROFIT_RATE, 2)
    return round(-amount, 2)


@router.post("/trade/start")
def start_bot_session(
    pair: str = "BTC/USDT",
    timeframe: str = "1M",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start a new trading session"""
    if user.id in _user_sessions:
        raise HTTPException(status_code=400, detail="Session already active")
    
    balance = float(user.balance)
    session = trading_engine.start_session(pair=pair, timeframe=timeframe, initial_balance=balance)
    
    _user_sessions[user.id] = {
        "pair": pair,
        "timeframe": timeframe,
        "initial_balance": balance,
        "started_at": session["start_time"].isoformat()
    }
    
    return {
        "status": "started",
        "pair": pair,
        "timeframe": timeframe,
        "balance": balance,
        "logs": trading_engine.analysis_logs[-5:] if trading_engine.analysis_logs else []
    }


@router.post("/trade", response_model=BotTradeResponse)
def execute_bot_trade(
    payload: BotTradeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Execute a bot trade (start or settle phase)"""
    balance = float(user.balance)
    
    if payload.phase not in {"start", "settle"}:
        raise HTTPException(status_code=400, detail="Invalid phase")

    side = "BUY" if random.random() < 0.5 else "SELL"

    if payload.phase == "start":
        if payload.amount <= 0:
            raise HTTPException(status_code=400, detail="Stake must be greater than 0")
        if payload.amount > balance:
            raise HTTPException(status_code=400, detail="Trade amount cannot exceed account balance")
        if user.id in _user_pending_trades:
            raise HTTPException(status_code=400, detail="A trade is already pending")

        # Reserve the stake
        user.balance = round(balance - payload.amount, 2)
        _user_pending_trades[user.id] = {
            "amount": payload.amount,
            "pair": payload.pair,
            "side": side
        }
        db.commit()

        return BotTradeResponse(
            pair=payload.pair,
            side=side,
            amount=payload.amount,
            win=False,
            delta=0.0,
            balance=float(user.balance),
            message="Trade started and stake reserved",
        )

    # Settle phase
    pending_trade = _user_pending_trades.pop(user.id, None)
    if pending_trade is None:
        raise HTTPException(status_code=400, detail="No pending trade to settle")

    # Execute trade through trading engine if session active
    try:
        if user.id in _user_sessions:
            result = trading_engine.execute_trade(
                pair=pending_trade["pair"],
                amount=pending_trade["amount"],
                direction=pending_trade["side"]
            )
            win = result["is_win"]
            new_balance = result["new_balance"]
        else:
            # Fallback to simple random outcome
            win = random.random() < 0.7
            delta = compute_trade_delta(pending_trade["amount"], win)
            if win:
                new_balance = round(balance + delta, 2)
            else:
                new_balance = round(balance, 2)
    except RuntimeError:
        # No active session, use simple logic
        win = random.random() < 0.7
        delta = compute_trade_delta(pending_trade["amount"], win)
        if win:
            new_balance = round(balance + delta, 2)
        else:
            new_balance = round(balance, 2)

    delta = compute_trade_delta(pending_trade["amount"], win)
    user.balance = new_balance
    db.commit()

    return BotTradeResponse(
        pair=pending_trade["pair"],
        side=pending_trade["side"],
        amount=pending_trade["amount"],
        win=win,
        delta=delta,
        balance=new_balance,
        message="Trade settled",
    )


@router.get("/trade/status")
def get_trade_status(
    user: User = Depends(get_current_user),
):
    """Get current trading status"""
    status = trading_engine.get_status()
    
    return {
        "status": status.get("status", "idle"),
        "pair": status.get("pair"),
        "balance": status.get("balance"),
        "wins": status.get("wins", 0),
        "losses": status.get("losses", 0),
        "win_rate": status.get("win_rate", 0),
        "trades_count": status.get("trades_count", 0),
        "recent_logs": trading_engine.analysis_logs[-10:] if trading_engine.analysis_logs else []
    }


@router.post("/trade/end")
def end_bot_session(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """End the current trading session"""
    if user.id not in _user_sessions:
        raise HTTPException(status_code=400, detail="No active session")
    
    try:
        summary = trading_engine.end_session()
        _user_sessions.pop(user.id, None)
        
        # Update user balance with final session balance
        user.balance = summary["ending_balance"]
        db.commit()
        
        return {
            "status": "ended",
            "summary": summary,
            "logs": trading_engine.analysis_logs
        }
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
