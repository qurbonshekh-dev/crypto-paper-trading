#!/usr/bin/env python3
"""Пересчёт исторических ожиданий трёх счетов на вселенной 215 монет."""
import json, datetime as dt
import risky_test as rt
from data import fetch

def load_universe(start):
    syms = [s for s in json.load(open("universe.json")) if s not in ("EURUSDT","WBTCUSDT")]
    data = {}
    for s in syms:
        try: c = fetch(s)
        except Exception: continue
        rows = [{"d": dt.datetime.utcfromtimestamp(k["t"]/1000).date().isoformat(),
                 **{q: k[q] for q in ("o","h","l","c","v")}} for k in c]
        if rows: data[s] = rows
    return data

START = "2022-01-01"
data = load_universe(START)
print(f"монет: {len(data)}")

r = rt.portfolio(data, START, rt.sig_dip(5), sl=0.12)
print(f"дип -5%, +4%/-12%:   итог {r['eq']:.0f}$  годовых {r['apy']:+.1f}%  просадка {r['dd']:.0f}%  сделок {r['n']}  win {r['win']:.0f}%")

rt.TP = 0.035
r = rt.portfolio(data, START, rt.sig_dip(4), sl=0.04)
print(f"узкий -4%, +3.5/-4%: итог {r['eq']:.0f}$  годовых {r['apy']:+.1f}%  просадка {r['dd']:.0f}%  сделок {r['n']}  win {r['win']:.0f}%")
rt.TP = 0.04

r = rt.portfolio(data, START, rt.sig_rsi, sl=0.12)
print(f"RSI<30, +4%/-12%:    итог {r['eq']:.0f}$  годовых {r['apy']:+.1f}%  просадка {r['dd']:.0f}%  сделок {r['n']}  win {r['win']:.0f}%")
print(f"бенчмарк BTC: {r['bench']:.0f}$ ({r['bench_apy']:+.1f}%)")
