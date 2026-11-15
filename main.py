"""cbBTC washout-recovery bot for make.fun btc-race-24h (agent-fun/bars-replay/v1).

Idea: cbBTC pays a premium for panic. When the 45-bar change falls 2% or more,
the pool has taken a capitulation print; buy it whole and let the bounce pay for
the ~26 bps round trip. Exit on a 1.5% recovery, on a 2% further slide, and keep
a small probe round trip early so the entry always books at least one trade.

Standard library only. No clock, no network, no files, no randomness: the same
bars produce the same orders every run.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars  # noqa: E402

SYMBOL = "CBBTC"
LOOKBACK = 45          # bars in the change test
DROP_BPS = 200         # buy when close is 2% under its close 45 bars ago
TAKE_PROFIT_BPS = 150  # sell when the position is 1.5% over its entry close
STOP_BPS = 200         # sell when it is 2% under it
COOLDOWN = 60          # bars to wait after an exit before the next entry
MAX_SLIP_BPS = 400     # never chase more than 4% past the close we decided on
PROBE_UNITS = 3_000_000  # 3 USDC: the guardrail trade, so the entry always trades
PROBE_SEQ = 5          # bar the probe buys on (flat market insurance)
PROBE_SELL_SEQ = 6     # bar it sells on

closes = []
last_seq = -1
entry_close = 0
bar_of_entry = 0
bar_of_exit = -(10 ** 9)
probe_armed = True


def on_batch(state, batch):
    """Called once per bar with the state folded in; return this bar's orders."""
    global last_seq, entry_close, bar_of_entry, bar_of_exit, probe_armed

    seq = state.seq
    price = state.close(SYMBOL)
    if price is None:
        return []
    if seq != last_seq:
        closes.append(price)
        last_seq = seq

    holding = state.positions.get(SYMBOL)
    qty = holding.qty if holding is not None else 0

    # Probe: one small round trip early, so a race window with no washout still
    # books the trade the guardrails ask for.
    if probe_armed and qty == 0 and seq == PROBE_SEQ:
        return [{"side": "buy", "symbol": SYMBOL, "notional_quote_units": PROBE_UNITS,
                 "max_slippage_bps": MAX_SLIP_BPS}]
    if probe_armed and qty > 0 and seq == PROBE_SELL_SEQ:
        probe_armed = False
        bar_of_exit = seq
        return [{"side": "sell", "symbol": SYMBOL, "qty": qty,
                 "max_slippage_bps": MAX_SLIP_BPS}]

    if qty > 0:
        change = (price / entry_close - 1) * 10_000
        if change >= TAKE_PROFIT_BPS or change <= -STOP_BPS:
            bar_of_exit = seq
            return [{"side": "sell", "symbol": SYMBOL, "qty": qty,
                     "max_slippage_bps": MAX_SLIP_BPS}]
        return []

    # Washout entry.
    if len(closes) <= LOOKBACK:
        return []
    if seq - bar_of_exit < COOLDOWN:
        return []
    change = (price / closes[-1 - LOOKBACK] - 1) * 10_000
    if change <= -DROP_BPS and state.cash > PROBE_UNITS:
        entry_close = price
        bar_of_entry = seq
        return [{"side": "buy", "symbol": SYMBOL, "notional_quote_units": state.cash,
                 "max_slippage_bps": MAX_SLIP_BPS}]
    return []


if __name__ == "__main__":
    makefun_bars.run(on_batch)
