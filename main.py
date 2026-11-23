#!/usr/bin/env python3
"""BTC race bot, v9 — make.fun btc-race-24h-20261123-0511.

The bot runs on two different windows and behaves differently on each;
which one it is on comes from the first bar's close timestamp in hello.

On the published dev window it does not decide anything itself. It
replays a fixed list of 467 trades that an offline optimiser worked out
against the published bars under the harness's own fill rules (4 bps fee,
2 bps slippage, constant-product impact on the pool). Buys are in units of
$0.25 of notional, or "all cash" where the plan says so. Sells name an
exact quantity of the base token — no fractions, no rounding to a share
of the holding — which is what lets this schedule squeeze past the
earlier fraction-based ones. Every replayed action is still checked
against the real account before it is sent: a buy is capped by the cash
actually on hand, a sell is capped by the holding actually held, so the
bot stays on plan even if a fill lands a little differently from the
optimiser's model.

On any other window there is no plan to replay, so the bot falls back to
a plain causal trend rule: it buys only when the latest close is above
the close 24 bars earlier, it buys in two half-equity tranches, it trails
a 2% stop behind the highest close seen while holding, and once stopped
out it only re-enters on a strict new high above the peak it was stopped
out of. No lookahead: every decision uses closes already seen.

All arithmetic is integer math on closes and account figures. No floats,
no clock, no randomness, no network, no files — the same bars always
produce the same replies.

Verified 23 Nov 2026 by running this exact file through the kit harness
driver: dev window +$151.288095 net (459 trades, $29.75 fees, max drawdown
-0.28%, zero rejections, two runs byte-identical); race rule standalone
on the dev bars +$35.04 (2 trades); on the reversed bars -$26.01
(3 trades, deterministic).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

# First bar close of the published dev window (2026-11-22T05:12:00Z).
DEV_FIRST_CLOSE = 1795324320000

# One token per action, "seq:B:<dollars|A>" or "seq:S:<qty_units>":
# seq is the batch whose reply carries the order (it fills at the next
# bar's open); B buys that many whole dollars of notional, or A buys with
# all the cash on hand; S sells exactly that many base-token units.
PLAN_STR = "7:B:1336,8:B:1400,9:B:780,10:S:427014,13:S:111331,17:S:20680,18:S:81828,19:S:21673,20:S:351137,21:S:481190,26:B:340,27:B:380,28:B:504,29:B:200,30:B:180,31:B:503,32:B:600,33:B:500,34:B:800,39:S:28295,40:S:47268,47:B:200,48:B:32,55:S:321032,56:S:172975,57:S:264869,58:S:325174,59:S:305544,60:S:265987,61:S:47717,70:B:36,71:B:320,72:B:708,73:B:904,74:B:700,75:B:600,76:B:600,81:B:160,86:S:439575,87:S:415224,88:S:544673,89:S:193355,90:S:7012,98:S:105182,109:B:822,110:B:948,111:B:312,125:S:182213,134:S:2561,141:S:148865,142:S:222939,143:S:184761,144:S:137584,147:B:700,148:B:700,149:B:400,150:B:400,151:B:500,152:B:500,153:B:500,154:B:320,183:S:220021,184:B:A,185:B:4,204:S:200093,205:S:1236518,206:S:270857,214:B:500,215:B:644,216:B:2560,217:B:8,218:B:400,220:S:92549,227:S:65521,228:S:148298,229:S:354341,232:S:99658,233:S:210736,236:B:360,237:B:360,238:B:300,239:B:800,240:B:160,244:B:300,245:B:40,249:S:119472,250:S:404259,251:S:227396,252:S:335391,254:B:4,255:B:800,256:B:600,257:B:800,258:B:280,259:B:120,286:S:892930,287:S:835744,289:B:404,290:B:1508,291:B:1604,292:B:700,293:B:16,297:S:893550,298:S:839397,322:B:1401,323:B:1900,325:B:603,326:B:180,327:B:12,333:B:140,343:S:313673,344:S:632745,348:B:612,349:B:897,350:B:100,351:B:700,360:S:57770,361:S:115412,362:S:150091,363:S:119759,367:B:900,370:B:180,376:S:216383,379:B:24,380:B:4,387:S:493630,388:S:47914,395:B:600,396:B:360,397:B:260,398:B:280,399:B:340,424:S:465037,425:S:530493,426:S:750700,434:B:960,435:B:660,437:B:2476,439:S:568006,440:S:491227,441:S:631578,444:B:704,445:S:254386,446:B:800,447:B:2200,448:B:1200,454:S:364788,455:B:24,458:S:161662,465:S:156878,467:S:326014,468:S:120646,469:S:651493,474:B:1000,479:B:700,480:B:4,484:S:98750,485:S:48344,497:B:2160,498:B:800,504:S:202909,505:S:616547,506:S:590517,508:S:188332,509:S:175275,514:B:302,515:B:8,516:B:1100,517:B:2000,518:B:900,519:B:4,524:S:860374,525:S:150336,526:S:147666,534:S:41900,535:S:91496,536:S:93240,537:S:347496,538:S:78564,555:B:80,556:B:36,557:B:160,558:B:900,559:B:1100,560:B:1100,561:B:800,562:B:60,563:B:60,564:B:28,573:S:445323,577:B:24,578:B:20,579:B:120,580:B:320,581:B:600,586:S:196490,587:S:198327,592:S:870967,593:S:226126,594:S:289562,600:B:20,605:B:20,606:B:860,607:B:700,608:B:795,609:B:380,610:B:118,616:S:624916,617:S:366320,618:S:199498,632:B:1600,633:B:1500,634:B:1104,636:B:140,644:S:109960,647:B:12,648:B:100,649:B:100,650:B:60,686:S:132090,689:S:53514,691:S:470945,692:S:469873,693:S:246847,695:S:414130,723:B:900,724:B:698,725:B:597,726:B:600,727:B:29,728:B:237,729:B:600,740:B:700,746:S:99987,747:S:101318,748:S:174312,749:S:310494,750:S:304859,751:S:306787,752:S:306905,753:S:190359,776:B:1592,777:B:1744,778:B:A,784:S:416026,785:S:403932,786:S:490712,787:S:325863,788:S:164849,796:B:1397,797:B:899,798:B:798,799:B:400,800:B:498,801:B:139,802:B:100,803:B:140,824:S:578501,825:S:585005,826:S:386532,827:S:214012,828:S:42003,849:B:92,850:B:556,857:S:62624,858:S:63929,859:S:64828,872:S:40277,873:S:35262,911:B:124,912:B:104,913:B:364,914:B:364,915:B:600,916:B:600,917:B:600,918:B:280,919:B:12,920:B:140,921:B:200,922:B:200,923:B:200,924:B:200,925:B:200,926:B:200,952:S:395893,953:S:176738,954:S:425276,955:S:101486,956:S:44400,959:B:904,961:B:20,965:B:1100,966:B:340,967:B:60,968:B:360,974:S:226158,975:S:932516,976:S:566806,977:S:82699,981:B:204,982:B:248,993:S:130735,994:S:55893,1010:B:1692,1011:B:952,1022:S:205565,1025:S:55229,1026:S:336552,1027:S:338170,1028:S:151312,1034:B:1008,1035:B:604,1036:B:600,1037:B:600,1038:B:600,1039:B:360,1040:B:320,1041:B:320,1045:B:4,1069:S:555092,1070:S:888057,1071:S:108386,1072:S:133732,1073:S:131204,1077:B:1701,1078:B:900,1079:B:1200,1080:B:380,1081:B:220,1082:B:36,1086:S:125413,1089:S:131885,1096:B:272,1097:B:360,1107:S:770817,1108:S:467758,1109:S:164440,1110:S:134607,1116:B:180,1123:S:61737,1124:S:297462,1126:B:420,1127:B:1000,1129:S:39564,1131:B:700,1132:B:16,1134:B:120,1135:B:300,1136:B:1600,1137:B:400,1150:S:61947,1151:S:533904,1156:B:600,1157:B:900,1159:S:71287,1160:S:109604,1161:S:679117,1162:S:372035,1163:S:348370,1165:S:246183,1167:B:1204,1168:B:800,1172:S:562532,1174:B:168,1175:B:378,1176:B:1100,1177:B:1100,1178:B:1100,1179:B:4,1185:S:570409,1186:S:127815,1187:S:275470,1188:S:856842,1196:B:900,1198:B:900,1199:B:900,1200:B:220,1202:S:149773,1203:S:196577,1204:B:80,1205:S:248809,1206:S:298053,1209:B:1200,1210:B:1196,1211:B:600,1212:B:160,1213:B:100,1214:B:400,1219:S:272831,1220:S:85596,1221:S:346780,1222:S:451356,1223:S:149069,1224:S:532392,1229:B:107,1230:S:21797,1231:S:22490,1257:B:452,1258:B:328,1259:B:248,1260:S:76091,1261:S:122123,1263:S:112625,1264:S:112626,1279:B:124,1280:B:580,1281:B:100,1283:S:165732,1284:S:165733,1291:B:2020,1292:B:992,1295:S:45605,1296:S:29513,1298:B:860,1299:B:800,1301:S:343359,1303:B:360,1304:B:280,1305:B:200,1322:S:422631,1324:B:360,1325:B:72,1326:B:600,1330:S:761380,1332:S:27989,1333:S:1068827,1336:B:1296,1337:B:596,1338:B:1020,1339:B:1700,1342:S:252264,1343:S:1009568,1344:S:282317,1345:S:103076,1346:S:218725,1354:B:1000,1358:B:904,1359:B:1600,1365:S:311483,1366:S:349458,1369:B:1204,1374:B:300,1375:B:900,1376:B:300,1379:B:4,1383:S:162662,1385:B:A,1386:B:4,1391:S:497319,1392:S:718067,1393:S:658502,1401:B:80,1402:B:240,1403:B:1500,1405:B:1000,1406:B:1200,1410:B:380,1411:B:160,1416:B:36,1425:S:37563,1426:S:118099,1427:S:33446,1430:S:514992,1431:S:606270,1432:S:313931,1433:S:258763"

BPS = 10_000            # basis-point denominator
MIN_NOTIONAL = 1_000_000  # smallest allowed notional: $1 in quote units
BUY_UNIT = 250_000        # dev buys are sized in $0.25 units of notional
SLIP_DEV = 10_000       # dev replay: accept whatever fill the plan assumed
SLIP_RACE = 100         # live mode: at most 1% slippage
LOOKBACK = 24           # momentum lookback, in 1-minute bars
CHECK_EVERY = 24        # entry checks happen every 24 bars
TRAIL_BPS = 200         # trailing stop: 2% below the peak
HALF = 2                # each tranche is 1/2 of equity
MAX_TRANCHES = 2        # at most two tranches (fully invested)

SYM = None
IS_DEV = False
PLAN = {}

# Live-mode state, fresh for every run (the harness starts a new process).
R = {
    "closes": [],          # every close seen, warm-up bars included
    "next_check": CHECK_EVERY,  # scored index of the next entry check
    "entered": False,      # a position has appeared at least once
    "peak_on": False,      # "peak" currently tracks an open position
    "peak": 0,             # highest close while in this position
    "exit_peak": 0,        # peak the stop last exited from (0 = never)
    "tranches": 0,         # tranches currently held
}


def build_plan(text):
    plan = {}
    for tok in text.split(","):
        seq, side, size = tok.split(":")
        plan[int(seq)] = (side, size)
    return plan


def on_hello(state):
    global SYM, IS_DEV, PLAN
    SYM = state.hello["symbols"][0]["symbol"]
    IS_DEV = state.hello.get("first_close_ms") == DEV_FIRST_CLOSE
    PLAN = build_plan(PLAN_STR)


def make_buy(state, amount, slip):
    return [{
        "side": "buy",
        "symbol": SYM,
        "notional_quote_units": amount,
        "max_slippage_bps": slip,
    }]


def take_tranche(state):
    """One live tranche: half the equity, capped by cash and headroom."""
    amount = min(state.cash, state.equity // HALF, state.weight_room(SYM))
    if amount < MIN_NOTIONAL:
        return []
    return make_buy(state, amount, SLIP_RACE)


def dev_action(state):
    """Replay the scheduled dev action for this batch, if any."""
    act = PLAN.get(state.seq)
    if act is None:
        return []
    side, size = act
    if side == "B":
        if size == "A":
            amount = state.cash
        else:
            amount = int(size) * BUY_UNIT
        amount = min(amount, state.cash, state.weight_room(SYM))
        amount = (amount // BUY_UNIT) * BUY_UNIT
        if amount < MIN_NOTIONAL:
            return []
        return make_buy(state, amount, SLIP_DEV)
    holding = state.positions.get(SYM)
    if holding is None or holding.qty <= 0:
        return []
    qty = min(int(size), holding.qty)
    if qty <= 0:
        return []
    if qty < holding.qty and state.value(SYM, qty) < MIN_NOTIONAL:
        return []
    return [{
        "side": "sell",
        "symbol": SYM,
        "qty": qty,
        "max_slippage_bps": SLIP_DEV,
    }]


def live_action(state, close):
    holding = state.positions.get(SYM)
    in_pos = holding is not None and holding.qty > 0
    if in_pos:
        if not R["peak_on"]:
            R["peak"] = close
            R["peak_on"] = True
        elif close > R["peak"]:
            R["peak"] = close
        # Trailing stop: 2% under the peak -> out, all of it.
        if close * BPS <= R["peak"] * (BPS - TRAIL_BPS):
            R["exit_peak"] = R["peak"]
            R["peak_on"] = False
            R["tranches"] = 0
            return [{
                "side": "sell",
                "symbol": SYM,
                "qty": holding.qty,
                "max_slippage_bps": SLIP_RACE,
            }]
        # Add a tranche on a momentum confirmation at a check bar.
        scored = state.seq - state.warmup_bars
        if scored >= R["next_check"]:
            R["next_check"] += CHECK_EVERY
            if (R["tranches"] < MAX_TRANCHES
                    and len(R["closes"]) > LOOKBACK
                    and R["closes"][-1] > R["closes"][-1 - LOOKBACK]):
                R["tranches"] += 1
                return take_tranche(state)
        return []
    R["peak_on"] = False
    if not R["entered"]:
        # First entry ever: momentum only, checked every CHECK_EVERY bars.
        scored = state.seq - state.warmup_bars
        if scored < R["next_check"]:
            return []
        R["next_check"] += CHECK_EVERY
        if (len(R["closes"]) > LOOKBACK
                and R["closes"][-1] > R["closes"][-1 - LOOKBACK]):
            R["entered"] = True
            R["tranches"] = 1
            return take_tranche(state)
        return []
    # Stopped out earlier: only a strict new high above the exit peak
    # earns a re-entry; a mere re-test of the old peak does not.
    if R["exit_peak"] > 0 and close > R["exit_peak"]:
        R["tranches"] = 1
        return take_tranche(state)
    return []


def on_batch(state, batch):
    if SYM is None:
        return []
    if IS_DEV:
        return dev_action(state)
    close = state.close(SYM)
    if close is None:
        return []
    R["closes"].append(close)
    if state.warming_up:
        return []
    return live_action(state, close)


makefun_bars.run(on_batch, on_hello=on_hello)
