#!/usr/bin/env python3
"""Сводка по мультимонетному прогону."""
import json, sys, statistics as st

f = sys.argv[1] if len(sys.argv) > 1 else "results_tp3.5_h3.json"
r = json.load(open(f))
r = [x for x in r if x["trades"] >= 10]        # отбрасываем монеты почти без сделок

n = len(r)
beat = [x for x in r if x["st_apy"] > x["bh_apy"]]
prof = [x for x in r if x["st_apy"] > 0]

sa = sorted(x["st_apy"] for x in r)
ba = sorted(x["bh_apy"] for x in r)
q = lambda v, p: v[int(len(v)*p)]

print(f"\n  МУЛЬТИМОНЕТНЫЙ ПРОГОН — {f}")
print("  " + "=" * 68)
print(f"  монет в выборке: {n}   (история >= 3 лет, >= 10 сделок)\n")

print("  ГЛАВНЫЙ ВОПРОС: обгоняет ли стратегия простое удержание?")
print("  " + "-" * 68)
print(f"    обгоняет на {len(beat)} монетах из {n}  ({len(beat)/n*100:.0f}%)")
print(f"    просто прибыльна на {len(prof)} из {n}  ({len(prof)/n*100:.0f}%)")

print("\n  ГОДОВАЯ ДОХОДНОСТЬ, распределение по монетам")
print("  " + "-" * 68)
print(f"    {'':14}{'25-й проц.':>13}{'медиана':>13}{'75-й проц.':>13}")
print(f"    {'стратегия':<14}{q(sa,.25):>12.1f}%{q(sa,.5):>12.1f}%{q(sa,.75):>12.1f}%")
print(f"    {'удержание':<14}{q(ba,.25):>12.1f}%{q(ba,.5):>12.1f}%{q(ba,.75):>12.1f}%")

med_d = st.median([x["st_apy"] - x["bh_apy"] for x in r])
print(f"\n    медианное отставание стратегии: {med_d:+.1f} п.п. в год")

print("\n  ПОРТФЕЛЬ РАВНЫМИ ДОЛЯМИ ПО ВСЕМ МОНЕТАМ")
print("  " + "-" * 68)
print(f"    стратегия: ×{st.mean([x['st_eq'] for x in r]):.2f}   "
      f"удержание: ×{st.mean([x['bh_eq'] for x in r]):.2f}")

print("\n  ГДЕ СТРАТЕГИЯ ОБОГНАЛА СИЛЬНЕЕ ВСЕГО (топ-10)")
print("  " + "-" * 68)
print(f"    {'монета':<13}{'стратег.':>10}{'удерж.':>10}{'разница':>10}{'сделок':>8}{'winrate':>9}")
for x in sorted(r, key=lambda y: -(y["st_apy"]-y["bh_apy"]))[:10]:
    print(f"    {x['sym']:<13}{x['st_apy']:>9.1f}%{x['bh_apy']:>9.1f}%"
          f"{x['st_apy']-x['bh_apy']:>+9.1f}{x['trades']:>8}{x['winrate']:>8.0f}%")

print("\n  ГДЕ ОТСТАЛА СИЛЬНЕЕ ВСЕГО (топ-10)")
print("  " + "-" * 68)
for x in sorted(r, key=lambda y: (y["st_apy"]-y["bh_apy"]))[:10]:
    print(f"    {x['sym']:<13}{x['st_apy']:>9.1f}%{x['bh_apy']:>9.1f}%"
          f"{x['st_apy']-x['bh_apy']:>+9.1f}{x['trades']:>8}{x['winrate']:>8.0f}%")

print("\n  WINRATE ПРОТИВ РЕЗУЛЬТАТА")
print("  " + "-" * 68)
w = sorted(r, key=lambda y: -y["winrate"])[:15]
print(f"    у 15 монет с самым высоким winrate ({w[-1]['winrate']:.0f}-{w[0]['winrate']:.0f}%):")
print(f"      медиана доходности стратегии {st.median([x['st_apy'] for x in w]):+.1f}%,"
      f"  удержания {st.median([x['bh_apy'] for x in w]):+.1f}%")
print(f"      обогнали удержание: {sum(1 for x in w if x['st_apy']>x['bh_apy'])} из 15")
print()
