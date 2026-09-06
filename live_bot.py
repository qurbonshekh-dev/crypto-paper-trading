#!/usr/bin/env python3
"""
live_bot.py — исполнитель стратегии «Частая торговля» на ТВОЁМ аккаунте Binance.

Запускается только тобой, на твоей машине. Ключи лежат в файле .env рядом
и в git не попадают (.gitignore). Никто, кроме этого процесса, их не читает.

Режимы (переменная MODE в .env или в окружении):
  dry      — ключи не нужны; берёт живые свечи Binance и СИМУЛИРУЕТ сделки,
             ничего не отправляя. Проверка, что всё подключено и считает.
  testnet  — Binance Spot Testnet (testnet.binance.vision), фейковые деньги,
             настоящие ордера. Ключи — с сайта тестовой сети.
  live     — реальные деньги. Включается только явно: MODE=live и LIVE_CONFIRM=YES.

Правила — те же, что у ⚡-счёта: импульс +1% за час на 5-минутках, лот $10,
до 10 позиций, тейк +1.5%, стоп (по умолчанию −3%), выход по времени через 24 ч.
Выходы в testnet/live ставятся на бирже OCO-ордером: тейк и стоп живут на
Binance и исполняются, даже если бот выключен.

    python3 live_bot.py            # бесконечный цикл, шаг 5 минут
    python3 live_bot.py --once     # один проход и выход (для проверки)
"""
import os, sys, json, time, math, logging, datetime as dt

try:
    import ccxt
except ImportError:
    sys.exit("нужен ccxt:  python3 -m pip install --user ccxt")

HERE = os.path.dirname(os.path.abspath(__file__))
UTC = dt.timezone.utc


# ─────────────────────────── конфиг ───────────────────────────
def load_env():
    p = os.path.join(HERE, ".env")
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
load_env()

MODE        = os.environ.get("MODE", "dry").lower()
API_KEY     = os.environ.get("BINANCE_API_KEY", "")
API_SECRET  = os.environ.get("BINANCE_API_SECRET", "")
LOT         = float(os.environ.get("LOT_USDT", 10))
MAX_POS     = int(os.environ.get("MAX_POS", 10))
TP          = float(os.environ.get("TP_PCT", 1.5)) / 100
SL          = float(os.environ.get("SL_PCT", 3.0)) / 100
MOM_PCT     = float(os.environ.get("MOM_PCT", 1.0)) / 100
MOM_BARS    = int(os.environ.get("MOM_BARS", 12))
MAX_HOLD_H  = float(os.environ.get("MAX_HOLD_H", 24))
DAY_STOP    = float(os.environ.get("DAILY_LOSS_STOP_PCT", 5)) / 100
FEE         = 0.00075
PAIRS = [s.strip() for s in os.environ.get("PAIRS",
    "BTC,ETH,SOL,XRP,BNB,DOGE,ADA,AVAX,LINK,LTC,BCH,TRX,ZEC,WLD,SUI").split(",")]
SYMS = [f"{p}/USDT" for p in PAIRS]

if MODE not in ("dry", "testnet", "live"):
    sys.exit(f"MODE должен быть dry | testnet | live, а не {MODE!r}")
if MODE in ("testnet", "live") and not (API_KEY and API_SECRET):
    sys.exit("для testnet/live нужны BINANCE_API_KEY и BINANCE_API_SECRET в .env")
if MODE == "live" and os.environ.get("LIVE_CONFIRM") != "YES":
    sys.exit("реальный режим требует LIVE_CONFIRM=YES в .env — это осознанное решение, не опечатка")

STATE_F = os.path.join(HERE, f"bot_state_{MODE}.json")
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s",
    handlers=[logging.FileHandler(os.path.join(HERE, f"bot_{MODE}.log")),
              logging.StreamHandler(sys.stdout)])
log = logging.info


# ─────────────────────────── биржа ───────────────────────────
def make_exchange():
    ex = ccxt.binance({"apiKey": API_KEY, "secret": API_SECRET, "enableRateLimit": True,
                       "options": {"defaultType": "spot",
                                   "createMarketBuyOrderRequiresPrice": False}})
    if MODE == "testnet":
        ex.set_sandbox_mode(True)
    ex.load_markets()
    return ex


def closed_candles(ex, sym, n):
    """Последние n ЗАКРЫТЫХ 5-минутных свечей [t,o,h,l,c,v] (текущую формирующуюся отбрасываем)."""
    rows = ex.fetch_ohlcv(sym, "5m", limit=n + 1)
    return rows[:-1]


def momentum(rows):
    if len(rows) < MOM_BARS + 1:
        return None
    base, last = rows[-1 - MOM_BARS][4], rows[-1][4]
    return last / base - 1 if base else None


# ─────────────────────────── состояние ───────────────────────────
def load_state():
    if os.path.exists(STATE_F):
        return json.load(open(STATE_F))
    return {"positions": [], "trades": [], "day": None, "day_start_eq": None, "halted": False}


def save_state(s):
    tmp = STATE_F + ".tmp"
    json.dump(s, open(tmp, "w"), indent=1)
    os.replace(tmp, STATE_F)


def record_exit(s, p, px, why):
    proceeds = p["qty"] * px * (1 - FEE)
    pnl = proceeds - p["cost"]
    s["trades"].append({"sym": p["sym"], "in": p["t"], "out": now_iso(), "entry": p["entry"],
                        "exit": px, "why": why, "pnl_usd": round(pnl, 4)})
    log(f"ВЫХОД {p['sym']:<9} {why:<5} {p['entry']:.6g} → {px:.6g}   {pnl:+.3f}$")


def now_iso():
    return dt.datetime.now(UTC).isoformat(timespec="seconds")


def age_h(p):
    return (dt.datetime.now(UTC) - dt.datetime.fromisoformat(p["t"])).total_seconds() / 3600


# ─────────────────────────── ордера (testnet/live) ───────────────────────────
def market_buy(ex, sym):
    """Покупка на LOT USDT по рынку. Возвращает (qty, avg_price, cost)."""
    o = ex.create_order(sym, "market", "buy", LOT)          # amount = сумма в USDT
    o = ex.fetch_order(o["id"], sym)
    qty, avg = float(o["filled"]), float(o["average"] or o["price"] or 0)
    cost = float(o.get("cost") or qty * avg)
    return qty, avg, cost


def place_oco(ex, sym, qty, entry):
    """Тейк (лимит) + стоп (стоп-лимит) одним OCO-ордером на стороне биржи."""
    m = ex.market(sym)
    base = m["base"]
    free = float(ex.fetch_balance()["free"].get(base, 0))
    q = float(ex.amount_to_precision(sym, min(qty, free)))
    tp = ex.price_to_precision(sym, entry * (1 + TP))
    sl = ex.price_to_precision(sym, entry * (1 - SL))
    sl_lim = ex.price_to_precision(sym, entry * (1 - SL) * 0.995)
    params = {"symbol": m["id"], "side": "SELL", "quantity": ex.amount_to_precision(sym, q),
              "price": tp, "stopPrice": sl, "stopLimitPrice": sl_lim,
              "stopLimitTimeInForce": "GTC"}
    fn = getattr(ex, "privatePostOrderListOco", None) or getattr(ex, "privatePostOrderOco")
    r = fn(params)
    ids = [str(x["orderId"]) for x in r.get("orders", [])]
    return {"list_id": str(r.get("orderListId")), "order_ids": ids, "qty": q,
            "tp": float(tp), "sl": float(sl)}


def cancel_oco_and_sell(ex, sym, p):
    m = ex.market(sym)
    try:
        ex.privateDeleteOrderList({"symbol": m["id"], "orderListId": p["oco"]["list_id"]})
    except Exception as e:
        log(f"  отмена OCO не удалась ({e}); пробую продать остаток")
    free = float(ex.fetch_balance()["free"].get(m["base"], 0))
    q = float(ex.amount_to_precision(sym, min(p["qty"], free)))
    if q <= 0:
        return None
    o = ex.create_order(sym, "market", "sell", q)
    o = ex.fetch_order(o["id"], sym)
    return float(o["average"] or o["price"])


def check_oco(ex, sym, p):
    """Исполнилась ли одна из ног OCO. Возвращает (цена, причина) или None."""
    for oid in p["oco"]["order_ids"]:
        o = ex.fetch_order(oid, sym)
        if o["status"] == "closed" and float(o["filled"] or 0) > 0:
            px = float(o["average"] or o["price"])
            why = "take" if abs(px - p["oco"]["tp"]) < abs(px - p["oco"]["sl"]) else "stop"
            return px, why
    return None


# ─────────────────────────── один проход ───────────────────────────
def equity(ex, s, last_px):
    if MODE == "dry":
        cash = s.get("cash", 100.0)
    else:
        cash = float(ex.fetch_balance()["free"].get("USDT", 0))
    return cash + sum(p["qty"] * last_px.get(p["sym"], p["entry"]) for p in s["positions"])


def step(ex, s):
    candles = {}
    for sym in SYMS:
        try:
            candles[sym] = closed_candles(ex, sym, MOM_BARS + 2)
        except Exception as e:
            log(f"  {sym}: свечи недоступны ({e})")
    last_px = {sym: rows[-1][4] for sym, rows in candles.items() if rows}

    # 1. выходы
    keep = []
    for p in s["positions"]:
        sym = p["sym"]
        if MODE == "dry":
            rows = candles.get(sym)
            if not rows:
                keep.append(p); continue
            _, o, h, l, c, _ = rows[-1]
            if l <= p["sl"]:      px, why = p["sl"], "stop"
            elif h >= p["tp"]:    px, why = p["tp"], "take"
            elif age_h(p) >= MAX_HOLD_H: px, why = c, "time"
            else:
                keep.append(p); continue
            s["cash"] = s.get("cash", 100.0) + p["qty"] * px * (1 - FEE)
            record_exit(s, p, px, why)
        else:
            try:
                hit = check_oco(ex, sym, p)
                if hit:
                    record_exit(s, p, hit[0], hit[1]); continue
                if age_h(p) >= MAX_HOLD_H:
                    px = cancel_oco_and_sell(ex, sym, p)
                    if px: record_exit(s, p, px, "time"); continue
            except Exception as e:
                log(f"  {sym}: проверка выхода не удалась ({e})")
            keep.append(p)
    s["positions"] = keep

    # 2. дневной предохранитель
    eq = equity(ex, s, last_px)
    today = dt.datetime.now(UTC).date().isoformat()
    if s.get("day") != today:
        s["day"], s["day_start_eq"], s["halted"] = today, eq, False
    if eq < s["day_start_eq"] * (1 - DAY_STOP):
        if not s["halted"]:
            log(f"СТОП НА СЕГОДНЯ: капитал ${eq:.2f} ниже {DAY_STOP*100:.0f}% от утреннего ${s['day_start_eq']:.2f}")
        s["halted"] = True

    # 3. входы
    if not s["halted"]:
        held = {p["sym"] for p in s["positions"]}
        cands = []
        for sym, rows in candles.items():
            if sym in held: continue
            mom = momentum(rows)
            if mom is not None and mom >= MOM_PCT:
                cands.append((mom, sym))
        cands.sort(reverse=True)
        for mom, sym in cands:
            if len(s["positions"]) >= MAX_POS: break
            if MODE == "dry":
                if s.get("cash", 100.0) < LOT: break
                px = last_px[sym]
                qty = LOT * (1 - FEE) / px
                s["cash"] = s.get("cash", 100.0) - LOT
                s["positions"].append({"sym": sym, "qty": qty, "entry": px, "cost": LOT,
                                       "tp": px * (1 + TP), "sl": px * (1 - SL), "t": now_iso()})
                log(f"ВХОД  {sym:<9} импульс {mom*100:+.2f}%  по {px:.6g}  (симуляция)")
            else:
                try:
                    free = float(ex.fetch_balance()["free"].get("USDT", 0))
                    if free < LOT: log("  USDT кончились"); break
                    qty, avg, cost = market_buy(ex, sym)
                    if qty <= 0: continue
                    oco = place_oco(ex, sym, qty, avg)
                    s["positions"].append({"sym": sym, "qty": oco["qty"], "entry": avg, "cost": cost,
                                           "tp": oco["tp"], "sl": oco["sl"], "t": now_iso(), "oco": oco})
                    log(f"ВХОД  {sym:<9} импульс {mom*100:+.2f}%  по {avg:.6g}  "
                        f"OCO тейк {oco['tp']:.6g} / стоп {oco['sl']:.6g}")
                except Exception as e:
                    log(f"  {sym}: вход не удался ({e})")

    save_state(s)
    n = len(s["trades"]); w = sum(1 for t in s["trades"] if t["pnl_usd"] > 0)
    log(f"капитал ${eq:.2f}  позиций {len(s['positions'])}/{MAX_POS}  "
        f"закрыто {n}  win {w/n*100 if n else 0:.0f}%  режим {MODE}")


def sleep_to_next_bar():
    now = time.time()
    nxt = (math.floor(now / 300) + 1) * 300 + 10       # +10 с, чтобы свеча точно закрылась
    time.sleep(max(nxt - now, 1))


if __name__ == "__main__":
    log(f"старт · режим {MODE} · {len(SYMS)} пар · лот ${LOT} · слотов {MAX_POS} · "
        f"тейк +{TP*100:.1f}% стоп −{SL*100:.1f}% · время-стоп {MAX_HOLD_H:.0f}ч")
    if MODE == "live":
        log("ВНИМАНИЕ: РЕАЛЬНЫЕ ДЕНЬГИ. Остановить: Ctrl+C. Открытые OCO останутся на бирже.")
    ex = make_exchange()
    state = load_state()
    once = "--once" in sys.argv
    while True:
        try:
            step(ex, state)
        except Exception as e:
            log(f"ошибка прохода: {e}")
        if once:
            break
        sleep_to_next_bar()
