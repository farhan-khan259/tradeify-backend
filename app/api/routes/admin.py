from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.database import get_db
from app.models import User, Transaction, TransactionType, TransactionStatus, Referral
from app.schemas.admin import AdminStats
from app.schemas.transaction import TransactionPublic, TransactionResolve
from app.schemas.user import UserAdminView

router = APIRouter(prefix="/admin", tags=["admin"])


def _sum(db: Session, type_: TransactionType, status: TransactionStatus) -> float:
    val = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(Transaction.type == type_, Transaction.status == status)
        .scalar()
    )
    return float(val or 0)


def _count(db: Session, type_: TransactionType, status: TransactionStatus) -> int:
    return (
        db.query(func.count(Transaction.id))
        .filter(Transaction.type == type_, Transaction.status == status)
        .scalar()
    )


@router.get("/stats", response_model=AdminStats)
def stats(_: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    return AdminStats(
        total_users=db.query(func.count(User.id)).scalar(),
        active_users=db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar(),
        admin_users=db.query(func.count(User.id)).filter(User.is_admin.is_(True)).scalar(),
        new_users_7d=db.query(func.count(User.id)).filter(User.created_at >= week_ago).scalar(),
        total_balance=float(db.query(func.coalesce(func.sum(User.balance), 0)).scalar() or 0),
        deposits_pending_count=_count(db, TransactionType.deposit, TransactionStatus.pending),
        deposits_approved_count=_count(db, TransactionType.deposit, TransactionStatus.approved),
        deposits_total_amount=_sum(db, TransactionType.deposit, TransactionStatus.approved),
        withdrawals_pending_count=_count(db, TransactionType.withdrawal, TransactionStatus.pending),
        withdrawals_approved_count=_count(db, TransactionType.withdrawal, TransactionStatus.approved),
        withdrawals_total_amount=_sum(db, TransactionType.withdrawal, TransactionStatus.approved),
        referral_bonus_total=float(
            db.query(func.coalesce(func.sum(Referral.bonus_amount), 0)).scalar() or 0
        ),
    )


@router.get("/users", response_model=list[UserAdminView])
def list_users(_: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.get("/transactions", response_model=list[TransactionPublic])
def list_transactions(
    status_filter: TransactionStatus | None = None,
    type_filter: TransactionType | None = None,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    q = db.query(Transaction)
    if status_filter:
        q = q.filter(Transaction.status == status_filter)
    if type_filter:
        q = q.filter(Transaction.type == type_filter)
    return q.order_by(Transaction.created_at.desc()).all()


@router.post("/transactions/{tx_id}/resolve", response_model=TransactionPublic)
def resolve_transaction(
    tx_id: int,
    payload: TransactionResolve,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if payload.status not in (TransactionStatus.approved, TransactionStatus.rejected):
        raise HTTPException(status_code=400, detail="Status must be approved or rejected")

    tx = db.get(Transaction, tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if tx.status != TransactionStatus.pending:
        raise HTTPException(status_code=400, detail="Transaction already resolved")

    user = db.get(User, tx.user_id)

    if payload.status == TransactionStatus.approved:
        if tx.type == TransactionType.deposit:
            user.balance = float(user.balance) + float(tx.amount)
        # Withdrawals already debited the balance at request time.
    else:  # rejected
        if tx.type == TransactionType.withdrawal:
            # Refund the reserved amount.
            user.balance = float(user.balance) + float(tx.amount)

    tx.status = payload.status
    tx.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(tx)
    return tx
