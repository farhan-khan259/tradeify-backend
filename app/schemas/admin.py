from pydantic import BaseModel


class AdminStats(BaseModel):
    total_users: int
    active_users: int
    admin_users: int
    new_users_7d: int

    total_balance: float

    deposits_pending_count: int
    deposits_approved_count: int
    deposits_total_amount: float  # sum of approved deposits

    withdrawals_pending_count: int
    withdrawals_approved_count: int
    withdrawals_total_amount: float  # sum of approved withdrawals

    referral_bonus_total: float
