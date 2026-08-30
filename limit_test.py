#!/usr/bin/env python3
"""
Вариант дип-стратегии: лимитная покупка ВНУТРИ дня на -X% от вчерашнего закрытия.
Исполнение: если минимум дня коснулся лимита — куплены по цене лимита.
Консервативно: у позиций, открытых сегодня, выходы проверяются только с завтра.
Тот же движок: $100, лот $10, 5 слотов, тейк +4%, стоп -12%, 5 дней, 0.1%.
"""
import json, datetime as dt
from risky_test import load, FEE, LOT, MAX_POS, TP, SL, HOLD


def portfolio_limit(data, start, th):
    idx = {s: {b["d"]: i for i, b in enumerate(rows)} for s, rows in data.items()}
    btc = data["BTCUSDT"]
    days = [b["d"] for b in btc if b["d"] > start]
    cash, positions, trades = 100.0, [], []
    peak, maxdd, bench_qty = 100.0, 0.0, None

    for day in days:
        # --- заявки на сегодня: слоты и кэш на утро, до сегодняшних выходов ---
        held = {p["sym"] for p in positions}
        slots = MAX_POS - len(positions)
        cands = []
        for s, rows in data.items():
            if s in held: continue
            i = idx[s].get(day)
            if i is None or i < 2: continue
            prev = rows[i-1]["c"]
            limit = prev * (1 - th/100)
            if rows[i]["l"] <= limit:                      # лимитка исполнилась
                cands.append((rows[i]["l"]/prev - 1, s, limit))   # приоритет: глубже упала
        cands.sort()
        newpos = []
        for _, s, limit in cands:
            if slots <= 0 or cash < LOT: break
            newpos.append({"sym": s, "day": day, "px": limit,
                           "qty": LOT*(1-FEE)/limit,
                           "t": limit*(1+TP), "s": limit*(1-SL)})
            cash -= LOT; slots -= 1

        # --- выходы только для старых позиций ---
        still = []
        for p in positions:
            i = idx[p["sym"]].get(day)
            if i is None: still.append(p); continue
            bar = data[p["sym"]][i]
            age = (dt.date.fromisoformat(day)-dt.date.fromisoformat(p["day"])).days
            ex = None
            if bar["l"] <= p["s"]: ex = p["s"]
            elif bar["h"] >= p["t"]: ex = p["t"]
            elif age >= HOLD-1: ex = bar["c"]
            if ex is None: still.append(p)
            else:
                pr = p["qty"]*ex*(1-FEE); cash += pr; trades.append(pr-LOT)
        positions = still + newpos

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
            "n": len(trades), "win": wins/len(trades)*100 if trades else 0, "bench": bench}


if __name__ == "__main__":
    START = "2022-01-01"
    data = load(START)
    print(f"\n  ЛИМИТКА ВНУТРИ ДНЯ НА -X% ОТ ВЧЕРАШНЕГО ЗАКРЫТИЯ ({START} -> сегодня)")
    print("  " + "="*70)
    print(f"    {'порог':<28}{'итог':>8}{'годовых':>9}{'просадка':>10}{'сделок':>8}{'win':>6}")
    for th in (3, 5, 8, 12):
        r = portfolio_limit(data, START, th)
        print(f"    лимит -{th}% внутри дня{'':<8}{r['eq']:>7.0f}${r['apy']:>+8.1f}%"
              f"{r['dd']:>9.0f}%{r['n']:>8}{r['win']:>5.0f}%")
    print(f"\n    для сравнения (из прошлого прогона):")
    print(f"    {'дип-закрытие -5% (наш счёт 2)':<28}{25:>7}${-26.0:>+8.1f}%{80:>9}%{1425:>8}{68:>5}%")
    print(f"    {'$100 в BTC':<28}{169:>7}${12.0:>+8.1f}%")
