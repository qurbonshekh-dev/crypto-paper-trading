#!/usr/bin/env python3
"""Какие источники дневных свечей доступны с этой машины."""
import json, urllib.request, urllib.error

def get(u):
    r = urllib.request.Request(u, headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
    with urllib.request.urlopen(r, timeout=20) as resp:
        return resp.getcode(), json.load(resp)

TESTS = [
  ("Binance",  "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=3"),
  ("OKX",      "https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=1D&limit=3"),
  ("Bybit",    "https://api.bybit.com/v5/market/kline?category=spot&symbol=BTCUSDT&interval=D&limit=3"),
  ("Coinbase", "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=86400"),
  ("Kraken",   "https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=1440"),
  ("CoinGecko","https://api.coingecko.com/api/v3/coins/bitcoin/ohlc?vs_currency=usd&days=7"),
]
for name, url in TESTS:
    try:
        code, d = get(url)
        n = len(d) if isinstance(d, list) else len(d.get("data", d.get("result", [])) or [])
        print(f"  {name:<10} OK    записей: {n}")
    except urllib.error.HTTPError as e:
        print(f"  {name:<10} HTTP {e.code}" + ("  ← гео-блокировка" if e.code == 451 else ""))
    except Exception as e:
        print(f"  {name:<10} ОШИБКА {type(e).__name__}: {str(e)[:60]}")
