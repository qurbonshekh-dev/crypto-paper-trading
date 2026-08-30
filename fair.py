#!/usr/bin/env python3
"""
Исправленный движок. Отличие от fair.py: после выхода из позиции
повторный вход возможен НЕ РАНЬШЕ открытия следующего дня.
В fair.py вход делался по open того же дня — то есть по цене,
которая была ДО момента выхода. Это завышало результат.
"""
import datetime as dt
from data import fetch

FEE = 0.001
MA = 200
btc = fetch("BTCUSDT")


def ma(i, n=MA):
    return sum(b["c"] for b in btc[i-n:i]) / n


def equity_stats(curve, days):
    eq, peak, dd = curve[-1], curve[0], 0.0
    for v in curve:
        peak = max(peak, v)
        dd = max(dd, (peak - v) / peak)
    yrs = days / 365.25
    return eq, ((eq ** (1/yrs) - 1) * 100 if eq > 0 else -100), dd * 100


def sim(lo, hi, mode, tp=0.035, hold=3, fee=None):
    f = FEE if fee is None else fee
    cash, coin, curve = 1.0, 0.0, []
    target, exit_at, blocked_until = None, -1, -1

    for i in range(lo, hi):
        o, h, c = btc[i]["o"], btc[i]["h"], btc[i]["c"]
        above = o > ma(i)

        if mode == "bh":
            if coin == 0 and cash > 0:
                coin, cash = cash * (1-f) / o, 0.0

        elif mode == "hold_ma":
            if above and coin == 0:
                coin, cash = cash * (1-f) / o, 0.0
            elif not above and coin > 0:
                cash, coin = coin * o * (1-f), 0.0

        elif mode == "trade":
            exited = False
            if coin > 0:
                if h >= target:
                    cash, coin, exited = coin * target * (1-f), 0.0, True
                elif i >= exit_at:
                    cash, coin, exited = coin * c * (1-f), 0.0, True
            if exited:
                blocked_until = i + 1        # <-- вход только со следующего дня
            if coin == 0 and above and cash > 0 and i >= blocked_until:
                coin, cash = cash * (1-f) / o, 0.0
                target, exit_at = o * (1+tp), i + hold

        curve.append(cash + coin * c)
    return curve


d = lambda i: dt.datetime.utcfromtimestamp(btc[i]["t"]/1000).date()


def compare(lo, hi, title):
    print(f"\n  {title}   {d(lo)} → {d(hi-1)}")
    print("  " + "-" * 72)
    days = (btc[hi-1]["t"] - btc[lo]["t"]) / 1000 / 86400
    for mode, label in [("trade", "схема: тейк +3.5% / 3д, вход выше MA200"),
                        ("hold_ma", "держать, пока выше MA200"),
                        ("bh", "купить и держать")]:
        eq, apy, dd = equity_stats(sim(lo, hi, mode), days)
        print(f"    {label:<44} ×{eq:>7.2f}  годовых {apy:>+6.1f}%  просадка {dd:>4.0f}%")


if __name__ == "__main__":
    compare(MA, len(btc), "ВЕСЬ ПЕРИОД (исправленный движок)")
    mid = len(btc) // 2
    compare(MA, mid, "1-я ПОЛОВИНА")
    compare(mid, len(btc), "2-я ПОЛОВИНА")
