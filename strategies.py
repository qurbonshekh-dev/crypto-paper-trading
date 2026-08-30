#!/usr/bin/env python3
"""
Проверка семейств стратегий на одном движке и одних данных.
Все — только на дневных свечах, комиссия 0.1%/сторона, всё в одной валюте (USDT).
"""
import json, math, statistics as st, datetime as dt
from data import fetch

FEE = 0.001
MA = 200


def stats(curve, days):
    eq, peak, dd = curve[-1], curve[0], 0.0
    for v in curve:
        peak = max(peak, v); dd = max(dd, (peak-v)/peak)
    yrs = days/365.25
    return eq, ((eq**(1/yrs)-1)*100 if eq > 0 and yrs > 0 else -100), dd*100


def roll_mean(a, n):
    out = [None]*len(a); s = sum(a[:n])
    for i in range(n, len(a)):
        out[i] = s/n; s += a[i]-a[i-n]
    return out


# ---------- 1. Трейлинг-стоп: убыток ограничен, прибыль нет ----------
def trailing(c, trail, ma_len=MA, fee=FEE):
    closes = [x["c"] for x in c]; ma = roll_mean(closes, ma_len)
    cash, coin, curve = 1.0, 0.0, []
    peak_px, blocked = None, -1
    trades, wins, entry = 0, 0, None
    for i in range(ma_len, len(c)):
        o, h, l, cl = c[i]["o"], c[i]["h"], c[i]["l"], c[i]["c"]
        if coin > 0:
            peak_px = max(peak_px, h)
            stop = peak_px*(1-trail)
            if l <= stop:
                cash, coin = coin*stop*(1-fee), 0.0
                trades += 1; wins += (stop*(1-fee))/(entry*(1+fee)) - 1 > 0
                blocked = i+1
        if coin == 0 and cash > 0 and i >= blocked and ma[i] and o > ma[i]:
            coin, cash = cash*(1-fee)/o, 0.0
            entry, peak_px = o, o
        curve.append(cash + coin*cl)
    return curve, trades, wins


# ---------- 2. Импульс: покупать сильнейшие за N дней ----------
def momentum(data, lookback, hold, top_n=3, fee=FEE):
    syms = list(data)
    days = sorted({b["d"] for b in data["BTCUSDT"]})
    idx = {s: {b["d"]: i for i, b in enumerate(rows)} for s, rows in data.items()}
    eq, curve, holdings, k = 1.0, [], {}, 0
    for d in days[lookback+1:]:
        if k % hold == 0:                       # ребалансировка
            rank = []
            for s in syms:
                i = idx[s].get(d)
                if i is None or i < lookback+1: continue
                r = data[s][i-1]["c"]/data[s][i-1-lookback]["c"] - 1
                rank.append((r, s))
            rank.sort(reverse=True)
            newh = {s for _, s in rank[:top_n] if _ > 0}
            turnover = len(newh ^ set(holdings)) / max(len(newh) or 1, 1)
            eq *= (1 - fee*min(turnover, 2))
            holdings = {s: data[s][idx[s][d]]["o"] for s in newh}
        else:
            newh = holdings
        if holdings:
            rets = []
            for s, p0 in holdings.items():
                i = idx[s].get(d)
                if i is None: continue
                rets.append(data[s][i]["c"]/data[s][i-1]["c"] - 1 if k % hold else data[s][i]["c"]/p0 - 1)
            if rets: eq *= (1 + sum(rets)/len(rets))
        curve.append(eq); k += 1
    return curve


# ---------- 3. Возврат к среднему на паре (грубый прокси парного арбитража) ----------
def pair_revert(a, b, z_in=2.0, z_out=0.5, win=60, fee=FEE):
    """Лонг отстающей / без шорта: вход когда спред ушёл на z_in сигм."""
    n = min(len(a), len(b))
    ra = [math.log(a[i]["c"]/a[i-1]["c"]) for i in range(1, n)]
    rb = [math.log(b[i]["c"]/b[i-1]["c"]) for i in range(1, n)]
    spread = [ra[i]-rb[i] for i in range(len(ra))]
    cum = [0.0]
    for x in spread: cum.append(cum[-1]+x)
    eq, pos, curve, entry = 1.0, 0, [], None
    for i in range(win+1, len(cum)-1):
        w = cum[i-win:i]
        m, sd = sum(w)/win, (st.pstdev(w) or 1e-9)
        z = (cum[i]-m)/sd
        px = a[i+1]["c"]/a[i+1-1]["c"] - 1
        if pos == 0 and z <= -z_in:
            pos, entry = 1, i
            eq *= (1-fee)
        elif pos == 1:
            eq *= (1 + px)
            if z >= -z_out:
                pos = 0; eq *= (1-fee)
        curve.append(eq)
    return curve


if __name__ == "__main__":
    btc = fetch("BTCUSDT")
    days = (btc[-1]["t"] - btc[MA]["t"])/1000/86400
    bh = ((1-FEE)/btc[MA]["o"]) * btc[-1]["c"]
    bh_apy = ((bh**(365.25/days))-1)*100

    print(f"\n  BTC 2018-2026, эталон «купить и держать»: ×{bh:.1f}  ({bh_apy:+.1f}% годовых)")
    print("  " + "="*70)
    print("\n  1. ТРЕЙЛИНГ-СТОП (убыток ограничен, прибыль не ограничена)")
    print(f"    {'откат от пика':<18}{'итог':>9}{'годовых':>10}{'просадка':>10}{'сделок':>8}{'win':>6}")
    for t in (0.08, 0.12, 0.15, 0.20, 0.25, 0.30):
        cv, tr, wn = trailing(btc, t)
        eq, apy, dd = stats(cv, days)
        print(f"    откат {t*100:>2.0f}%{'':<9}×{eq:>7.2f}{apy:>9.1f}%{dd:>9.0f}%{tr:>8}"
              f"{(wn/tr*100 if tr else 0):>5.0f}%")
