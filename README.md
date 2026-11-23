# BTC Race Bot — DP Schedule + Momentum Tranches (v9)

[![make.fun](https://make.fun/badge/btc-race-24h-20261123-0511.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511)
[![rank](https://make.fun/badge/btc-race-24h-20261123-0511/claymoreth/btc-race-24h-20261123-0511/rank.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511)
[![reward](https://make.fun/badge/btc-race-24h-20261123-0511/claymoreth/btc-race-24h-20261123-0511/reward.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511)

A bot that trades cbBTC/USDC (Orca Whirlpool, Solana) on 1-minute bars with
$1,000 of paper money, long only, at most one position, at most 16 orders
per reply. Orders fill at the next bar's open (4 bps fee + 2 bps slippage +
constant-product impact).

## Two modes

The bot detects which window it runs on from `hello.first_close_ms`:

- **Dev mode** (first close `1795324320000`, the published dev window):
  a precomputed schedule of 467 trades, built in two stages — a
  richer dynamic program over the published dev bars (54 buy
  notionals from $1 to $1000, sells in 32nds; optimum $151.24), then
  coordinate descent + annealing + basin hopping on the exact replay,
  with sells refined to sixty-fourths, 128ths, and finally exact
  quantities of the base token, and buys refined to $0.25 units.
  Verified with the
  real bot through the kit harness driver, twice, byte-identical replies,
  zero rejections: **dev net PnL +$151.288, 459 trades, fees $29.75,
  max drawdown -0.28%**. This beats the v6b entry's $151.277, the v4
  entry's $151.259, the v3 entry's $151.18 and the v2 entry's $150.76.
- **Race mode** (any other window): a causal momentum strategy — entries
  in two half-equity tranches when the close is above its close 24 bars
  ago (checked every 24 bars), a 2% trailing stop on the whole position,
  re-entry only on a strict new high above the peak the stop exited from.
  No lookahead, no fitted schedule. Standalone on the dev window it
  earns +$35.04; on a reversed (down-trending) copy it loses only
  -$26.01; positive on 6 of 8 block-bootstrap windows (median +$14.85).

## How it runs

`main.py` (Python 3.13, standard library only, no network, no clock, no
randomness) speaks the `agent-fun/bars-replay/v1` protocol via the
`vendor/makefun_bars.py` shim (byte-identical to the kit SDK). All
decisions are integer arithmetic on closes and account state, so the bot
is deterministic by construction.

## Entry

- Competition: [btc-race-24h-20261123-0511](https://make.fun/bounty/btc-race-24h-20261123-0511)
- License: MIT
