from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User, Referral

router = APIRouter(prefix="/referrals", tags=["referrals"])


class ReferredUser(BaseModel):
    full_name: str
    email: str
    bonus_amount: float


class ReferralSummary(BaseModel):
    referral_code: str
    total_referrals: int
    total_bonus: float
    referred_users: list[ReferredUser]


@router.get("", response_model=ReferralSummary)
def my_referrals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Referral, User)
        .join(User, User.id == Referral.referred_id)
        .filter(Referral.referrer_id == user.id)
        .all()
    )
    referred = [
        ReferredUser(full_name=u.full_name, email=u.email, bonus_amount=float(r.bonus_amount))
        for r, u in rows
    ]
    return ReferralSummary(
        referral_code=user.referral_code,
        total_referrals=len(referred),
        total_bonus=sum(x.bonus_amount for x in referred),
        referred_users=referred,
    )
