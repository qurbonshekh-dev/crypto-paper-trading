#!/usr/bin/env python3
"""Отбор монет: все спотовые USDT-пары с историей не меньше N лет."""
import json, time, urllib.request, datetime as dt, os, sys

MIN_YEARS = 3.0
STABLE = {"USDC","FDUSD","TUSD","BUSD","DAI","USDP","EURI","AEUR","XUSD",
          "USD1","RLUSD","USDE","FDUSD","PYUSD","USTC","SUSD"}
SUFFIX_BAD = ("UP","DOWN","BULL","BEAR")   # плечевые токены
BASE_BAD   = {"XAUT","PAXG"}               # золото, не крипта


def get(u, tries=3):
    for k in range(tries):
        try:
            with urllib.request.urlopen(u, timeout=25) as r:
                return json.load(r)
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(1.5)


def listing_date(sym):
    d = get(f"https://api.binance.com/api/v3/klines?symbol={sym}"
            f"&interval=1d&startTime=0&limit=1")
    return dt.datetime.fromtimestamp(d[0][0]/1000, dt.timezone.utc).date() if d else None


if __name__ == "__main__":
    info = get("https://api.binance.com/api/v3/exchangeInfo")
    cand = []
    for s in info["symbols"]:
        b = s["baseAsset"]
        if (s["quoteAsset"] != "USDT" or s["status"] != "TRADING"
                or b in STABLE or b in BASE_BAD
                or any(b.endswith(x) for x in SUFFIX_BAD)
                or b.endswith("B") and len(b) > 3):     # токенизированные акции: MSTRB, SNDKB
            continue
        cand.append(s["symbol"])

    print(f"кандидатов после фильтра: {len(cand)}")
    today = dt.date.today()
    keep = []
    for i, sym in enumerate(cand, 1):
        try:
            d = listing_date(sym)
        except Exception as e:
            print(f"  {sym}: ошибка {e}"); continue
        if d and (today - d).days / 365.25 >= MIN_YEARS:
            keep.append(sym)
        if i % 50 == 0:
            print(f"  проверено {i}/{len(cand)}, подходят {len(keep)}", flush=True)
        time.sleep(0.12)

    json.dump(sorted(keep), open("universe.json", "w"), indent=1)
    print(f"\nотобрано {len(keep)} пар с историей >= {MIN_YEARS} лет → universe.json")
