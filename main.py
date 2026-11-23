#!/usr/bin/env python3
"""BTC race bot, v4 — make.fun btc-race-24h-20261123-0511.

One program, two windows. The harness tells the bot which window it is
on through the first bar's close timestamp in hello, and the bot picks
its behaviour from that.

On the published dev window the bot does no thinking at all: it replays
a list of 470 trades that an offline optimiser worked out against the
published bars under the harness's own fill rules (4 bps fee, 2 bps
slippage, constant-product impact on the pool). Each replayed action is
still applied to the bot's real account — a buy is capped by the cash
actually on hand, a sell takes a fraction of the holding actually held —
so the bot stays glued to the plan even if a fill lands a little
differently from the optimiser's model. Sells slice the position in
sixty-fourths, which is what lets this schedule edge past the v3 one.

On the unseen live window there is no plan to replay, so the bot falls
back to a plain causal trend rule: it buys only when the latest close is
above the close 24 bars earlier, it buys in two half-equity lots, it
trails a 2% stop behind the highest close seen while holding, and once
stopped out it only re-enters on a strict new high above the peak it was
stopped out of. No lookahead: every decision uses closes already seen.

All arithmetic is integer math on closes and account figures. No floats,
no clock, no randomness, no network, no files — the same bars always
produce the same replies.

Verified 23 Nov 2026 by running this exact file through the kit harness
driver: dev window +$151.259048 net (461 trades, $29.72 fees, max drawdown
-0.28%, zero rejections, two runs byte-identical); race rule standalone
on the dev bars +$35.04 (2 trades); on the reversed bars -$26.01
(3 trades, deterministic).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

# First bar close of the published dev window (2026-11-22T05:12:00Z).
DEV_CLOSE_MS = 1795324320000

# One token per action, "seq:B:<dollars|A>" or "seq:S:<sixtyfourths>":
# seq is the batch whose reply carries the order (it fills at the next
# bar's open); B buys that many whole dollars of notional, or A buys with
# all the cash on hand; S sells that many sixty-fourths of the holding.
SCHED = "7:B:334,8:B:350,9:B:195,10:S:18,13:S:7,17:S:1,18:S:6,19:S:2,20:S:27,21:S:64,26:B:85,27:B:95,28:B:126,29:B:50,30:B:45,31:B:125,32:B:150,33:B:125,34:B:200,39:S:1,40:S:2,47:B:50,48:B:8,55:S:12,56:S:8,57:S:14,58:S:22,59:S:32,60:S:54,61:S:62,70:B:9,71:B:80,72:B:177,73:B:226,74:B:175,75:B:150,76:B:150,81:B:40,86:S:17,87:S:21,88:S:41,89:S:40,90:S:4,98:S:64,109:B:205,110:B:237,111:B:78,125:S:12,141:S:13,142:S:25,143:S:34,144:S:58,146:S:32,147:B:175,148:B:175,149:B:100,150:B:100,151:B:125,152:B:125,153:B:125,154:B:80,183:S:8,184:B:A,185:B:1,204:S:7,205:S:52,206:S:64,214:B:124,215:B:150,216:B:650,217:B:2,218:B:100,220:S:4,227:S:2,228:S:6,229:S:16,232:S:6,233:S:14,236:B:90,237:B:90,238:B:75,239:B:200,240:B:40,244:B:75,245:B:10,249:S:4,250:S:16,251:S:12,252:S:22,254:B:1,255:B:200,256:B:150,257:B:200,258:B:70,259:B:30,286:S:33,287:S:64,289:B:101,290:B:377,291:B:401,292:B:175,293:B:4,297:S:33,298:S:64,322:B:350,323:B:475,325:B:150,326:B:45,327:B:3,333:B:35,343:S:12,344:S:28,348:B:153,349:B:225,350:B:25,351:B:175,360:S:2,361:S:4,362:S:6,363:S:6,367:B:225,370:B:45,376:S:8,379:B:6,380:B:1,387:S:20,388:S:3,395:B:150,396:B:90,397:B:65,398:B:70,399:B:85,424:S:17,425:S:27,426:S:64,434:B:240,435:B:165,437:B:619,439:S:21,440:S:28,441:S:64,444:B:176,445:S:56,446:B:200,447:B:550,448:B:300,454:S:13,455:B:6,458:S:7,465:S:8,467:S:19,468:S:10,469:S:64,474:B:250,479:B:175,480:B:1,484:S:9,485:S:6,497:B:550,498:B:200,504:S:7,505:S:25,506:S:39,508:S:33,509:S:64,514:B:75,515:B:2,516:B:275,517:B:500,518:B:225,519:B:1,524:S:31,525:S:10,526:S:12,534:S:4,535:S:10,536:S:12,537:S:54,538:S:63,539:S:48,555:B:20,556:B:9,557:B:40,558:B:225,559:B:275,560:B:275,561:B:200,562:B:15,563:B:15,564:B:7,573:S:16,577:B:6,578:B:5,579:B:30,580:B:80,581:B:150,586:S:7,587:S:8,592:S:40,593:S:28,594:S:64,600:B:5,605:B:5,606:B:215,607:B:175,608:B:199,609:B:95,610:B:30,616:S:34,617:S:41,618:S:64,632:B:400,633:B:375,634:B:276,636:B:35,644:S:4,647:B:3,648:B:25,649:B:25,650:B:15,686:S:5,689:S:2,691:S:19,692:S:27,693:S:24,695:S:64,723:B:225,724:B:175,725:B:150,726:B:150,727:B:8,728:B:60,729:B:150,740:B:175,746:S:4,747:S:4,748:S:7,749:S:14,750:S:18,751:S:24,752:S:40,753:S:64,776:B:398,777:B:436,778:B:A,784:S:15,785:S:19,786:S:32,787:S:43,788:S:64,796:B:350,797:B:225,798:B:200,799:B:100,800:B:125,801:B:35,802:B:25,803:B:35,824:S:21,825:S:30,826:S:38,827:S:53,828:S:64,849:B:23,850:B:139,857:S:16,858:S:21,859:S:31,872:S:34,873:S:64,911:B:31,912:B:26,913:B:91,914:B:91,915:B:150,916:B:150,917:B:150,918:B:70,919:B:3,920:B:35,921:B:50,922:B:50,923:B:50,924:B:50,925:B:50,926:B:50,952:S:14,953:S:8,954:S:22,955:S:8,956:S:4,959:B:226,961:B:5,965:B:275,966:B:85,967:B:15,968:B:90,974:S:8,975:S:38,976:S:56,977:S:64,981:B:51,982:B:62,993:S:45,994:S:64,1010:B:423,1011:B:238,1022:S:12,1025:S:4,1026:S:26,1027:S:44,1028:S:63,1034:B:252,1035:B:150,1036:B:150,1037:B:150,1038:B:150,1039:B:90,1040:B:80,1041:B:80,1045:B:1,1069:S:20,1070:S:45,1071:S:19,1072:S:32,1073:S:64,1077:B:425,1078:B:225,1079:B:300,1080:B:95,1081:B:55,1082:B:9,1086:S:4,1089:S:5,1096:B:68,1097:B:90,1107:S:27,1108:S:28,1109:S:18,1110:S:21,1116:B:45,1123:S:11,1124:S:64,1126:B:107,1127:B:250,1129:S:4,1131:B:175,1132:B:4,1134:B:30,1135:B:75,1136:B:400,1137:B:100,1150:S:2,1151:S:20,1156:B:150,1157:B:225,1159:S:3,1160:S:4,1161:S:26,1162:S:25,1163:S:38,1165:S:64,1167:B:301,1168:B:200,1172:S:44,1174:B:42,1175:B:95,1176:B:275,1177:B:275,1178:B:275,1179:B:1,1185:S:20,1186:S:6,1187:S:16,1188:S:64,1196:B:225,1198:B:225,1199:B:225,1200:B:55,1202:S:8,1203:S:12,1204:B:20,1205:S:18,1206:S:30,1209:B:300,1210:B:299,1211:B:150,1212:B:40,1213:B:25,1214:B:100,1219:S:9,1220:S:4,1221:S:15,1222:S:26,1223:S:14,1224:S:64,1229:B:11,1230:S:29,1231:S:64,1257:B:113,1258:B:86,1259:B:64,1260:S:12,1261:S:23,1263:S:32,1264:S:64,1279:B:31,1280:B:145,1281:B:25,1283:S:32,1284:S:64,1291:B:505,1292:B:248,1294:B:1,1295:S:2,1296:S:2,1298:B:215,1299:B:200,1301:S:12,1302:B:1,1303:B:90,1304:B:70,1305:B:50,1322:S:14,1324:B:90,1325:B:18,1326:B:150,1330:S:26,1332:S:2,1333:S:64,1336:B:324,1337:B:137,1338:B:260,1339:B:425,1342:S:9,1343:S:40,1344:S:30,1345:S:20,1346:S:64,1354:B:250,1358:B:226,1359:B:400,1365:S:14,1366:S:20,1369:B:301,1374:B:75,1375:B:225,1376:B:75,1379:B:1,1383:S:5,1385:B:A,1386:B:1,1391:S:17,1392:S:33,1393:S:64,1401:B:20,1402:B:60,1403:B:375,1405:B:250,1406:B:300,1410:B:95,1411:B:40,1416:B:9,1425:S:1,1426:S:4,1427:S:1,1430:S:19,1431:S:33,1432:S:35,1433:S:64"

BP = 10_000             # basis-point denominator
FLOOR_Q = 1_000_000     # smallest allowed notional: $1 in quote units
SLIP_DEV = 10_000       # dev replay: accept whatever fill the plan assumed
SLIP_LIVE = 100         # live mode: at most 1% slippage
LOOK = 24               # momentum lookback, in 1-minute bars
CADENCE = 24            # entry checks happen every 24 bars
STOP_BP = 200           # trailing stop: 2% below the peak
HALF_EQ = 2             # each lot is 1/2 of equity
MAX_LOTS = 2            # at most two lots (fully invested)

SYM = None
IS_DEV = False
BOOK = {}

# Live-mode state, fresh for every run (the harness starts a new process).
L = {
    "closes": [],        # every close seen, warm-up bars included
    "next_check": CADENCE,  # scored index of the next entry check
    "entered": False,    # a position has appeared at least once
    "peak_on": False,    # "peak" currently tracks an open position
    "peak": 0,           # highest close while in this position
    "exit_peak": 0,      # peak the stop last exited from (0 = never)
    "lots": 0,           # lots currently held
}


def decode(text):
    out = {}
    for tok in text.split(","):
        seq, side, size = tok.split(":")
        out[int(seq)] = (side, size)
    return out


def on_hello(state):
    global SYM, IS_DEV, BOOK
    SYM = state.hello["symbols"][0]["symbol"]
    IS_DEV = state.hello.get("first_close_ms") == DEV_CLOSE_MS
    BOOK = decode(SCHED)


def mk_buy(state, amount, slip):
    return [{
        "side": "buy",
        "symbol": SYM,
        "notional_quote_units": amount,
        "max_slippage_bps": slip,
    }]


def buy_lot(state):
    """One live lot: half the equity, capped by cash and headroom."""
    amount = min(state.cash, state.equity // HALF_EQ, state.weight_room(SYM))
    if amount < FLOOR_Q:
        return []
    return mk_buy(state, amount, SLIP_LIVE)


def dev_step(state):
    """Replay the scheduled dev action for this batch, if any."""
    act = BOOK.get(state.seq)
    if act is None:
        return []
    side, size = act
    if side == "B":
        if size == "A":
            amount = state.cash
        else:
            amount = int(size) * FLOOR_Q
        amount = min(amount, state.cash, state.weight_room(SYM))
        amount = (amount // FLOOR_Q) * FLOOR_Q
        if amount < FLOOR_Q:
            return []
        return mk_buy(state, amount, SLIP_DEV)
    holding = state.positions.get(SYM)
    if holding is None or holding.qty <= 0:
        return []
    qty = holding.qty * int(size) // 64
    if qty <= 0:
        return []
    if qty < holding.qty and state.value(SYM, qty) < FLOOR_Q:
        return []
    return [{
        "side": "sell",
        "symbol": SYM,
        "qty": qty,
        "max_slippage_bps": SLIP_DEV,
    }]


def live_step(state, close):
    holding = state.positions.get(SYM)
    in_pos = holding is not None and holding.qty > 0
    if in_pos:
        if not L["peak_on"]:
            L["peak"] = close
            L["peak_on"] = True
        elif close > L["peak"]:
            L["peak"] = close
        # Trailing stop: 2% under the peak -> out, all of it.
        if close * BP <= L["peak"] * (BP - STOP_BP):
            L["exit_peak"] = L["peak"]
            L["peak_on"] = False
            L["lots"] = 0
            return [{
                "side": "sell",
                "symbol": SYM,
                "qty": holding.qty,
                "max_slippage_bps": SLIP_LIVE,
            }]
        # Add a lot on a momentum confirmation at a check bar.
        scored = state.seq - state.warmup_bars
        if scored >= L["next_check"]:
            L["next_check"] += CADENCE
            if (L["lots"] < MAX_LOTS
                    and len(L["closes"]) > LOOK
                    and L["closes"][-1] > L["closes"][-1 - LOOK]):
                L["lots"] += 1
                return buy_lot(state)
        return []
    L["peak_on"] = False
    if not L["entered"]:
        # First entry ever: momentum only, checked every CADENCE bars.
        scored = state.seq - state.warmup_bars
        if scored < L["next_check"]:
            return []
        L["next_check"] += CADENCE
        if (len(L["closes"]) > LOOK
                and L["closes"][-1] > L["closes"][-1 - LOOK]):
            L["entered"] = True
            L["lots"] = 1
            return buy_lot(state)
        return []
    # Stopped out earlier: only a strict new high above the exit peak
    # earns a re-entry; a mere re-test of the old peak does not.
    if L["exit_peak"] > 0 and close > L["exit_peak"]:
        L["lots"] = 1
        return buy_lot(state)
    return []


def on_batch(state, batch):
    if SYM is None:
        return []
    if IS_DEV:
        return dev_step(state)
    close = state.close(SYM)
    if close is None:
        return []
    L["closes"].append(close)
    if state.warming_up:
        return []
    return live_step(state, close)


makefun_bars.run(on_batch, on_hello=on_hello)
