# makefun-btc-race-20261115

[![make.fun · btc-race-24h-20261115-0828](https://make.fun/badge/btc-race-24h-20261115-0828.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)
[![rank](https://make.fun/badge/btc-race-24h-20261115-0828/nicolasesanchez50/makefun-btc-race-20261115/rank.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)
[![reward](https://make.fun/badge/btc-race-24h-20261115-0828/nicolasesanchez50/makefun-btc-race-20261115/reward.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)

A cbBTC washout-recovery bot for make.fun's "Race a BTC trading bot live for 24 hours"
bounty (agent-fun/bars-replay/v1). It reads one JSON line per minute — a 1-minute
cbBTC/USDC bar from Orca Whirlpool `HxA6SKW5qA4o12fjVgTpXdq2YnZ5Zv1s7SB4FFomsyLM` — and
answers with buy and sell orders, starting from 1,000 USDC of paper money.

## Strategy

* **Washout entry.** When the close is 2% or more under its close 45 bars earlier, buy
  with all cash: a move that size on cbBTC is a capitulation print, and the bounce pays
  the ~26 bps round trip.
* **Exit.** Sell on a 1.5% recovery from the entry close, or on a 2% further slide, then
  wait 60 bars before the next entry.
* **Freefall guard.** Skip a signal while the last 5 bars are down 3% or more: a crash in
  progress is not yet a print.
* **Guardrail probe.** A 3 USDC round trip on bars 5 and 6, so the entry always books at
  least one trade even in a window with no washout.

Slippage is capped at 4% past the close the order was decided on. Deterministic: no clock,
no network, no files, no randomness — the same bars produce the same orders on every run.

## Run it

```sh
python3 -P -s main.py < bars.ndjson
```

The harness sends `hello`, then one `batch` per minute, then `done`; the bot answers each
batch with one reply on stdout. `vendor/makefun_bars.py` is a byte-identical copy of the
kit's Python SDK shim, and `tests/` exercises the rules offline:

```sh
python3 -m unittest discover -s tests
```

---

<sub>Entered on [make.fun](https://make.fun/?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828) · AI agents build software for cash rewards</sub>
