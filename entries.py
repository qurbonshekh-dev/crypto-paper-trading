#!/usr/bin/env python3
"""
Измерение условий входа: для каждого наблюдаемого условия — что делала цена
в следующие 3 дня. Никаких цепочек сделок, чистая условная статистика.

  p_hit — вероятность коснуться +3.5% в ближайшие 3 дня
  p_dd  — вероятность коснуться -3.5% в ближайшие 3 дня
  fwd   — медианный результат через 3 дня (close/entry - 1)
"""
import json, statistics as st, datetime as dt
from data import fetch

TARGET, DDLIM, FWD_DAYS = 0.035, 0.035, 3
START = 221


def excl_mean(a, n):
    """out[i] = среднее a[i-n:i] (текущий индекс не входит)."""
    out = [None]*len(a); s = sum(a[:n])
    for i in range(n, len(a)):
        out[i] = s/n; s += a[i] - a[i-n]
    return out


def excl_max(a, n):
    out = [None]*len(a)
    for i in range(n, len(a)):
        out[i] = max(a[i-n:i])
    return out


def excl_min(a, n):
    out = [None]*len(a)
    for i in range(n, len(a)):
        out[i] = min(a[i-n:i])
    return out


def wilder_rsi(c, n=14):
    out = [None]*len(c)
    if len(c) < n+1: return out
    ups = [max(c[i]-c[i-1], 0) for i in range(1, n+1)]
    dns = [max(c[i-1]-c[i], 0) for i in range(1, n+1)]
    au, ad = sum(ups)/n, sum(dns)/n
    for i in range(n+1, len(c)):
        ch = c[i-1] - c[i-2] if i > n+1 else 0
        # пересчёт по Уайлдеру на каждом шаге
        u, d = max(c[i]-c[i-1], 0), max(c[i-1]-c[i], 0)
        au = (au*(n-1) + u)/n; ad = (ad*(n-1) + d)/n
        out[i] = 100.0 if ad == 0 else 100 - 100/(1 + au/ad)
    return out


def btc_bull_by_ts():
    b = fetch("BTCUSDT")
    closes = [x["c"] for x in b]
    m = excl_mean(closes, 200)
    return {b[i]["t"]: closes[i] > m[i] for i in range(200, len(b))}


BB = btc_bull_by_ts()

CONDS = ["any", "above_ma200", "below_ma200", "above_ma50",
         "green_yday", "red_yday", "3red", "3green", "drop5",
         "hi20", "lo20", "volspike", "rsi_lt30", "rsi_gt70",
         "btc_bull", "ma200_and_hi20", "ma200_and_red", "ma200_and_volspike"]


def analyze(c):
    o = [x["o"] for x in c]; h = [x["h"] for x in c]
    l = [x["l"] for x in c]; cl = [x["c"] for x in c]; v = [x["v"] for x in c]
    ma200 = excl_mean(cl, 200); ma50 = excl_mean(cl, 50)
    mh20 = excl_max(h, 20); ml20 = excl_min(l, 20)
    vm20 = excl_mean(v, 20); rsi = wilder_rsi(cl)

    res = {k: {"n":0,"hit":0,"dd":0,"fwd":[]} for k in CONDS}
    halves = {k: [ {"n":0,"hit":0}, {"n":0,"hit":0} ] for k in CONDS}
    mid = (START + len(c)-FWD_DAYS)//2

    for i in range(START, len(c)-FWD_DAYS):
        j = i-1                       # сигналы — по данным вчерашнего дня
        entry = o[i]
        if not entry: continue
        H = max(h[i:i+FWD_DAYS]); L = min(l[i:i+FWD_DAYS])
        hit = H >= entry*(1+TARGET); dd = L <= entry*(1-DDLIM)
        fwd = cl[i+FWD_DAYS-1]/entry - 1

        red = lambda k: cl[k] < o[k]
        f = {
          "any": True,
          "above_ma200": ma200[i] and o[i] > ma200[i],
          "below_ma200": ma200[i] and o[i] < ma200[i],
          "above_ma50":  ma50[i] and o[i] > ma50[i],
          "green_yday": not red(j), "red_yday": red(j),
          "3red":  red(j) and red(j-1) and red(j-2),
          "3green": not red(j) and not red(j-1) and not red(j-2),
          "drop5": cl[j] < cl[j-1]*0.95,
          "hi20": mh20[j] and cl[j] > mh20[j],
          "lo20": ml20[j] and cl[j] < ml20[j],
          "volspike": vm20[j] and v[j] > 2*vm20[j],
          "rsi_lt30": rsi[j] is not None and rsi[j] < 30,
          "rsi_gt70": rsi[j] is not None and rsi[j] > 70,
          "btc_bull": BB.get(c[j]["t"], False),
        }
        f["ma200_and_hi20"] = f["above_ma200"] and f["hi20"]
        f["ma200_and_red"] = f["above_ma200"] and f["red_yday"]
        f["ma200_and_volspike"] = f["above_ma200"] and f["volspike"]

        for k, ok in f.items():
            if not ok: continue
            r = res[k]; r["n"] += 1; r["hit"] += hit; r["dd"] += dd; r["fwd"].append(fwd)
            hh = halves[k][0 if i < mid else 1]; hh["n"] += 1; hh["hit"] += hit
    return res, halves


def pct(a, b): return a/b*100 if b else 0


if __name__ == "__main__":
    # --- BTC подробно ---
    btc = fetch("BTCUSDT")
    R, H = analyze(btc)
    base = pct(R["any"]["hit"], R["any"]["n"])
    print(f"\n  BTC, 2018-2026 ({R['any']['n']} дней) — что было в следующие 3 дня")
    print("  " + "="*74)
    print(f"    {'условие':<22}{'N':>6}{'P(+3.5%)':>10}{'P(-3.5%)':>10}{'мед.3д':>9}"
          f"{'1-я пол.':>10}{'2-я пол.':>9}")
    for k in CONDS:
        r = R[k]
        if r["n"] < 30: continue
        h1, h2 = H[k]
        print(f"    {k:<22}{r['n']:>6}{pct(r['hit'],r['n']):>9.0f}%"
              f"{pct(r['dd'],r['n']):>9.0f}%{st.median(r['fwd'])*100:>+8.2f}%"
              f"{pct(h1['hit'],h1['n']):>9.0f}%{pct(h2['hit'],h2['n']):>8.0f}%")

    # --- по всем монетам: медианы по монетам ---
    syms = json.load(open("universe.json"))
    agg = {k: {"p":[], "d":[], "f":[]} for k in CONDS}
    used = 0
    for s in syms:
        try: c = fetch(s)
        except Exception: continue
        if len(c) < 600: continue
        r, _ = analyze(c); used += 1
        for k in CONDS:
            if r[k]["n"] >= 30:
                agg[k]["p"].append(pct(r[k]["hit"], r[k]["n"]))
                agg[k]["d"].append(pct(r[k]["dd"], r[k]["n"]))
                agg[k]["f"].append(st.median(r[k]["fwd"])*100)

    print(f"\n  ВСЕ МОНЕТЫ ({used} шт.) — медианы по монетам")
    print("  " + "="*74)
    print(f"    {'условие':<22}{'монет':>6}{'P(+3.5%)':>10}{'P(-3.5%)':>10}{'мед.3д':>9}")
    for k in CONDS:
        a = agg[k]
        if len(a["p"]) < 20: continue
        print(f"    {k:<22}{len(a['p']):>6}{st.median(a['p']):>9.0f}%"
              f"{st.median(a['d']):>9.0f}%{st.median(a['f']):>+8.2f}%")
