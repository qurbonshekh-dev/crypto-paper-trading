#!/usr/bin/env python3
"""Что реально сдвинет частую торговлю в плюс: перебор на 5-минутных свечах OKX."""
import os, json, time, datetime as dt
import okx_data

CACHE = "cache5m"
FEE_REAL = 0.00075
LOT, UTC = 10.0, dt.timezone.utc
PAIRS = ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","BNBUSDT","DOGEUSDT","ADAUSDT",
         "AVAXUSDT","LINKUSDT","LTCUSDT","BCHUSDT","TRXUSDT","ZECUSDT","WLDUSDT","SUIUSDT"]


def load(sym, bars=8000):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, f"{sym}.json")
    if os.path.exists(p):
        return json.load(open(p))
    r = okx_data.candles(sym, "5m", bars)
    json.dump(r, open(p, "w"))
    time.sleep(0.1)
    return r


def run(data, tp, sl, mom_bars, mom_pct, maxpos, fee, max_hold=288):
    syms = list(data)
    n = min(len(data[s]) for s in syms)
    cash, pos, tr = 100.0, [], []
    for i in range(mom_bars + 1, n):
        keep = []
        for p in pos:
            b = data[p["s"]][i]
            ex = None
            if b["l"] <= p["sl"]:        ex = p["sl"]
            elif b["h"] >= p["tp"]:      ex = p["tp"]
            elif i - p["i"] >= max_hold: ex = b["c"]
            if ex is None: keep.append(p)
            else:
                pr = p["q"] * ex * (1 - fee); cash += pr; tr.append(pr - LOT)
        pos = keep
        if len(pos) < maxpos and cash >= LOT:
            held = {p["s"] for p in pos}
            cand = []
            for s in syms:
                if s in held: continue
                r = data[s]; base = r[i-1-mom_bars]["c"]
                if base > 0 and r[i-1]["c"]/base - 1 >= mom_pct/100:
                    cand.append((r[i-1]["c"]/base - 1, s))
            cand.sort(reverse=True)
            for _, s in cand:
                if len(pos) >= maxpos or cash < LOT: break
                px = data[s][i]["o"]; cash -= LOT
                pos.append({"s":s,"i":i,"q":LOT*(1-fee)/px,
                            "tp":px*(1+tp/100),"sl":px*(1-sl/100)})
    eq = cash + sum(p["q"]*data[p["s"]][n-1]["c"] for p in pos)
    w = sum(1 for x in tr if x > 0)
    return eq, len(tr), (w/len(tr)*100 if tr else 0)


if __name__ == "__main__":
    data = {s: load(s) for s in PAIRS}
    n = min(len(v) for v in data.values())
    days = n*5/60/24
    print(f"  данные: {len(data)} пар, {n} 5-мин свечей ≈ {days:.0f} дней\n")

    base = run(data, 1.5, 1.0, 12, 1.0, 10, FEE_REAL)
    print(f"  ТЕКУЩИЕ ПРАВИЛА (тейк 1.5 / стоп 1 / имп 1% / 10 слотов)")
    print(f"    ${base[0]:.2f}  сделок {base[1]}  ({base[1]/days:.0f}/день)  win {base[2]:.0f}%\n")

    print("  А. ШИРЕ СТОП — чтобы шум не выбивал (тейк 1.5%)")
    print("  " + "-"*62)
    for sl in (1.0, 1.5, 2.0, 3.0):
        eq, n_, w = run(data, 1.5, sl, 12, 1.0, 10, FEE_REAL)
        print(f"    стоп {sl}%   ${eq:>6.2f}  сделок {n_:>4} ({n_/days:>3.0f}/д)  win {w:>3.0f}%")

    print("\n  Б. ШИРЕ ЦЕЛЬ — реже сделки, меньше комиссий (стоп 1%)")
    print("  " + "-"*62)
    for tp in (1.5, 2.5, 4.0, 6.0):
        eq, n_, w = run(data, tp, 1.0, 12, 1.0, 10, FEE_REAL)
        print(f"    тейк {tp}%   ${eq:>6.2f}  сделок {n_:>4} ({n_/days:>3.0f}/д)  win {w:>3.0f}%")

    print("\n  В. СТРОЖЕ ВХОД — только сильный импульс")
    print("  " + "-"*62)
    for mp in (1.0, 2.0, 3.0, 4.0):
        eq, n_, w = run(data, 1.5, 1.0, 12, mp, 10, FEE_REAL)
        print(f"    импульс {mp}%  ${eq:>6.2f}  сделок {n_:>4} ({n_/days:>3.0f}/д)  win {w:>3.0f}%")

    print("\n  Г. СИММЕТРИЧНО ШИРЕ (реже + больше цель + шире стоп)")
    print("  " + "-"*62)
    for tp, sl, mp in ((3.0,2.0,2.0),(4.0,2.0,2.0),(4.0,3.0,3.0),(6.0,3.0,3.0),(8.0,4.0,3.0)):
        eq, n_, w = run(data, tp, sl, 12, mp, 10, FEE_REAL)
        print(f"    тейк{tp}/стоп{sl}/имп{mp}  ${eq:>6.2f}  сделок {n_:>4} ({n_/days:>4.1f}/д)  win {w:>3.0f}%")

    hold = 100*(1-FEE_REAL)/data["BTCUSDT"][0]["o"]*data["BTCUSDT"][n-1]["c"]
    print(f"\n  эталон: $100 в BTC за тот же период → ${hold:.2f}")
