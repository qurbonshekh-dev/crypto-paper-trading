#!/usr/bin/env python3
"""
Paper trading — стратегия из fair.py на живых данных, деньги виртуальные.

Логика 1:1 с бэктестом:
  вход  — на открытии дня UTC, если позиции нет и цена выше MA200
  выход — по тейку +3.5% (лимитный ордер живёт всё время удержания)
          либо по закрытию дня через 3 дня после входа

Состояние переживает перезапуск. Пропущенные дни доигрываются
по реальным историческим свечам и помечаются в журнале как replay.

  python3 paper.py                    # запуск / продолжение
  python3 paper.py --reset --balance 1000
"""
import argparse
import asyncio
import csv
import datetime as dt
import json
import os
import urllib.request

import websockets

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_F = os.path.join(HERE, "paper_state.json")
JOURNAL = os.path.join(HERE, "paper_journal.csv")

SYMBOL = "BTCUSDT"   # переопределяется аргументами командной строки
TP = 0.035           # тейк-профит
HOLD = 3             # дней удержания
MA_LEN = 200         # 0 = торговать без фильтра
FEE = 0.001          # 0.1% на сторону

UTC = dt.timezone.utc
JOURNAL_COLS = ["ts", "day", "action", "reason", "price", "qty",
                "cash", "equity", "pnl_pct", "mode"]


# ---------------------------------------------------------------- данные
def klines(symbol, limit=260):
    """Свежие дневные свечи, без кэша — нужны актуальные."""
    url = (f"https://api.binance.com/api/v3/klines"
           f"?symbol={symbol}&interval=1d&limit={limit}")
    with urllib.request.urlopen(url, timeout=20) as r:
        raw = json.load(r)
    return [{"day": dt.datetime.fromtimestamp(k[0] / 1000, UTC).date(),
             "o": float(k[1]), "h": float(k[2]),
             "l": float(k[3]), "c": float(k[4])} for k in raw]


def ma_before(candles, day, extra_close=None):
    """
    MA200 по завершённым дням СТРОГО до `day`. Без подглядывания в будущее.
    extra_close — закрытие дня (day-1), если оно уже известно, но в `candles`
    ещё не финализировано биржей. Так граница суток не зависит от гонки с API.
    """
    if MA_LEN == 0:
        return 0.0                      # фильтр выключен — вход разрешён всегда
    prev = day - dt.timedelta(days=1)
    closes = [c["c"] for c in candles if c["day"] < (prev if extra_close else day)]
    if extra_close is not None:
        closes.append(extra_close)
    return sum(closes[-MA_LEN:]) / MA_LEN if len(closes) >= MA_LEN else None


# ---------------------------------------------------------------- состояние
def load_state(reset, balance):
    if not reset and os.path.exists(STATE_F):
        with open(STATE_F) as f:
            return json.load(f)
    return {"cash": balance, "coin": 0.0, "entry_px": None, "target": None,
            "entry_day": None, "exit_day": None, "last_day": None,
            "start_equity": balance,
            "started": dt.datetime.now(UTC).isoformat(timespec="seconds")}


def save_state(s):
    tmp = STATE_F + ".tmp"
    with open(tmp, "w") as f:
        json.dump(s, f, indent=2, default=str)
    os.replace(tmp, STATE_F)          # атомарно: не потеряем при обрыве


def journal(row):
    new = not os.path.exists(JOURNAL)
    with open(JOURNAL, "a", newline="") as f:
        w = csv.DictWriter(f, JOURNAL_COLS)
        if new:
            w.writeheader()
        w.writerow(row)


# ---------------------------------------------------------------- сделки
def buy(s, price, day, mode):
    s["coin"] = s["cash"] * (1 - FEE) / price
    s["cash"] = 0.0
    s["entry_px"] = price
    s["target"] = price * (1 + TP)
    s["entry_day"] = str(day)
    s["exit_day"] = str(day + dt.timedelta(days=HOLD))
    eq = s["coin"] * price
    journal({"ts": dt.datetime.now(UTC).isoformat(timespec="seconds"), "day": day,
             "action": "BUY", "reason": "ma200_ok", "price": round(price, 2),
             "qty": round(s["coin"], 8), "cash": 0.0, "equity": round(eq, 2),
             "pnl_pct": "", "mode": mode})
    return f"BUY  {price:,.2f}  цель {s['target']:,.2f}  выход не позже {s['exit_day']}"


def sell(s, price, day, reason, mode):
    entry = s["entry_px"]
    s["cash"] = s["coin"] * price * (1 - FEE)
    pnl = (price * (1 - FEE)) / (entry * (1 + FEE)) - 1
    qty, s["coin"] = s["coin"], 0.0
    s["entry_px"] = s["target"] = s["entry_day"] = s["exit_day"] = None
    journal({"ts": dt.datetime.now(UTC).isoformat(timespec="seconds"), "day": day,
             "action": "SELL", "reason": reason, "price": round(price, 2),
             "qty": round(qty, 8), "cash": round(s["cash"], 2),
             "equity": round(s["cash"], 2), "pnl_pct": round(pnl * 100, 3),
             "mode": mode})
    return f"SELL {price:,.2f}  ({reason})  сделка {pnl*100:+.2f}%"


# ------------------------------------------------------- граница суток UTC
def day_boundary(s, day_closed, close_px, candles, mode, log):
    """
    Отработка полуночи UTC: день day_closed закрылся по close_px,
    открывается следующий. Порядок как в бэктесте: сначала выход, потом вход.
    """
    nxt = day_closed + dt.timedelta(days=1)

    if s["coin"] > 0 and s["exit_day"] and day_closed >= dt.date.fromisoformat(s["exit_day"]):
        log(sell(s, close_px, day_closed, "time", mode))

    if s["coin"] == 0:
        m = ma_before(candles, nxt, extra_close=close_px)
        if m is None:
            log(f"{nxt}: недостаточно истории для MA200, пропуск")
        elif close_px > m:
            log(buy(s, close_px, nxt, mode))
        else:
            log(f"{nxt}: цена {close_px:,.0f} ниже MA200 {m:,.0f} — вне рынка")

    s["last_day"] = str(day_closed)
    save_state(s)


def catch_up(s, candles, log):
    """Доиграть дни, пропущенные пока процесс не работал."""
    today = dt.datetime.now(UTC).date()
    done = [c for c in candles if c["day"] < today]        # только закрытые дни
    if not done:
        return
    if s["last_day"] is None:
        s["last_day"] = str(done[-1]["day"] - dt.timedelta(days=1))
    last = dt.date.fromisoformat(s["last_day"])

    missed = [c for c in done if c["day"] > last]
    if not missed:
        return
    log(f"доигрываю пропущенных дней: {len(missed)} (по историческим свечам)")
    for c in missed:
        # тейк мог сработать внутри пропущенного дня — проверяем по максимуму
        if s["coin"] > 0 and s["target"] and c["h"] >= s["target"]:
            log(sell(s, s["target"], c["day"], "take", "replay"))
        day_boundary(s, c["day"], c["c"], candles, "replay", log)


# ---------------------------------------------------------------- дисплей
def render(s, price, candles, events):
    print("\033[2J\033[H", end="")   # очистка экрана без подпроцесса
    eq = s["cash"] + s["coin"] * price
    total = (eq / s["start_equity"] - 1) * 100
    now = dt.datetime.now(UTC)
    print(f"  PAPER TRADING · {SYMBOL} · TP+{TP*100:.1f}% / {HOLD}д / MA{MA_LEN}")
    print(f"  {now:%Y-%m-%d %H:%M:%S} UTC   старт {s['started'][:10]}   ВИРТУАЛЬНЫЕ ДЕНЬГИ\n")
    print(f"    цена            {price:>14,.2f}")
    m = ma_before(candles, now.date())
    if m:
        rel = "выше ✓" if price > m else "ниже ✗"
        print(f"    MA200           {m:>14,.2f}   цена {rel}")
    print()
    if s["coin"] > 0:
        upnl = (price * (1-FEE)) / (s["entry_px"] * (1+FEE)) - 1
        col = "\033[32m" if upnl >= 0 else "\033[31m"
        left = (dt.date.fromisoformat(s["exit_day"]) - now.date()).days
        print(f"    В ПОЗИЦИИ  вход {s['entry_px']:,.2f}  →  цель {s['target']:,.2f}")
        print(f"    сейчас {col}{upnl*100:+.2f}%\033[0m   до цели "
              f"{(s['target']/price-1)*100:+.2f}%   выход по времени через {left} дн.")
    else:
        print(f"    ВНЕ РЫНКА   {s['cash']:,.2f} USDT ждут открытия дня")
    print(f"\n    капитал {eq:>12,.2f}   всего {total:+.2f}%")
    print("\n  " + "-" * 60)
    for e in events[-8:]:
        print(f"    {e}")
    print("\n  Ctrl+C — выход, состояние сохранится")


# ---------------------------------------------------------------- главный цикл
async def main(s):
    events = []
    candles = klines(SYMBOL)

    def log(msg):
        stamp = dt.datetime.now(UTC).strftime("%m-%d %H:%M")
        events.append(f"{stamp}  {msg}")

    catch_up(s, candles, log)
    save_state(s)

    url = f"wss://stream.binance.com:9443/ws/{SYMBOL.lower()}@miniTicker"
    delay = 2
    cur_day = dt.datetime.now(UTC).date()
    last_draw = 0.0

    while True:
        try:
            async with websockets.connect(url, ping_interval=20) as ws:
                delay = 2
                log("подключено к потоку Binance")
                async for raw in ws:
                    price = float(json.loads(raw)["c"])
                    now = dt.datetime.now(UTC)

                    # полночь UTC: день закрылся
                    if now.date() > cur_day:
                        candles = klines(SYMBOL)          # обновляем историю для MA
                        day_boundary(s, cur_day, price, candles, "live", log)
                        cur_day = now.date()

                    # тейк-профит — лимитный ордер, срабатывает в любой момент
                    if s["coin"] > 0 and price >= s["target"]:
                        log(sell(s, s["target"], now.date(), "take", "live"))
                        save_state(s)

                    if now.timestamp() - last_draw > 1.0:
                        render(s, price, candles, events)
                        last_draw = now.timestamp()

        except (websockets.ConnectionClosed, OSError, asyncio.TimeoutError) as e:
            log(f"обрыв ({type(e).__name__}), переподключение через {delay}с")
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="начать заново")
    ap.add_argument("--balance", type=float, default=1000.0, help="стартовый капитал")
    ap.add_argument("--symbol", default=SYMBOL, help="пара, напр. ETHUSDT")
    ap.add_argument("--tp", type=float, default=TP*100, help="тейк-профит, %%")
    ap.add_argument("--hold", type=int, default=HOLD, help="дней удержания")
    ap.add_argument("--ma", type=int, default=MA_LEN, help="период фильтра, 0 = без фильтра")
    ap.add_argument("--fee", type=float, default=FEE*100, help="комиссия за сторону, %%")
    a = ap.parse_args()

    SYMBOL, TP, HOLD, MA_LEN, FEE = a.symbol, a.tp/100, a.hold, a.ma, a.fee/100
    STATE_F = os.path.join(HERE, f"paper_state_{SYMBOL}.json")
    JOURNAL = os.path.join(HERE, f"paper_journal_{SYMBOL}.csv")
    print(f"  {SYMBOL}  TP+{TP*100:g}%  {HOLD}д  "
          f"{'MA'+str(MA_LEN) if MA_LEN else 'без фильтра'}  комиссия {FEE*100:g}%")

    if a.reset and os.path.exists(JOURNAL):
        os.replace(JOURNAL, JOURNAL + ".bak")
        print("старый журнал переименован в paper_journal.csv.bak")

    st = load_state(a.reset, a.balance)
    try:
        asyncio.run(main(st))
    except KeyboardInterrupt:
        save_state(st)
        print("\nсостояние сохранено в paper_state.json")
