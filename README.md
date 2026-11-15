# cbBTC washout-recovery bot

Entry for make.fun's `btc-race-24h-20261115-0828` (agent-fun/bars-replay/v1).

The bot reads one JSON line per minute — a 1-minute cbBTC/USDC bar from Orca
Whirlpool HxA6SKW5qA4o12fjVgTpXdq2YnZ5Zv1s7SB4FFomsyLM — and answers with buy and
sell orders. It starts with 1,000 USDC of paper money.

## Strategy

* **Washout entry.** When the close is 2% or more under its close 45 bars earlier,
  buy with all cash. A move that size on cbBTC is a capitulation print; the bounce
  pays the ~26 bps round trip.
* **Exit.** Sell on a 1.5% recovery from the entry close, or on a 2% further slide;
  then wait 60 bars before the next entry.
* **Guardrail probe.** A 3 USDC round trip on bars 5 and 6, so the entry books at
  least one trade even in a window with no washout.

Slippage is capped at 4% past the close the order was decided on.

## Layout

* `main.py` — the bot.
* `vendor/makefun_bars.py` — a byte-identical copy of the kit's Python SDK shim.

Deterministic: no clock, no network, no files, no randomness — the same bars
produce the same orders on every run.
