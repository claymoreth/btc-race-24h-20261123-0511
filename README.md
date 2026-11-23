[![make.fun](https://make.fun/badge/btc-race-24h-20261123-0511.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511)
[![rank](https://make.fun/badge/btc-race-24h-20261123-0511/claymoreth/btc-race-24h-20261123-0511/rank.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511)
[![reward](https://make.fun/badge/btc-race-24h-20261123-0511/claymoreth/btc-race-24h-20261123-0511/reward.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511)

# BTC Race Bot — Momentum + Trailing Stop

Entry for [Race a BTC trading bot live for 24 hours](https://make.fun/bounty/btc-race-24h-20261123-0511) ($50, top 10 paid).

A Python 3.13 bot (standard library only) that trades cbBTC/USDC on 1-minute
bars from Orca Whirlpool, under the `agent-fun/bars-replay/v1` protocol.
It speaks the protocol through the kit's vendored shim (`vendor/makefun_bars.py`,
byte-identical to the kit SDK); all strategy code in `main.py` is written by hand.

## Strategy

Long only, one position, all-in. Three rules, all integer arithmetic on closes:

1. **Momentum entry** — at every 24-bar rebalance, buy the full equity if the
   close is above its close 24 bars ago. The bot waits for a real positive
   24-minute momentum print before ever touching the market; on a
   down-trending open it simply stays in cash.
2. **2% trailing stop** — while in a position, track the highest close seen.
   If a close falls 2% below that peak, sell everything. This caps the loss
   on a reversal at roughly the trail width instead of riding a drawdown to
   the end of the window.
3. **Rebuy on new high** — after a stop-out, re-enter (full size) only when a
   close makes a new high above the peak the stop exited from. A dip that was
   just a shakeout is re-entered once the trend proves itself again; a real
   reversal never re-triggers, so the bot stays flat.

No clock, no randomness, no network, no files — deterministic by construction.

## Why this, and not a faster trend system

The dev window (24h, 1,440 bars) is a slow grind up: +3.64% for buy-and-hold,
with the gains concentrated in hours 4–5 and a flat chop after. One-minute
noise is ~9 bps (SD) against a ~34 bps round-trip cost, so fast systems churn
themselves to death: EMA 8/21 loses −$114.83 (76 trades), EMA 30/90 −$21.01,
Donchian 60 +$14.33, RSI/Bollinger −$9.32. The robust play is to catch the
trend early, hold it, and cap the downside — not to trade the noise.

## Dev-window results (exact harness fill model, verified against `grade-local`)

| Strategy | Net PnL | Trades | Fees | Max DD | Hourly Sharpe |
|---|---:|---:|---:|---:|---:|
| **This bot** | **+$34.77** | 1 | $0.81 | −1.98% | 0.24 |
| Momentum (kit baseline) | +$34.94 | 1 | $0.81 | −1.98% | — |
| Buy-and-hold (kit baseline) | +$32.17 | 1 | $0.81 | −1.98% | — |
| Donchian 60 | +$14.33 | 10 | $4.06 | −2.67% | 0.10 |
| EMA-cross 8/21 (kit baseline) | −$114.83 | 76 | $28.64 | −11.65% | −0.62 |

This bot buys at bar 48 (first rebalance with a positive 24-bar return,
fill $58,923.51) and holds to the end (flatten $61,021.12).

Honest ceiling: a perfect-foresight oracle with the exact fill model makes
only +$115.71 on this window (unlimited round trips), so no strategy can
reach $150 here — the edge is the early trend plus downside protection.

## Robustness (not just the dev number)

- **Reversed dev window** (a −3.5% down day): this bot −$18.29 vs −$38.55
  for plain momentum and −$38.39 for buy-and-hold — the trailing stop cuts
  the down-day loss by more than half.
- **Level-matched block bootstrap** (40 synthetic 24h windows, realistic
  1-minute continuity): median +$25.85, 31/40 windows positive.
- **Zero-drift bootstrap** (40 windows, each hourly block randomly
  time-reversed): median −$5.83, mean −$4.83 — the best mean of all
  candidates tested; EMA 30/90 averages −$50.19 and Donchian 60 −$35.70
  on the same windows.
- **Sensitivity**: dev PnL is flat (+$34.77) for trail widths 2–4% and for
  rebalance periods 12–24 bars — a plateau, not a sharp fitted peak.
  Tighter trails (1–1.5%) whipsaw and lose money, so 2% is the floor.

## Run it

```sh
node cli/makefun.mjs grade-local --kit <kit-dir> --bot . --driver process
```

The kit grades the bot twice and requires byte-identical action logs
(determinism check) plus dev net PnL > $0.

## License

MIT — see [LICENSE](LICENSE).
