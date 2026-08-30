#!/usr/bin/env python3
"""
Проверка «рискованной» стратегии: покупать вчерашних неудачников.
Тот же портфельный движок, что на платформе: $100, лот $10, макс 5 позиций,
тейк +4%, стоп -12%, время-стоп 5-й день, комиссия 0.1%, вход на открытии.
Меняется только СИГНАЛ входа.
"""
import json, datetime as dt
from data import fetch

FEE, LOT, MAX_POS = 0.001, 10.0, 5
TP, SL, HOLD, RSI_WIN = 0.04, 0.12, 5, 250
EXCLUDE = {"EURUSDT", "WBTCUSDT"}


def wilder_rsi(closes):
    n = 14
    if len(closes) < n+1: return None
    au = sum(max(closes[i]-closes[i-1],0.0) for i in range(1,n+1))/n
    ad = sum(max(closes[i-1]-closes[i],0.0) for i in range(1,n+1))/n
    for i in range(n+1, len(closes)):
        au = (au*(n-1)+max(closes[i]-closes[i-1],0.0))/n
        ad = (ad*(n-1)+max(closes[i-1]-closes[i],0.0))/n
    return 100.0 if ad == 0 else 100.0-100.0/(1.0+au/ad)


def load(start):
    syms = [s for s in json.load(open("liquid.json")) if s not in EXCLUDE]
    data = {}
    for s in syms:
        c = fetch(s)
        rows = [{"d": dt.datetime.utcfromtimestamp(k["t"]/1000).date().isoformat(),
                 "o":k["o"],"h":k["h"],"l":k["l"],"c":k["c"],"v":k["v"]} for k in c]
        data[s] = rows
    return data


def portfolio(data, start, signal_fn, hold=HOLD, sl=SL):
    """signal_fn(data, idx, day) -> [(priority, sym), ...] отсортированный."""
    idx = {s: {b["d"]: i for i, b in enumerate(rows)} for s, rows in data.items()}
    btc = data["BTCUSDT"]
    days = [b["d"] for b in btc if b["d"] > start]
    cash, positions, trades = 100.0, [], []
    peak, maxdd = 100.0, 0.0
    bench_qty = None
    for day in days:
        cands = signal_fn(data, idx, day)
        held = {p["sym"] for p in positions}
        for _, sym in cands:
            if len(positions) >= MAX_POS or cash < LOT: break
            if sym in held: continue
            i = idx[sym].get(day)
            if i is None: continue
            px = data[sym][i]["o"]
            positions.append({"sym":sym,"day":day,"px":px,"qty":LOT*(1-FEE)/px,
                              "t":px*(1+TP),"s":px*(1-sl)})
            cash -= LOT; held.add(sym)
        still = []
        for p in positions:
            i = idx[p["sym"]].get(day)
            if i is None: still.append(p); continue
            bar = data[p["sym"]][i]
            age = (dt.date.fromisoformat(day)-dt.date.fromisoformat(p["day"])).days
            ex = None
            if bar["l"] <= p["s"]: ex, why = p["s"], "stop"
            elif bar["h"] >= p["t"]: ex, why = p["t"], "take"
            elif age >= hold-1: ex, why = bar["c"], "time"
            if ex is None: still.append(p)
            else:
                pr = p["qty"]*ex*(1-FEE); cash += pr
                trades.append(pr-LOT)
        positions = still
        ib = idx["BTCUSDT"].get(day)
        if bench_qty is None and ib is not None:
            bench_qty = 100.0*(1-FEE)/btc[ib]["o"]
        mark = cash + sum(p["qty"]*data[p["sym"]][idx[p["sym"]][day]]["c"]
                          for p in positions if day in idx[p["sym"]])
        peak = max(peak, mark); maxdd = max(maxdd, (peak-mark)/peak)
    last = days[-1]
    mark = cash + sum(p["qty"]*data[p["sym"]][idx[p["sym"]][last]]["c"]
                      for p in positions if last in idx[p["sym"]])
    bench = bench_qty*btc[idx["BTCUSDT"][last]]["c"]
    yrs = (dt.date.fromisoformat(last)-dt.date.fromisoformat(start)).days/365.25
    wins = sum(1 for t in trades if t > 0)
    return {"eq": mark, "apy": ((mark/100)**(1/yrs)-1)*100, "dd": maxdd*100,
            "n": len(trades), "win": wins/len(trades)*100 if trades else 0,
            "bench": bench, "bench_apy": ((bench/100)**(1/yrs)-1)*100}


# ---- сигналы ----
def sig_dip(th):
    """твоя схема: вчера упала на th% и больше; приоритет — кто сильнее упал"""
    def f(data, idx, day):
        out = []
        for s, rows in data.items():
            i = idx[s].get(day)
            if i is None or i < 2: continue
            r = rows[i-1]["c"]/rows[i-2]["c"] - 1
            if r <= -th/100: out.append((r, s))
        out.sort()
        return out
    return f

def sig_worst1(data, idx, day):
    """каждый день покупаем одну самую упавшую вчера"""
    out = []
    for s, rows in data.items():
        i = idx[s].get(day)
        if i is None or i < 2: continue
        out.append((rows[i-1]["c"]/rows[i-2]["c"]-1, s))
    out.sort()
    return out[:1]

def sig_rsi(data, idx, day):
    """наша текущая (сигнал B) для сравнения в том же движке"""
    out = []
    for s, rows in data.items():
        i = idx[s].get(day)
        if i is None or i < RSI_WIN: continue
        r = wilder_rsi([x["c"] for x in rows[i-RSI_WIN:i]])
        if r is not None and r < 30: out.append((r, s))
    out.sort()
    return out


if __name__ == "__main__":
    START = "2022-01-01"
    data = load(START)
    print(f"\n  ПОРТФЕЛЬ $100 НА 24 ЛИКВИДНЫХ ПАРАХ, {START} -> сегодня")
    print(f"  одинаковые правила выхода: тейк+4% / стоп-12% / 5 дней")
    print("  " + "="*72)
    print(f"    {'вход':<34}{'итог':>8}{'годовых':>9}{'просадка':>10}{'сделок':>8}{'win':>6}")
    tests = [
        ("упала вчера на 3%+", sig_dip(3)),
        ("упала вчера на 5%+", sig_dip(5)),
        ("упала вчера на 8%+", sig_dip(8)),
        ("самая упавшая вчера (каждый день)", sig_worst1),
        ("наша: RSI14 < 30", sig_rsi),
    ]
    bench_shown = False
    for name, fn in tests:
        r = portfolio(data, START, fn)
        print(f"    {name:<34}{r['eq']:>7.0f}${r['apy']:>+8.1f}%{r['dd']:>9.0f}%"
              f"{r['n']:>8}{r['win']:>5.0f}%")
        if not bench_shown:
            print(f"    {'(бенчмарк: $100 в BTC)':<34}{r['bench']:>7.0f}$"
                  f"{r['bench_apy']:>+8.1f}%")
            bench_shown = True
