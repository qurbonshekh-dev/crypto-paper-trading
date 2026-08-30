#!/usr/bin/env python3
"""Треугольный арбитраж внутри Binance: перебор ВСЕХ циклов USDT->A->B->USDT."""
import json, time, urllib.request

def get(u):
    with urllib.request.urlopen(u, timeout=25) as r:
        return json.load(r)

info = get("https://api.binance.com/api/v3/exchangeInfo")
meta = {s["symbol"]: (s["baseAsset"], s["quoteAsset"])
        for s in info["symbols"] if s["status"] == "TRADING"}

def scan():
    book = {t["symbol"]: (float(t["bidPrice"]), float(t["askPrice"]))
            for t in get("https://api.binance.com/api/v3/ticker/bookTicker")
            if float(t["bidPrice"]) > 0}
    usdt = {b: s for s, (b, q) in meta.items() if q == "USDT" and s in book}
    out = []
    for sym, (base, quote) in meta.items():          # кросс-пара base/quote
        if sym not in book or quote == "USDT" or base not in usdt or quote not in usdt:
            continue
        bidX, askX = book[sym]
        bidB, askB = book[usdt[base]]
        bidQ, askQ = book[usdt[quote]]
        # маршрут 1: USDT -> quote -> base -> USDT
        r1 = (1/askQ) * (1/askX) * bidB
        # маршрут 2: USDT -> base -> quote -> USDT
        r2 = (1/askB) * bidX * bidQ
        out.append((max(r1, r2) - 1, sym, "→".join(
            ["USDT", quote, base, "USDT"] if r1 >= r2 else ["USDT", base, quote, "USDT"])))
    out.sort(reverse=True)
    return out

best = {}
for k in range(6):
    for g, sym, route in scan()[:20]:
        if sym not in best or g > best[sym][0]:
            best[sym] = (g, route)
    if k < 5: time.sleep(8)

rows = sorted(best.values(), reverse=True)[:10]
fee3 = (1 - 0.001)**3 - 1
fee3b = (1 - 0.00075)**3 - 1
print(f"ЛУЧШИЕ ТРЕУГОЛЬНИКИ ЗА ~60 СЕК (6 сканов всего рынка, {len(meta)} пар):")
print(f"  {'маршрут':<28}{'валовый':>10}{'после 3x0.1%':>14}{'c BNB-скидкой':>15}")
for g, route in rows:
    print(f"  {route:<28}{g*100:>+9.3f}%{(g+fee3)*100:>+13.3f}%{(g+fee3b)*100:>+14.3f}%")
print(f"\n  комиссия трёх сделок: {-fee3*100:.2f}% (обычная) / {-fee3b*100:.2f}% (BNB)")
