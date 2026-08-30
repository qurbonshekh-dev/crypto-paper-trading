#!/usr/bin/env python3
"""Зависит ли успех стратегии от волатильности монеты?"""
import json, sys, statistics as st
from data import fetch

r = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "results_tp3.5_h3.json"))
r = [x for x in r if x["trades"] >= 10]

for x in r:
    c = fetch(x["sym"])[200:]
    moves = [abs(b["c"] - b["o"]) / b["o"] * 100 for b in c if b["o"]]
    x["vol"] = st.median(moves)
    # как часто цена вообще доходит до +3.5% за 3 дня
    hits = sum(1 for i in range(len(c)-3)
               if max(b["h"] for b in c[i+1:i+4]) >= c[i]["o"] * 1.035)
    x["reach"] = hits / max(len(c)-3, 1) * 100

r.sort(key=lambda x: x["vol"])
k = max(len(r)//4, 1)
groups = [("самые спокойные 25%", r[:k]),
          ("средние 50%",          r[k:-k]),
          ("самые волатильные 25%", r[-k:])]

print("\n  ЗАВИСИМОСТЬ ОТ ВОЛАТИЛЬНОСТИ (TP3.5% / 3д + MA200)")
print("  " + "=" * 72)
print(f"    {'группа':<24}{'дн.ход':>9}{'дошло до цели':>15}"
      f"{'стратегия':>12}{'удержание':>12}{'обогнали':>11}")
for name, g in groups:
    if not g:
        continue
    beat = sum(1 for x in g if x["st_apy"] > x["bh_apy"])
    print(f"    {name:<24}{st.median([x['vol'] for x in g]):>8.2f}%"
          f"{st.median([x['reach'] for x in g]):>14.0f}%"
          f"{st.median([x['st_apy'] for x in g]):>11.1f}%"
          f"{st.median([x['bh_apy'] for x in g]):>11.1f}%"
          f"{beat:>7}/{len(g)}")
print("\n  'дошло до цели' — доля дней, когда цена достигала +3.5% в ближайшие 3 дня")
print()
