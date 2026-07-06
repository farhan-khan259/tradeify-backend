import random
from collections import deque

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.bot import BotTradeRequest, BotTradeResponse

router = APIRouter(prefix="/bot", tags=["bot"])

WIN_PROFIT_RATE = 1.90
_user_outcome_queues: dict[int, deque[bool]] = {}
_pending_trades: dict[int, float] = {}


def _next_outcome(user_id: int) -> bool:
    queue = _user_outcome_queues.setdefault(user_id, deque())
    if not queue:
        outcomes = [True] * 7 + [False] * 3
        random.shuffle(outcomes)
        queue.extend(outcomes)
    return queue.popleft()


def compute_trade_delta(amount: float, win: bool) -> float:
    if win:
        return round(amount * WIN_PROFIT_RATE, 2)
    return round(-amount, 2)


@router.post("/trade", response_model=BotTradeResponse)
def execute_bot_trade(
    payload: BotTradeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    balance = float(user.balance)
    if payload.phase not in {"start", "settle"}:
        raise HTTPException(status_code=400, detail="Invalid phase")

    side = "BUY" if random.random() < 0.5 else "SELL"

    if payload.phase == "start":
        if payload.amount <= 0:
            raise HTTPException(status_code=400, detail="Stake must be greater than 0")
        if payload.amount > balance:
            raise HTTPException(status_code=400, detail="Trade amount cannot exceed account balance")
        if user.id in _pending_trades:
            raise HTTPException(status_code=400, detail="A trade is already pending")

        user.balance = round(balance - payload.amount, 2)
        _pending_trades[user.id] = payload.amount
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

    pending_amount = _pending_trades.pop(user.id, None)
    if pending_amount is None:
        raise HTTPException(status_code=400, detail="No pending trade to settle")

    win = _next_outcome(user.id)
    delta = compute_trade_delta(pending_amount, win)
    if win:
        user.balance = round(balance + pending_amount + delta, 2)
    else:
        user.balance = round(balance, 2)
    db.commit()

    return BotTradeResponse(
        pair=payload.pair,
        side=side,
        amount=pending_amount,
        win=win,
        delta=delta,
        balance=float(user.balance),
        message="Trade settled",
    )
