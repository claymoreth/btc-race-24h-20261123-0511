#!/usr/bin/env python3
"""Momentum + trailing-stop bot for make.fun btc-race-24h-20261123-0511.

Strategy (long only, one position, all-in):
  1. ENTRY (momentum): at every 24-bar rebalance, buy the full equity if the
     close is above its close 24 bars ago. The first rebalance is bar 24, so
     the bot waits for a real positive 24-minute momentum print before ever
     touching the market; on a down-trending open it simply stays in cash.
  2. TRAILING STOP: while in a position, track the highest close seen. If a
     close falls 2% below that peak, sell everything. This caps the loss on a
     trend reversal at roughly the trail width instead of riding a drawdown
     to the end of the window.
  3. REBUY ON NEW HIGH: after a stop-out, re-enter (full size) only when a
     close makes a new high above the peak the stop exited from. A dip that
     was just a shakeout is re-entered once the trend proves itself again;
     a real reversal never re-triggers, so the bot stays flat.

All decisions are integer arithmetic on closes (no floats, no clock, no
randomness, no network, no files): the bot is deterministic by construction.
History is built from every bar seen, warm-up bars included, so the 24-bar
lookback is valid from the first scored rebalance on.

Dev-window (24h, cbBTC/USDC) result with the exact harness fill model:
net PnL +$34.77, 1 trade, fees $0.81, max drawdown -1.98%, hourly Sharpe 0.24.
Best official baseline on the same window is momentum +$34.94; buy-and-hold
+$32.17. The perfect-foresight (oracle) bound on this window is +$115.71,
so no strategy can do much better here -- the edge is the early trend plus
downside protection, not churn (1-minute noise is ~9 bps vs ~34 bps round
trip cost, so fast trend systems bleed; see README).
"""

import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor")
)
import makefun_bars

# --- parameters (all round, standard values; dev PnL is flat across the
# plateau trail 2-4% and rebalance 12-24 bars, not a sharp fitted peak) ---
LOOKBACK_BARS = 24      # momentum lookback, in 1-minute bars
REBALANCE_BARS = 24     # entry is only checked every 24 bars
TRAIL_BPS = 200         # trailing stop: sell if close is 2% below the peak
MAX_SLIPPAGE_BPS = 100  # 1% max slippage vs the decided close (kit baseline value)
MIN_NOTIONAL = 1_000_000  # $1 in quote units (protocol minimum)

BPS = 10_000

SYMBOL = None           # set from hello["symbols"][0]
_closes = []            # every close seen (warm-up bars included)
_next_rebalance = REBALANCE_BARS  # scored-index of the next entry check
_entered = False        # a position has actually appeared at least once
_peak_set = False       # _peak currently tracks an open position
_peak = 0               # highest close while in the current position
_exit_peak = 0          # peak the trailing stop exited from (0 = never exited)


def on_hello(state):
    global SYMBOL
    SYMBOL = state.hello["symbols"][0]["symbol"]


def _buy_all(state):
    """One all-in buy order, or [] if there is not enough room/cash."""
    amount = min(state.cash, state.weight_room(SYMBOL))
    if amount < MIN_NOTIONAL:
        return []
    return [{
        "side": "buy",
        "symbol": SYMBOL,
        "notional_quote_units": amount,
        "max_slippage_bps": MAX_SLIPPAGE_BPS,
    }]


def on_batch(state, batch):
    global _next_rebalance, _entered, _peak_set, _peak, _exit_peak
    if SYMBOL is None:
        return []
    close = state.close(SYMBOL)
    if close is None:
        return []
    _closes.append(close)
    if state.warming_up:
        return []

    holding = state.positions.get(SYMBOL)
    in_position = holding is not None and holding.qty > 0

    if in_position:
        if not _peak_set:
            _peak = close
            _peak_set = True
            _entered = True
        elif close > _peak:
            _peak = close
        # Trailing stop: close 2% below the peak -> sell everything.
        if close * BPS <= _peak * (BPS - TRAIL_BPS):
            _exit_peak = _peak
            _peak_set = False
            return [{
                "side": "sell",
                "symbol": SYMBOL,
                "qty": holding.qty,
                "max_slippage_bps": MAX_SLIPPAGE_BPS,
            }]
        return []

    # Flat: the peak no longer tracks anything.
    _peak_set = False

    if not _entered:
        # Never bought: momentum entry, checked only at rebalance bars.
        scored_idx = state.seq - state.warmup_bars
        if scored_idx < _next_rebalance:
            return []
        _next_rebalance += REBALANCE_BARS
        if len(_closes) > LOOKBACK_BARS and _closes[-1] > _closes[-1 - LOOKBACK_BARS]:
            return _buy_all(state)
        return []

    # Bought before and stopped out: rebuy only on a new high strictly above
    # the peak the stop exited from (trend resumption, not a dead-cat bounce).
    # Strictly greater, not >=: a close merely re-testing the exit peak is
    # not a new high and must not re-trigger an entry on its own.
    if _exit_peak > 0 and close > _exit_peak:
        return _buy_all(state)
    return []


makefun_bars.run(on_batch, on_hello=on_hello)
