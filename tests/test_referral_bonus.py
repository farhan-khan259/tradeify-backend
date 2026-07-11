import unittest

from app.services.referral import REFERRAL_BONUS, MIN_REFERRAL_DEPOSIT, should_credit_referral_bonus


class TestReferralBonus(unittest.TestCase):
    def test_referral_bonus_amount_is_5_dollars(self):
        self.assertEqual(REFERRAL_BONUS, 5.0)

    def test_bonus_requires_a_50_dollar_minimum_deposit(self):
        self.assertTrue(should_credit_referral_bonus(MIN_REFERRAL_DEPOSIT))
        self.assertTrue(should_credit_referral_bonus(100.0))
        self.assertFalse(should_credit_referral_bonus(49.99))
        self.assertFalse(should_credit_referral_bonus(0.0))


if __name__ == "__main__":
    unittest.main()
