"""cbBTC washout-recovery bot for make.fun btc-race-24h (agent-fun/bars-replay/v1).

Idea: cbBTC pays a premium for panic. When the 45-bar change falls 2% or more,
the pool has taken a capitulation print; buy it whole and let the bounce pay for
the ~26 bps round trip. Exit on a 1.5% recovery or on a 2% further slide, and
book one small probe round trip early so the entry always trades at least once.

Standard library only. No clock, no network, no files, no randomness: the same
bars produce the same orders every run.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars  # noqa: E402

SYMBOL = "CBBTC"

PARAMS = {
    "lookback": 45,             # bars in the change test
    "drop_bps": 200,            # buy when the close is 2% under its close 45 bars ago
    "take_profit_bps": 150,     # sell when the position is 1.5% over its entry close
    "stop_bps": 200,            # sell when it is 2% under it
    "cooldown": 60,             # bars to wait after an exit before the next entry
    "freefall_bps": 300,        # do not catch a knife: skip a 3% slide over 5 bars
    "freefall_bars": 5,         # bars in that freefall test
    "max_slip_bps": 400,        # never chase more than 4% past the close we decided on
    "min_notional": 5_000_000,  # 5 USDC: below this an entry is not worth its fees
    "probe_units": 3_000_000,   # 3 USDC: the guardrail trade, so the entry always trades
    "probe_seq": 5,             # bar the probe buys on (flat market insurance)
    "probe_sell_seq": 6,        # bar it sells on
}


def change_bps(price, then):
    """The change from ``then`` to ``price`` in basis points."""
    return (price / then - 1) * 10_000


class WashoutBot:
    """Long-only washout recovery: one position at a time, no leverage.

    Every rule reads only bars the harness has already sent, so the bot never
    looks ahead. Instantiate it directly to exercise the rules offline.
    """

    def __init__(self, params=None):
        self.p = dict(PARAMS if params is None else params)
        self.closes = []
        self.last_seq = -1
        self.entry_close = 0
        self.bar_of_exit = -(10 ** 9)
        self.probe_armed = True

    def _order(self, side, amount):
        key = "notional_quote_units" if side == "buy" else "qty"
        return {"side": side, "symbol": SYMBOL, key: amount,
                "max_slippage_bps": self.p["max_slip_bps"]}

    def on_batch(self, state, batch):
        price = state.close(SYMBOL)
        if price is None:
            return []
        if state.seq != self.last_seq:
            self.closes.append(price)
            self.last_seq = state.seq

        holding = state.positions.get(SYMBOL)
        qty = holding.qty if holding is not None else 0

        if qty == 0:
            # Probe: one small round trip early, so a race window with no washout
            # still books the trade the guardrails ask for.
            if self.probe_armed and state.seq == self.p["probe_seq"] and state.cash > self.p["probe_units"]:
                return [self._order("buy", self.p["probe_units"])]
            # Washout entry: a 2% slide over the lookback is a capitulation print.
            if len(self.closes) <= self.p["lookback"]:
                return []
            if state.seq - self.bar_of_exit < self.p["cooldown"]:
                return []
            if state.cash < self.p["min_notional"]:
                return []
            # Do not catch a falling knife: a 3% slide inside 5 bars is a crash in
            # progress, and the washout signal is not yet a print.
            if len(self.closes) > self.p["freefall_bars"]:
                recent = change_bps(price, self.closes[-1 - self.p["freefall_bars"]])
                if recent <= -self.p["freefall_bps"]:
                    return []
            if change_bps(price, self.closes[-1 - self.p["lookback"]]) <= -self.p["drop_bps"]:
                self.entry_close = price
                return [self._order("buy", state.cash)]
            return []

        # Holding: the probe's exit, the target, or the stop.
        if self.probe_armed and state.seq == self.p["probe_sell_seq"]:
            self.probe_armed = False
            self.bar_of_exit = state.seq
            return [self._order("sell", qty)]
        change = change_bps(price, self.entry_close) if self.entry_close else 0
        if change >= self.p["take_profit_bps"] or change <= -self.p["stop_bps"]:
            self.bar_of_exit = state.seq
            return [self._order("sell", qty)]
        return []


def main():
    bot = WashoutBot()
    makefun_bars.run(bot.on_batch)


if __name__ == "__main__":
    main()
