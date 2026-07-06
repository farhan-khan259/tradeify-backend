import random
from collections import deque

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.bot import BotTradeRequest, BotTradeResponse

router = APIRouter(prefix="/bot", tags=["bot"])

WIN_RATE = 0.70
WIN_PAYOUT = 0.85
_OUTCOME_QUEUE: deque[bool] = deque()


def _next_outcome() -> bool:
    if not _OUTCOME_QUEUE:
        outcomes = [True] * 7 + [False] * 3
        random.shuffle(outcomes)
        _OUTCOME_QUEUE.extend(outcomes)
    return _OUTCOME_QUEUE.popleft()


@router.post("/trade", response_model=BotTradeResponse)
def execute_bot_trade(
    payload: BotTradeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    balance = float(user.balance)
    if balance <= 0:
        raise HTTPException(status_code=400, detail="Account balance must be greater than $0 to trade")
    if payload.amount > balance:
        raise HTTPException(status_code=400, detail="Trade amount cannot exceed account balance")

    side = "BUY" if random.random() < 0.5 else "SELL"
    win = _next_outcome()
    delta = payload.amount * WIN_PAYOUT if win else -payload.amount

    user.balance = balance + delta
    db.commit()

    return BotTradeResponse(
        pair=payload.pair,
        side=side,
        amount=payload.amount,
        win=win,
        delta=delta,
        balance=float(user.balance),
    )
