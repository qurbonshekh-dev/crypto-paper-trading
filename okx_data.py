#!/usr/bin/env python3
"""
Свечи с OKX — источник, доступный из облачных дата-центров США
(Binance отвечает им HTTP 451).

Формат на выходе идентичен прежнему binance-загрузчику, поэтому
движки стратегий не меняются.
"""
import json, time, urllib.request, datetime as dt

UTC = dt.timezone.utc
BASE = "https://www.okx.com/api/v5/market/history-candles"
BASE_RECENT = "https://www.okx.com/api/v5/market/candles"


def inst(sym):
    """BTCUSDT -> BTC-USDT"""
    return sym[:-4] + "-USDT" if sym.endswith("USDT") else sym


def _fetch(url, tries=4):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=25) as r:
                d = json.load(r)
            if d.get("code") not in ("0", 0):
                raise RuntimeError(f"OKX code={d.get('code')} msg={d.get('msg')}")
            return d["data"]
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(1.5 * (k + 1))


def candles(sym, bar, limit_bars):
    """
    bar: '1Dutc' — дневные, закрытие в 00:00 UTC (как у Binance)
         '15m'   — 15-минутные
    Возвращает список по возрастанию времени: t,o,h,l,c,v
    """
    out, after = {}, None
    need = limit_bars
    while need > 0:
        base = BASE_RECENT if after is None else BASE
        u = f"{base}?instId={inst(sym)}&bar={bar}&limit=300"
        if after: u += f"&after={after}"
        d = _fetch(u)
        if not d: break
        for k in d:
            out[int(k[0])] = k
        after = d[-1][0]
        need -= len(d)
        if len(d) < 300: break
        time.sleep(0.12)
    rows = [out[t] for t in sorted(out)]
    return [{"t": int(k[0]), "o": float(k[1]), "h": float(k[2]),
             "l": float(k[3]), "c": float(k[4]), "v": float(k[5])} for k in rows]


def daily(sym, limit=330):
    rows = candles(sym, "1Dutc", limit)
    for r in rows:
        r["d"] = dt.datetime.fromtimestamp(r["t"]/1000, UTC).date().isoformat()
    return rows


def m15(sym, since_ms):
    """15-минутные свечи начиная примерно с since_ms."""
    span = dt.datetime.now(UTC).timestamp()*1000 - since_ms
    need = int(span / (15*60*1000)) + 20
    return candles(sym, "15m", max(need, 100))


if __name__ == "__main__":
    r = daily("BTCUSDT", 5)
    print("дневные BTC:", [(x["d"], x["c"]) for x in r[-3:]])
    r2 = m15("BTCUSDT", dt.datetime.now(UTC).timestamp()*1000 - 6*3600*1000)
    print(f"15-мин BTC: {len(r2)} баров, последний {r2[-1]['c']}")
