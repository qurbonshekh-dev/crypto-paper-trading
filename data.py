#!/usr/bin/env python3
"""Загрузка исторических свечей с Binance (без ключа) + кэш в CSV."""
import csv
import os
import time
import urllib.request
import json

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
API = "https://api.binance.com/api/v3/klines"


def fetch(symbol, interval="1d", start_ms=1502928000000):
    """Все свечи от start_ms до сегодня, постранично по 1000."""
    path = os.path.join(CACHE, f"{symbol}_{interval}.csv")
    if os.path.exists(path):
        with open(path) as f:
            return [
                {"t": int(r[0]), "o": float(r[1]), "h": float(r[2]),
                 "l": float(r[3]), "c": float(r[4]), "v": float(r[5])}
                for r in csv.reader(f)
            ]

    os.makedirs(CACHE, exist_ok=True)
    rows, cursor = [], start_ms
    while True:
        url = f"{API}?symbol={symbol}&interval={interval}&startTime={cursor}&limit=1000"
        with urllib.request.urlopen(url, timeout=20) as r:
            batch = json.load(r)
        if not batch:
            break
        rows += batch
        if len(batch) < 1000:
            break
        cursor = batch[-1][0] + 1
        time.sleep(0.25)  # вежливо к rate limit

    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        for k in rows:
            w.writerow(k[:6])

    return [{"t": int(k[0]), "o": float(k[1]), "h": float(k[2]),
             "l": float(k[3]), "c": float(k[4]), "v": float(k[5])} for k in rows]


if __name__ == "__main__":
    import datetime
    for s in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
        d = fetch(s)
        print(f"{s}: {len(d)} свечей, "
              f"{datetime.datetime.utcfromtimestamp(d[0]['t']/1000).date()} → "
              f"{datetime.datetime.utcfromtimestamp(d[-1]['t']/1000).date()}")
