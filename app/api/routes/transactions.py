from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User, Transaction, TransactionType, TransactionStatus
from app.schemas.transaction import TransactionCreate, TransactionPublic

router = APIRouter(prefix="/transactions", tags=["transactions"])

MIN_DEPOSIT = 50
MIN_WITHDRAWAL = 100


@router.get("", response_model=list[TransactionPublic])
def list_my_transactions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Transaction)
        .filter(Transaction.user_id == user.id)
        .order_by(Transaction.created_at.desc())
        .all()
    )


@router.post("/deposit", response_model=TransactionPublic, status_code=201)
def request_deposit(
    payload: TransactionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.amount < MIN_DEPOSIT:
        raise HTTPException(status_code=400, detail=f"Minimum deposit is ${MIN_DEPOSIT}")

    if not payload.note or not payload.note.strip():
        raise HTTPException(status_code=400, detail="Transaction reference or note is required")

    if not payload.screenshot_data or not payload.screenshot_data.strip():
        raise HTTPException(status_code=400, detail="Upload the payment screenshot")

    # Demo deposits are recorded as pending and credited only on admin approval.
    tx = Transaction(
        user_id=user.id,
        type=TransactionType.deposit,
        status=TransactionStatus.pending,
        amount=payload.amount,
        note=payload.note,
        screenshot_data=payload.screenshot_data,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


@router.post("/withdraw", response_model=TransactionPublic, status_code=201)
def request_withdrawal(
    payload: TransactionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.amount < MIN_WITHDRAWAL:
        raise HTTPException(status_code=400, detail=f"Minimum withdrawal is ${MIN_WITHDRAWAL}")
    if not payload.account_name:
        raise HTTPException(status_code=400, detail="Please select the account name")
    if not payload.wallet_address:
        raise HTTPException(status_code=400, detail="Please enter your wallet address")
    if not payload.network:
        raise HTTPException(status_code=400, detail="Please choose the network/chain")
    if payload.amount > float(user.balance):
        raise HTTPException(status_code=400, detail="Insufficient balance")

    # Reserve funds immediately so a user can't double-spend pending withdrawals.
    user.balance = float(user.balance) - payload.amount
    tx = Transaction(
        user_id=user.id,
        type=TransactionType.withdrawal,
        status=TransactionStatus.pending,
        amount=payload.amount,
        note=payload.note,
        account_name=payload.account_name,
        wallet_address=payload.wallet_address,
        network=payload.network,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx
