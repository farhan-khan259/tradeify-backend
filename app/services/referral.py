import secrets
import string

from sqlalchemy.orm import Session

from app.models import User

_ALPHABET = string.ascii_uppercase + string.digits

# Demo-only bonus credited (in simulated balance) to a referrer when someone signs up.
REFERRAL_BONUS = 25.0


def generate_referral_code(db: Session, length: int = 8) -> str:
    """Generate a unique referral code not already present in the users table."""
    for _ in range(20):
        code = "".join(secrets.choice(_ALPHABET) for _ in range(length))
        if not db.query(User).filter(User.referral_code == code).first():
            return code
    raise RuntimeError("Could not generate a unique referral code")
