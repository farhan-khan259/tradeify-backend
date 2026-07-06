from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models import User
from app.services.referral import generate_referral_code


def seed_admin(db: Session) -> None:
    """Create a default admin account if no users exist yet."""
    if db.query(User).count() > 0:
        return
    admin = User(
        email=settings.FIRST_ADMIN_EMAIL,
        full_name="Tradeify Admin",
        hashed_password=hash_password(settings.FIRST_ADMIN_PASSWORD),
        is_admin=True,
        referral_code=generate_referral_code(db),
    )
    db.add(admin)
    db.commit()
