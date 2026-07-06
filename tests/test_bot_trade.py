import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.api.routes.bot import compute_trade_delta, WIN_PAYOUT


class BotTradeTests(unittest.TestCase):
    def test_compute_trade_delta_win_returns_ninety_percent(self) -> None:
        amount = 10.0
        delta = compute_trade_delta(amount, win=True)

        self.assertEqual(delta, amount * WIN_PAYOUT)
        self.assertEqual(delta, 9.0)

    def test_compute_trade_delta_loss_returns_full_stake(self) -> None:
        amount = 10.0
        delta = compute_trade_delta(amount, win=False)

        self.assertEqual(delta, -amount)


if __name__ == "__main__":
    unittest.main()
