import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models import User, Referral
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    RegisterRequest,
    ResetPasswordRequest,
    Token,
)
from app.schemas.user import UserPublic
from app.services.referral import generate_referral_code, REFERRAL_BONUS
from app.services.mail import send_password_reset_otp_email

router = APIRouter(prefix="/auth", tags=["auth"])


def _utc_now_matching(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return datetime.utcnow()
    return datetime.now(timezone.utc)


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    referrer: User | None = None
    if payload.referral_code:
        referrer = db.query(User).filter(User.referral_code == payload.referral_code).first()
        if not referrer:
            raise HTTPException(status_code=400, detail="Invalid referral code")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        referral_code=generate_referral_code(db),
        referred_by_id=referrer.id if referrer else None,
    )
    db.add(user)
    db.flush()  # assign user.id

    if referrer:
        referrer.balance = float(referrer.balance) + REFERRAL_BONUS
        db.add(Referral(referrer_id=referrer.id, referred_id=user.id, bonus_amount=REFERRAL_BONUS))

    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2 form uses "username"; we treat it as email.
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserPublic)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    # Always respond the same way so the endpoint can't be used to probe which
    # emails are registered.
    generic = "If an account exists for that email, a password reset OTP has been sent."
    if not user:
        return ForgotPasswordResponse(message=generic)

    otp = f"{secrets.randbelow(1_000_000):06d}"
    user.password_reset_otp = otp
    user.password_reset_expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.PASSWORD_RESET_OTP_EXPIRE_MINUTES
    )
    db.commit()

    try:
        send_password_reset_otp_email(user.email, otp)
    except Exception:
        pass

    return ForgotPasswordResponse(
        message=generic,
        otp=otp if settings.EXPOSE_FORGOT_PASSWORD_OTP else None,
    )


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or OTP")

    if not user.password_reset_otp or not user.password_reset_expires_at:
        raise HTTPException(status_code=400, detail="No password reset request found")
    if user.password_reset_otp != payload.otp:
        raise HTTPException(status_code=400, detail="Invalid email or OTP")
    if user.password_reset_expires_at < _utc_now_matching(user.password_reset_expires_at):
        raise HTTPException(status_code=400, detail="OTP has expired")

    user.hashed_password = hash_password(payload.new_password)
    user.password_reset_otp = None
    user.password_reset_expires_at = None
    db.commit()
