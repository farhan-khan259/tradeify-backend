#!/usr/bin/env python3
"""
Comprehensive tests for the Trading Engine
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.trading_engine import TradingEngine, TradeSignal


class TestTradingEngine(unittest.TestCase):
    """Test cases for TradingEngine"""

    def setUp(self):
        """Set up test fixtures"""
        self.engine = TradingEngine()

    def test_engine_initialization(self):
        """Test that engine initializes correctly"""
        self.assertFalse(self.engine.is_running)
        self.assertIsNone(self.engine.current_session)
        self.assertEqual(len(self.engine.trades_history), 0)

    def test_start_session(self):
        """Test starting a trading session"""
        session = self.engine.start_session(pair="BTC/USDT", timeframe="1M", initial_balance=200.0)
        
        self.assertTrue(self.engine.is_running)
        self.assertIsNotNone(self.engine.current_session)
        self.assertEqual(session["pair"], "BTC/USDT")
        self.assertEqual(session["timeframe"], "1M")
        self.assertEqual(session["initial_balance"], 200.0)
        self.assertEqual(session["current_balance"], 200.0)
        self.assertEqual(session["total_wins"], 0)
        self.assertEqual(session["total_losses"], 0)

    def test_execute_trade_win(self):
        """Test executing a winning trade"""
        self.engine.start_session(pair="BTC/USDT", initial_balance=200.0)
        
        # Mock win condition
        self.engine.current_session["total_wins"] = 0
        self.engine.current_session["total_losses"] = 0
        
        result = self.engine.execute_trade(pair="BTC/USDT", amount=20.0, direction="BUY")
        
        self.assertIn("is_win", result)
        self.assertIn("profit", result)
        self.assertIn("new_balance", result)
        self.assertGreater(result["new_balance"], 0)

    def test_execute_trade_without_session(self):
        """Test that trading without session raises error"""
        with self.assertRaises(RuntimeError):
            self.engine.execute_trade(pair="BTC/USDT", amount=20.0, direction="BUY")

    def test_end_session(self):
        """Test ending a trading session"""
        self.engine.start_session(pair="BTC/USDT", initial_balance=200.0)
        self.engine.execute_trade(pair="BTC/USDT", amount=20.0, direction="BUY")
        
        summary = self.engine.end_session()
        
        self.assertFalse(self.engine.is_running)
        self.assertIsNone(self.engine.current_session)
        self.assertIn("total_trades", summary)
        self.assertIn("wins", summary)
        self.assertIn("losses", summary)
        self.assertIn("win_rate", summary)
        self.assertIn("duration", summary)

    def test_multiple_trades(self):
        """Test executing multiple trades in a session"""
        self.engine.start_session(pair="BTC/USDT", initial_balance=200.0)
        
        num_trades = 5
        for _ in range(num_trades):
            result = self.engine.execute_trade(pair="BTC/USDT", amount=10.0, direction="BUY")
            self.assertIn("is_win", result)
        
        self.assertEqual(len(self.engine.current_session["trades"]), num_trades)
        total_trades = (self.engine.current_session["total_wins"] + 
                       self.engine.current_session["total_losses"])
        self.assertEqual(total_trades, num_trades)

    def test_market_structure_analysis(self):
        """Test market structure analysis"""
        structures = self.engine.analyze_market_structure("BTC/USDT")
        
        self.assertIn("structures", structures)
        self.assertIsInstance(structures["structures"], list)

    def test_order_book_analysis(self):
        """Test order book analysis"""
        order_book = self.engine.analyze_order_book("BTC/USDT")
        
        self.assertIn("buy_wall", order_book)
        self.assertIn("sell_wall", order_book)
        self.assertIn("bid_ask_ratio", order_book)
        self.assertGreater(order_book["bid_ask_ratio"], 0)

    def test_technical_patterns(self):
        """Test technical pattern detection"""
        patterns = self.engine.detect_technical_patterns("BTC/USDT")
        
        self.assertIsInstance(patterns, list)
        self.assertGreaterEqual(len(patterns), 0)

    def test_smart_money_flow_analysis(self):
        """Test smart money flow analysis"""
        smart_money = self.engine.analyze_smart_money_flow()
        
        self.assertIn("signals", smart_money)
        self.assertIsInstance(smart_money["signals"], list)

    def test_sentiment_indicators(self):
        """Test sentiment indicator analysis"""
        sentiment = self.engine.analyze_sentiment_indicators()
        
        self.assertIn("sentiment", sentiment)
        self.assertIn("analysis", sentiment)
        self.assertIn(sentiment["sentiment"], ["bullish", "bearish", "neutral"])

    def test_trading_signal_generation(self):
        """Test trading signal generation"""
        signal, direction, confidence = self.engine.generate_trading_signal("BTC/USDT", "1M")
        
        self.assertIsInstance(signal, TradeSignal)
        self.assertIn(direction, ["BUY", "SELL"])
        self.assertGreater(confidence, 0)
        self.assertLessEqual(confidence, 1.0)

    def test_status_when_idle(self):
        """Test status reporting when idle"""
        status = self.engine.get_status()
        
        self.assertEqual(status["status"], "idle")

    def test_status_when_running(self):
        """Test status reporting when running"""
        self.engine.start_session(pair="BTC/USDT", initial_balance=200.0)
        status = self.engine.get_status()
        
        self.assertEqual(status["status"], "running")
        self.assertEqual(status["pair"], "BTC/USDT")
        self.assertEqual(status["balance"], 200.0)

    def test_analysis_logging(self):
        """Test that analysis logging works"""
        self.engine.log_analysis("Test message")
        
        self.assertGreater(len(self.engine.analysis_logs), 0)
        self.assertIn("Test message", self.engine.analysis_logs[-1])

    def test_session_profit_calculation(self):
        """Test that profit/loss is calculated correctly"""
        self.engine.start_session(pair="BTC/USDT", initial_balance=100.0)
        initial_balance = 100.0
        
        self.engine.execute_trade(pair="BTC/USDT", amount=10.0, direction="BUY")
        
        summary = self.engine.end_session()
        
        # Profit/loss should be difference between ending and starting balance
        expected_pl = summary["ending_balance"] - initial_balance
        self.assertEqual(summary["profit_loss"], expected_pl)

    def test_win_rate_calculation(self):
        """Test win rate calculation"""
        self.engine.start_session(pair="BTC/USDT", initial_balance=200.0)
        
        # Execute trades
        for _ in range(10):
            self.engine.execute_trade(pair="BTC/USDT", amount=5.0, direction="BUY")
        
        total_trades = (self.engine.current_session["total_wins"] + 
                       self.engine.current_session["total_losses"])
        
        expected_win_rate = (self.engine.current_session["total_wins"] / total_trades * 100) if total_trades > 0 else 0
        self.assertEqual(self.engine.current_session["win_rate"], expected_win_rate)


class TestTradeSignal(unittest.TestCase):
    """Test TradeSignal enum"""

    def test_signal_values(self):
        """Test that all signal types are defined"""
        self.assertEqual(TradeSignal.BREAKOUT.value, "BREAKOUT")
        self.assertEqual(TradeSignal.STOP_HUNT.value, "STOP_HUNT")
        self.assertEqual(TradeSignal.BULLISH.value, "BULLISH")
        self.assertEqual(TradeSignal.BEARISH.value, "BEARISH")
        self.assertEqual(TradeSignal.NEUTRAL.value, "NEUTRAL")


if __name__ == "__main__":
    unittest.main()
