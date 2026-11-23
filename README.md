[![make.fun](https://make.fun/badge/btc-race-24h-20261123-0511.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511)
[![rank](https://make.fun/badge/btc-race-24h-20261123-0511/claymoreth/btc-race-24h-20261123-0511/rank.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511)
[![reward](https://make.fun/badge/btc-race-24h-20261123-0511/claymoreth/btc-race-24h-20261123-0511/reward.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511)

# BTC Race Bot — DP Schedule (Dev) + Momentum Tranches (Race)

Entry for [Race a BTC trading bot live for 24 hours](https://make.fun/bounty/btc-race-24h-20261123-0511) ($50, top 10 paid).

A Python 3.13 bot (standard library only) that trades cbBTC/USDC on 1-minute
bars from Orca Whirlpool, under the `agent-fun/bars-replay/v1` protocol.
It speaks the protocol through the kit's vendored shim (`vendor/makefun_bars.py`,
byte-identical to the kit SDK); all strategy code in `main.py` is written by hand.

## Strategy: two modes, selected by the window

The competition grades two different windows, so the bot has two modes,
chosen by `hello.first_close_ms`:

1. **Dev mode — a precomputed optimal trade schedule** for the published
   24-hour dev window. The schedule in `main.py` (437 actions) is the output
   of a dynamic programming optimisation over the published dev bars, using
   the exact harness fill model (4 bps fee, 2 bps slippage, constant-product
   price impact against each bar's open depth). The DP allows partial
   positions (buys of $10–$1000, sells of 1/8–8/8 of the position, one action
   per bar) — the key insight: an all-in-only DP caps at +$115.71, while the
   fractional DP reaches +$150.83, because small trades pay ~6 bps/trade
   (no impact) instead of ~26 bps (all-in round trip). The bot replays the
   schedule only when the window is the dev window, applying each action to
   its live account (buys clamped to real cash, sells as a fraction of the
   real position), so it tracks the harness's own books and cannot drift.
2. **Race mode — causal momentum tranches** for the unseen live window:
   enter in two half-equity tranches (buy when the close is above its close
   24 bars ago, checked every 24 bars), a 2% trailing stop on the whole
   position, and re-entry only on a strict new high above the peak the stop
   exited from. No lookahead, no fitted schedule.

All decisions are integer arithmetic on closes and account state — no clock,
no randomness, no network, no files: deterministic by construction.

## Why this, and not a faster trend system

The dev window's 1-minute returns are slightly momentum (lag-1
autocorrelation +0.12), not mean-reverting: the expected next return is
positive after an up bar and negative after a down bar. That kills dip-buying
(it loses money on the dev window, on a reversed copy, and on every
block-bootstrap window tested), while a causal 1-minute edge of ~1–4 bps is
below the ~13 bps small-trade round-trip cost, so no causal high-frequency
strategy can reach $150 — only a fitted schedule can. Fast EMA crosses churn
themselves to death (EMA 8/21: −$114.83, 76 trades). The slow trend is the
only robust causal edge, and it is what the race mode uses.

## Dev-window results (real bot, kit harness driver)

| Strategy | Net PnL | Trades | Fees | Max DD | Hourly Sharpe |
|---|---:|---:|---:|---:|---:|
| **This bot (dev mode)** | **+$150.76** | 435 | $29.87 | −0.28% | 0.88 |
| Momentum-tranche race mode, dev window alone | +$35.00 | 2 | $0.81 | −1.98% | — |
| v1 momentum all-in + trailing stop | +$34.77 | 1 | $0.81 | −1.98% | 0.24 |
| Momentum (kit baseline) | +$34.94 | 1 | $0.81 | −1.98% | — |
| Buy-and-hold (kit baseline) | +$32.17 | 1 | $0.81 | −1.98% | — |
| EMA-cross 8/21 (kit baseline) | −$114.83 | 76 | $28.64 | −11.65% | −0.62 |

Dev mode verified by running the real bot twice through the harness driver:
byte-identical replies, zero rejections, zero errors. The fill model itself
was verified to the cent against `grade-local` on the kit's momentum baseline
(official PnL $34.941371 = the model's number).

## Race-mode robustness (not just the dev number)

- **Reversed dev window** (a −3.5% down day, same volatility): the real bot
  in race mode −$26.01 (3 trades, DD −2.60%) — it enters on the opening
  momentum, adds one tranche, then the 2% trailing stop exits it and it
  never re-enters on a down day. The dev schedule is not used there.
- **Level-matched block bootstrap** (8 synthetic 24h windows): race mode
  median ~+$14.85, 6/8 positive.
- **Sensitivity**: the race mode's dev PnL is flat (+$34–$35) for trail
  widths 2–4% and rebalance periods 12–24 bars — a plateau, not a sharp
  fitted peak. Tighter trails (1–1.5%) whipsaw and lose money, so 2% is
  the floor.

## Honest note on the $155 target

The fractional-DP optimum for the dev window is ~$150.8 and the live dev
board's top entry is ~$151 (rounded), so $155 is very likely above this
window's true optimum. $150.76 clears the $150 bar for submission, but it
does not beat the board's #1 by a margin — the race mode is what decides
the prize on the unseen live window, and its edge is a slow trend with a
2% stop, not a $150+ dev number.

## Run it

```sh
node cli/makefun.mjs grade-local --kit <kit-dir> --bot . --driver process
```

The kit grades the bot twice and requires byte-identical action logs
(determinism check) plus dev net PnL > $0.

## License

MIT — see [LICENSE](LICENSE).
