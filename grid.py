#!/usr/bin/env python3
"""
Несколько наборов параметров по всем монетам сразу (из кэша, без сети).
Отвечает на вопрос: есть ли ХОТЬ КАКАЯ-ТО настройка, прибыльная на большинстве монет.
"""
import json, statistics as st
import multi
from data import fetch

SETS = [(3.5, 3), (3.5, 7), (5, 3), (5, 5), (8, 5), (8, 7), (12, 10)]

syms = json.load(open("universe.json"))
coins = []
for s in syms:
    try:
        c = fetch(s)
    except Exception:
        continue
    if len(c) >= 400:
        coins.append((s, c))
print(f"  монет с достаточной историей: {len(coins)}\n")

print("  ЕСТЬ ЛИ ПРИБЫЛЬНАЯ НАСТРОЙКА? (все монеты, комиссия 0.1%)")
print("  " + "=" * 74)
print(f"    {'параметры':<16}{'прибыльна на':>16}{'обогнала удерж.':>18}"
      f"{'медиана год.':>15}")

bh = []
for s, c in coins:
    days = (c[-1]["t"] - c[200]["t"]) / 1000 / 86400
    _, a, _ = multi.stats(multi.buy_hold(c), days)
    bh.append(a)

for tp, hold in SETS:
    prof = beat = n = 0
    apys = []
    for (s, c), b in zip(coins, bh):
        days = (c[-1]["t"] - c[200]["t"]) / 1000 / 86400
        curve, tr, _ = multi.simulate(c, tp/100, hold)
        if tr < 10:
            continue
        _, a, _ = multi.stats(curve, days)
        apys.append(a); n += 1
        prof += a > 0
        beat += a > b
    print(f"    TP{tp:g}% / {hold:>2}д      {prof:>7}/{n} ({prof/n*100:>3.0f}%)"
          f"   {beat:>7}/{n} ({beat/n*100:>3.0f}%)   {st.median(apys):>+12.1f}%")

print(f"\n    {'удержание':<16}{sum(1 for a in bh if a>0):>7}/{len(bh)} "
      f"({sum(1 for a in bh if a>0)/len(bh)*100:>3.0f}%)"
      f"{'—':>20}   {st.median(bh):>+12.1f}%")
print()
