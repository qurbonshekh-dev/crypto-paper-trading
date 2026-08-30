#!/usr/bin/env python3
"""
Отчёт по журналу paper trading: что получилось на живых данных
и как это соотносится с ожиданием из бэктеста.

  python3 report.py [SYMBOL]
"""
import csv
import os
import sys
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
sym = (sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT").upper()
path = os.path.join(HERE, f"paper_journal_{sym}.csv")
if not os.path.exists(path):
    path = os.path.join(HERE, "paper_journal.csv")     # старое имя без пары
if not os.path.exists(path):
    sys.exit(f"журнала нет: запусти paper.py и дай ему поработать")

rows = list(csv.DictReader(open(path)))
sells = [r for r in rows if r["action"] == "SELL"]
buys = [r for r in rows if r["action"] == "BUY"]

print(f"\n  ОТЧЁТ PAPER TRADING · {sym}")
print("  " + "=" * 66)
if not rows:
    sys.exit("  журнал пуст")

t0 = dt.datetime.fromisoformat(rows[0]["ts"])
t1 = dt.datetime.fromisoformat(rows[-1]["ts"])
days = max((t1 - t0).days, 1)
print(f"  период: {t0.date()} → {t1.date()}  ({days} дн.)")
print(f"  входов: {len(buys)}   закрытых сделок: {len(sells)}")
live = sum(1 for r in rows if r["mode"] == "live")
print(f"  из них в реальном времени: {live}, доиграно по истории: {len(rows)-live}")

if not sells:
    print("\n  закрытых сделок пока нет — выводы делать рано")
    sys.exit()

pnls = [float(r["pnl_pct"]) for r in sells]
wins = [p for p in pnls if p > 0]
losses = [p for p in pnls if p <= 0]
takes = sum(1 for r in sells if r["reason"] == "take")

eq = 1.0
for p in pnls:
    eq *= 1 + p / 100

print("\n  ФАКТ")
print("  " + "-" * 66)
print(f"    winrate            {len(wins)/len(sells)*100:>6.1f}%   "
      f"({len(wins)} прибыльных / {len(losses)} убыточных)")
print(f"    по тейку вышло     {takes/len(sells)*100:>6.1f}%   ({takes} из {len(sells)})")
if wins:
    print(f"    средняя прибыль    {sum(wins)/len(wins):>+6.2f}%")
if losses:
    print(f"    средний убыток     {sum(losses)/len(losses):>+6.2f}%")
print(f"    суммарно капитал   {(eq-1)*100:>+6.2f}%   (×{eq:.4f})")
if days >= 7:
    print(f"    в пересчёте на год {((eq**(365.25/days))-1)*100:>+6.1f}%")

print("\n  ОЖИДАНИЕ ИЗ БЭКТЕСТА (исправленный движок, 2018-2026, TP3.5%/3д+MA200)")
print("  " + "-" * 66)
print(f"    winrate ~59%,  ср.прибыль +2.9%,  ср.убыток -5.0%,  годовых -13%")
print(f"    эталон 'купить и держать' за тот же период: +25.8% годовых")

print("\n  ЧТО СРАВНИВАТЬ")
print("  " + "-" * 66)
print("    1. winrate и средний убыток — сходятся ли с бэктестом?")
print("       если факт заметно хуже — виновато исполнение (проскальзывание).")
print("    2. доля выходов по тейку — бэктест считает, что лимитный ордер")
print("       исполняется ровно по цене цели. На живом рынке бывает иначе.")
print("    3. итог против простого удержания монеты за тот же период —")
print("       это единственное сравнение, которое в конце концов имеет значение.")
print()
