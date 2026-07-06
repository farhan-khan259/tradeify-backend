import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.api.routes.bot import compute_trade_delta, WIN_PROFIT_RATE


class BotTradeTests(unittest.TestCase):
    def test_compute_trade_delta_win_returns_190_percent_profit(self) -> None:
        amount = 10.0
        delta = compute_trade_delta(amount, win=True)

        self.assertEqual(delta, amount * WIN_PROFIT_RATE)
        self.assertEqual(delta, 19.0)

    def test_compute_trade_delta_loss_returns_full_stake(self) -> None:
        amount = 10.0
        delta = compute_trade_delta(amount, win=False)

        self.assertEqual(delta, -amount)


if __name__ == "__main__":
    unittest.main()
