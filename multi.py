#!/usr/bin/env python3
"""
Прогон исправленного движка по множеству монет.
Для каждой: стратегия против простого удержания на её же истории.
"""
import json, os, sys, datetime as dt
from data import fetch

FEE = 0.001
MA_LEN = 200
UTC = dt.timezone.utc


def rolling_ma(closes, n):
    """ma[i] = среднее closes[i-n:i]; до i=n не определено."""
    ma = [None] * len(closes)
    s = sum(closes[:n])
    for i in range(n, len(closes)):
        ma[i] = s / n
        s += closes[i] - closes[i - n]
    return ma


def stats(curve, days):
    eq, peak, dd = curve[-1], curve[0], 0.0
    for v in curve:
        peak = max(peak, v)
        dd = max(dd, (peak - v) / peak)
    yrs = days / 365.25
    apy = ((eq ** (1 / yrs) - 1) * 100) if eq > 0 and yrs > 0 else -100.0
    return eq, apy, dd * 100


def simulate(c, tp, hold, use_filter=True, fee=FEE, ma_len=MA_LEN):
    """Исправленный движок: повторный вход не раньше дня, следующего за выходом."""
    n = len(c)
    closes = [x["c"] for x in c]
    ma = rolling_ma(closes, ma_len)
    cash, coin, curve = 1.0, 0.0, []
    target, exit_at, blocked = None, -1, -1
    trades, wins, entry = 0, 0, None

    for i in range(ma_len, n):
        o, h, cl = c[i]["o"], c[i]["h"], c[i]["c"]
        above = (o > ma[i]) if use_filter else True
        exited = False
        if coin > 0:
            if h >= target:
                cash, coin, exited = coin * target * (1-fee), 0.0, True
                px = target
            elif i >= exit_at:
                cash, coin, exited = coin * cl * (1-fee), 0.0, True
                px = cl
            if exited:
                trades += 1
                wins += (px * (1-fee)) / (entry * (1+fee)) - 1 > 0
                blocked = i + 1
        if coin == 0 and above and cash > 0 and i >= blocked:
            coin, cash = cash * (1-fee) / o, 0.0
            entry, target, exit_at = o, o * (1+tp), i + hold
        curve.append(cash + coin * cl)
    return curve, trades, wins


def buy_hold(c, fee=FEE, ma_len=MA_LEN):
    qty = (1.0 * (1-fee)) / c[ma_len]["o"]
    return [qty * x["c"] for x in c[ma_len:]]


if __name__ == "__main__":
    tp = float(sys.argv[1]) / 100 if len(sys.argv) > 1 else 0.035
    hold = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    syms = json.load(open("universe.json"))
    out = []
    for i, s in enumerate(syms, 1):
        try:
            c = fetch(s)
        except Exception as e:
            print(f"  {s}: загрузка не удалась ({e})", flush=True); continue
        if len(c) < MA_LEN + 200:
            continue
        days = (c[-1]["t"] - c[MA_LEN]["t"]) / 1000 / 86400
        curve, tr, wn = simulate(c, tp, hold)
        st_eq, st_apy, st_dd = stats(curve, days)
        bh_eq, bh_apy, bh_dd = stats(buy_hold(c), days)
        out.append({"sym": s, "days": round(days), "trades": tr,
                    "winrate": round(wn/tr*100, 1) if tr else 0,
                    "st_apy": round(st_apy, 1), "st_dd": round(st_dd, 1),
                    "bh_apy": round(bh_apy, 1), "bh_dd": round(bh_dd, 1),
                    "st_eq": round(st_eq, 4), "bh_eq": round(bh_eq, 4)})
        if i % 25 == 0:
            print(f"  обработано {i}/{len(syms)}", flush=True)

    json.dump(out, open(f"results_tp{tp*100:g}_h{hold}.json", "w"), indent=1)
    print(f"\nготово: {len(out)} монет → results_tp{tp*100:g}_h{hold}.json")
