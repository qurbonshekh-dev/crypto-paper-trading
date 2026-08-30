#!/usr/bin/env python3
"""Межбиржевой арбитраж: живые bid/ask на 5 биржах, ~90 секунд наблюдения."""
import json, time, urllib.request

def get(u):
    req = urllib.request.Request(u, headers={"User-Agent": "curl/8"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)

def quotes(sym_usdt, sym_usd, kr_pair):
    q = {}
    try:
        d = get(f"https://api.binance.com/api/v3/ticker/bookTicker?symbol={sym_usdt}")
        q["Binance"] = (float(d["bidPrice"]), float(d["askPrice"]))
    except Exception: pass
    try:
        d = get(f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={sym_usdt}")["result"]["list"][0]
        q["Bybit"] = (float(d["bid1Price"]), float(d["ask1Price"]))
    except Exception: pass
    try:
        d = get(f"https://www.okx.com/api/v5/market/ticker?instId={sym_usd.replace('-USD','-USDT')}")["data"][0]
        q["OKX"] = (float(d["bidPx"]), float(d["askPx"]))
    except Exception: pass
    try:
        d = get(f"https://api.exchange.coinbase.com/products/{sym_usd}/ticker")
        q["Coinbase*"] = (float(d["bid"]), float(d["ask"]))
    except Exception: pass
    try:
        d = get(f"https://api.kraken.com/0/public/Ticker?pair={kr_pair}")["result"]
        v = list(d.values())[0]
        q["Kraken*"] = (float(v["b"][0]), float(v["a"][0]))
    except Exception: pass
    return q

best = {}
N = 15
for k in range(N):
    for coin, s1, s2, s3 in (("BTC","BTCUSDT","BTC-USD","XBTUSD"),
                             ("ETH","ETHUSDT","ETH-USD","ETHUSD")):
        q = quotes(s1, s2, s3)
        for a in q:
            for b in q:
                if a == b: continue
                # покупаем по ask на a, продаём по bid на b
                gross = q[b][0]/q[a][1] - 1
                key = (coin, a, b)
                if key not in best or gross > best[key]:
                    best[key] = gross
    time.sleep(5)

rows = sorted(((g, c, a, b) for (c, a, b), g in best.items()), reverse=True)[:8]
print(f"ЛУЧШИЕ РАЗРЫВЫ ЗА ~90 СЕК НАБЛЮДЕНИЯ (из {N} замеров):")
print(f"  {'монета':<7}{'купить на':<12}{'продать на':<12}{'валовый разрыв':>15}")
for g, c, a, b in rows:
    print(f"  {c:<7}{a:<12}{b:<12}{g*100:>+14.3f}%")
print("\n  * Coinbase и Kraken торгуют к USD, не USDT — конвертация добавляет ~0.05-0.1%")
