"""Offline unit tests for the washout bot's rules (no harness needed).

Run: python3 -m unittest discover -s tests
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402


class StubState:
    """The slice of BarsState the rules read."""

    def __init__(self, seq, price, cash=1_000_000_000, qty=0):
        self.seq = seq
        self._price = price
        self.cash = cash
        self.positions = {}
        if qty:
            self.positions[main.SYMBOL] = main.makefun_bars.Holding(qty, 0)

    def close(self, symbol):
        return self._price if symbol == main.SYMBOL else None


def seed(bot, prices):
    """Feed closes the way the harness would, one per bar."""
    for i, price in enumerate(prices):
        bot.closes.append(price)
        bot.last_seq = i
        st = StubState(i, price)
        bot.on_batch(st, {})


class WashoutTests(unittest.TestCase):
    def test_needs_lookback_history(self):
        bot = main.WashoutBot()
        st = StubState(0, 100_000_000)
        self.assertEqual(bot.on_batch(st, {}), [])

    def test_no_entry_on_a_small_dip(self):
        bot = main.WashoutBot()
        seed(bot, [100_000_000] * 45 + [99_000_000])  # -1%, under the 2% trigger
        self.assertEqual(bot.on_batch(StubState(45, 99_000_000), {}), [])

    def test_entry_on_a_washout(self):
        bot = main.WashoutBot()
        seed(bot, [100_000_000] * 45 + [98_000_000])  # -2%
        orders = bot.on_batch(StubState(45, 98_000_000), {})
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0]["side"], "buy")
        self.assertEqual(orders[0]["notional_quote_units"], 1_000_000_000)

    def test_freefall_guard_skips_a_crash(self):
        bot = main.WashoutBot()
        seed(bot, [110_000_000] * 45 + [106_700_000])  # -3% inside 5 bars, -3% over 45
        self.assertEqual(bot.on_batch(StubState(45, 106_700_000), {}), [])

    def test_take_profit(self):
        bot = main.WashoutBot()
        bot.entry_close = 100_000_000
        st = StubState(50, 101_600_000, qty=1_000)  # +1.6%, past the +1.5% target
        orders = bot.on_batch(st, {})
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0]["side"], "sell")

    def test_stop(self):
        bot = main.WashoutBot()
        bot.entry_close = 100_000_000
        st = StubState(50, 97_900_000, qty=1_000)  # -2.1%, past the -2% stop
        orders = bot.on_batch(st, {})
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0]["side"], "sell")

    def test_hold_inside_the_band(self):
        bot = main.WashoutBot()
        bot.entry_close = 100_000_000
        st = StubState(50, 100_500_000, qty=1_000)  # +0.5%, neither exit
        self.assertEqual(bot.on_batch(st, {}), [])

    def test_probe_round_trip(self):
        bot = main.WashoutBot()
        buy = bot.on_batch(StubState(main.PARAMS["probe_seq"], 100_000_000), {})
        self.assertEqual(len(buy), 1)
        self.assertEqual(buy[0]["side"], "buy")
        self.assertEqual(buy[0]["notional_quote_units"], main.PARAMS["probe_units"])
        sell = bot.on_batch(StubState(main.PARAMS["probe_sell_seq"], 100_000_000, qty=1_000), {})
        self.assertEqual(len(sell), 1)
        self.assertEqual(sell[0]["side"], "sell")
        self.assertFalse(bot.probe_armed)


if __name__ == "__main__":
    unittest.main()
