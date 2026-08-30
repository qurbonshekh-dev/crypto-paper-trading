#!/usr/bin/env python3
"""
Журнал РЕАЛЬНЫХ сделок месячного теста ($100).
Сделки совершаешь ты на бирже; сюда записываешь факт — сразу после исполнения.

  python3 journal.py buy  SOLUSDT 10 101.84   # купил на 10 USDT по 101.84
  python3 journal.py sell SOLUSDT 105.90      # продал самый старый лот по 105.90
  python3 journal.py status                   # открытые позиции + текущий P&L
  python3 journal.py report                   # итог теста против бенчмарка
"""
import csv, json, os, sys, datetime as dt, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(HERE, "real_journal.csv")
FEE = 0.001
COLS = ["ts", "action", "symbol", "usd", "price", "qty", "pnl_pct", "pnl_usd"]
UTC = dt.timezone.utc


def now():
    return dt.datetime.now(UTC).isoformat(timespec="seconds")


def rows():
    if not os.path.exists(F):
        return []
    return list(csv.DictReader(open(F)))


def append(row):
    new = not os.path.exists(F)
    with open(F, "a", newline="") as f:
        w = csv.DictWriter(f, COLS)
        if new:
            w.writeheader()
        w.writerow(row)


def price_now(sym):
    u = f"https://api.binance.com/api/v3/ticker/price?symbol={sym}"
    with urllib.request.urlopen(u, timeout=15) as r:
        return float(json.load(r)["price"])


def open_lots(rs):
    """FIFO: непроданные покупки."""
    lots = []
    for r in rs:
        if r["action"] == "BUY":
            lots.append(dict(r))
        elif r["action"] == "SELL":
            for l in lots:
                if l["symbol"] == r["symbol"]:
                    lots.remove(l)
                    break
    return lots


def cmd_buy(sym, usd, price):
    usd, price = float(usd), float(price)
    rs = rows()
    if not rs:                                     # бенчмарк фиксируем при 1-й сделке
        append({"ts": now(), "action": "BENCH", "symbol": "BTCUSDT",
                "usd": 100, "price": price_now("BTCUSDT"), "qty": "",
                "pnl_pct": "", "pnl_usd": ""})
    append({"ts": now(), "action": "BUY", "symbol": sym, "usd": usd,
            "price": price, "qty": round(usd/price, 8), "pnl_pct": "", "pnl_usd": ""})
    print(f"записано: BUY {sym} на {usd} USDT по {price}")


def cmd_sell(sym, price):
    price = float(price)
    lots = [l for l in open_lots(rows()) if l["symbol"] == sym]
    if not lots:
        sys.exit(f"нет открытого лота {sym}")
    l = lots[0]
    entry, usd = float(l["price"]), float(l["usd"])
    pnl = (price*(1-FEE))/(entry*(1+FEE)) - 1
    append({"ts": now(), "action": "SELL", "symbol": sym, "usd": round(usd*(1+pnl), 2),
            "price": price, "qty": l["qty"],
            "pnl_pct": round(pnl*100, 3), "pnl_usd": round(usd*pnl, 3)})
    held = (dt.datetime.fromisoformat(now()) - dt.datetime.fromisoformat(l["ts"])).days
    print(f"записано: SELL {sym} по {price}  →  {pnl*100:+.2f}% "
          f"({usd*pnl:+.2f} USDT), держал {held} дн.")


def cmd_status():
    rs = rows()
    lots = open_lots(rs)
    print(f"\n  ОТКРЫТЫЕ ПОЗИЦИИ ({len(lots)})")
    unreal = 0.0
    for l in lots:
        p = price_now(l["symbol"])
        entry, usd = float(l["price"]), float(l["usd"])
        pnl = (p*(1-FEE))/(entry*(1+FEE)) - 1
        unreal += usd*pnl
        age = (dt.datetime.now(UTC) - dt.datetime.fromisoformat(l["ts"])).days
        flag = "  <-- 5-й день, пора закрывать" if age >= 5 else ""
        print(f"    {l['symbol']:<12} вход {entry:,.6g}  сейчас {p:,.6g}  "
              f"{pnl*100:+6.2f}%  ({usd*pnl:+.2f} USDT)  {age} дн.{flag}")
    real = sum(float(r["pnl_usd"]) for r in rs if r["action"] == "SELL")
    print(f"\n  реализовано {real:+.2f} USDT   нереализовано {unreal:+.2f} USDT")


def cmd_report():
    rs = rows()
    sells = [r for r in rs if r["action"] == "SELL"]
    bench = next((r for r in rs if r["action"] == "BENCH"), None)
    print(f"\n  ОТЧЁТ МЕСЯЧНОГО ТЕСТА")
    print("  " + "=" * 56)
    if not rs:
        sys.exit("  журнал пуст")
    t0 = dt.datetime.fromisoformat(rs[0]["ts"])
    days = max((dt.datetime.now(UTC) - t0).days, 1)
    print(f"  период: {t0.date()} → сегодня  ({days} дн.)")
    real = sum(float(r["pnl_usd"]) for r in sells)
    unreal = 0.0
    for l in open_lots(rs):
        p = price_now(l["symbol"])
        unreal += float(l["usd"]) * ((p*(1-FEE))/(float(l["price"])*(1+FEE)) - 1)
    if sells:
        pnls = [float(r["pnl_pct"]) for r in sells]
        wins = sum(1 for p in pnls if p > 0)
        print(f"  закрыто сделок: {len(sells)}, прибыльных {wins} "
              f"({wins/len(sells)*100:.0f}%), средняя {sum(pnls)/len(pnls):+.2f}%")
    print(f"  реализовано:    {real:+.2f} USDT")
    print(f"  нереализовано:  {unreal:+.2f} USDT")
    print(f"  ИТОГ на $100:   {real+unreal:+.2f} USDT  ({(real+unreal):+.1f}%)")
    if bench:
        b0, b1 = float(bench["price"]), price_now("BTCUSDT")
        print(f"  бенчмарк — просто держать BTC с первой сделки: "
              f"{(b1/b0-1)*100:+.2f}%")
    print(f"\n  помни: итог одного месяца — это одна случайная выборка,")
    print(f"  а не 'сколько можно зарабатывать'.")


if __name__ == "__main__":
    a = sys.argv[1:] or ["status"]
    try:
        {"buy": lambda: cmd_buy(*a[1:4]), "sell": lambda: cmd_sell(*a[1:3]),
         "status": cmd_status, "report": cmd_report}[a[0]]()
    except KeyError:
        sys.exit(__doc__)
