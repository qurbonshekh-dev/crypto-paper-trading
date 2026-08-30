#!/usr/bin/env python3
"""
Проверка идеи «много мелких сделок»: вход по импульсу, тейк +1.5%, стоп -1%.
Данные — 15-минутные свечи Binance (внутри дня), 2 месяца, 15 ликвидных пар.
"""
import json, os, time, urllib.request, datetime as dt

CACHE = "cache15m"
FEE, LOT, MAXPOS = 0.001, 10.0, 5

PAIRS = ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","BNBUSDT","DOGEUSDT","ADAUSDT",
         "AVAXUSDT","LINKUSDT","LTCUSDT","BCHUSDT","TRXUSDT","ZECUSDT","WLDUSDT","SUIUSDT"]


def klines(sym, interval="15m", pages=6):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, f"{sym}_{interval}.json")
    if os.path.exists(p):
        return json.load(open(p))
    out, end = [], None
    for _ in range(pages):
        u = (f"https://api.binance.com/api/v3/klines?symbol={sym}"
             f"&interval={interval}&limit=1000")
        if end: u += f"&endTime={end}"
        with urllib.request.urlopen(u, timeout=25) as r:
            b = json.load(r)
        if not b: break
        out = b + out
        end = b[0][0] - 1
        time.sleep(0.15)
    rows = [{"t":k[0],"o":float(k[1]),"h":float(k[2]),"l":float(k[3]),
             "c":float(k[4]),"v":float(k[5])} for k in out]
    json.dump(rows, open(p,"w"))
    return rows


def run(data, tp, sl, mom_bars, mom_pct, max_hold=96):
    """Вход: цена выросла на mom_pct% за последние mom_bars баров."""
    syms = list(data)
    n = min(len(data[s]) for s in syms)
    cash, pos, trades = 100.0, [], []
    for i in range(mom_bars+1, n):
        # выходы
        keep = []
        for p in pos:
            b = data[p["s"]][i]
            ex = None
            if b["l"] <= p["sl"]: ex, why = p["sl"], "stop"
            elif b["h"] >= p["tp"]: ex, why = p["tp"], "take"
            elif i - p["i"] >= max_hold: ex, why = b["c"], "time"
            if ex is None: keep.append(p)
            else:
                pr = p["q"]*ex*(1-FEE); cash += pr
                trades.append((pr-LOT, why))
        pos = keep
        # входы по импульсу
        if len(pos) < MAXPOS and cash >= LOT:
            held = {p["s"] for p in pos}
            cand = []
            for s in syms:
                if s in held: continue
                rows = data[s]
                prev = rows[i-1]["c"]; base = rows[i-1-mom_bars]["c"]
                if base > 0 and prev/base - 1 >= mom_pct/100:
                    cand.append((prev/base-1, s))
            cand.sort(reverse=True)
            for _, s in cand:
                if len(pos) >= MAXPOS or cash < LOT: break
                px = data[s][i]["o"]
                cash -= LOT
                pos.append({"s":s,"i":i,"q":LOT*(1-FEE)/px,
                            "tp":px*(1+tp/100),"sl":px*(1-sl/100)})
    eq = cash + sum(p["q"]*data[p["s"]][n-1]["c"] for p in pos)
    return eq, trades


if __name__ == "__main__":
    data = {}
    for s in PAIRS:
        try:
            data[s] = klines(s)
        except Exception as e:
            print(f"  {s}: {e}")
    n = min(len(v) for v in data.values())
    days = n*15/60/24
    print(f"  данные: {len(data)} пар, {n} 15-мин свечей ≈ {days:.0f} дней\n")
    print(f"  {'вход (импульс)':<26}{'сделок':>8}{'/день':>7}{'winrate':>9}"
          f"{'итог $100':>11}{'за 2 мес':>10}")
    print("  " + "-"*72)
    for mb, mp in ((2,0.5),(4,0.5),(4,1.0),(8,1.0),(4,1.5),(12,2.0)):
        eq, tr = run(data, 1.5, 1.0, mb, mp)
        if not tr: continue
        w = sum(1 for p,_ in tr if p>0)
        print(f"  +{mp}% за {mb*15:>3} мин{'':<12}{len(tr):>8}{len(tr)/days:>7.1f}"
              f"{w/len(tr)*100:>8.0f}%{eq:>10.2f}${(eq/100-1)*100:>+9.1f}%")
