#!/usr/bin/env python3
"""
Утренняя проверка сигналов для месячного теста.
Показывает, на каких монетах СЕГОДНЯ выполняются условия входа,
которые исторически чаще предшествовали росту (см. entries.py).

  python3 signals.py
"""
import json, os, datetime as dt, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
EXCLUDE = {"EURUSDT", "WBTCUSDT"}          # фиат и прокси BTC — не для теста
UTC = dt.timezone.utc


def klines(symbol, limit=260):
    url = (f"https://api.binance.com/api/v3/klines?symbol={symbol}"
           f"&interval=1d&limit={limit}")
    with urllib.request.urlopen(url, timeout=20) as r:
        raw = json.load(r)
    return [{"t": k[0], "o": float(k[1]), "h": float(k[2]), "l": float(k[3]),
             "c": float(k[4]), "v": float(k[5])} for k in raw]


def wilder_rsi(c, n=14):
    if len(c) < n + 1:
        return None
    au = sum(max(c[i]-c[i-1], 0) for i in range(1, n+1)) / n
    ad = sum(max(c[i-1]-c[i], 0) for i in range(1, n+1)) / n
    for i in range(n+1, len(c)):
        u, d = max(c[i]-c[i-1], 0), max(c[i-1]-c[i], 0)
        au = (au*(n-1)+u)/n
        ad = (ad*(n-1)+d)/n
    return 100.0 if ad == 0 else 100 - 100/(1 + au/ad)


def indicators(sym):
    k = klines(sym)
    today = dt.datetime.now(UTC).date()
    done = [x for x in k if dt.datetime.fromtimestamp(x["t"]/1000, UTC).date() < today]
    if len(done) < 221:
        return None
    closes = [x["c"] for x in done]
    y = done[-1]                                    # вчера, завершённый день
    price = k[-1]["c"]                              # текущая цена
    ma200 = sum(closes[-200:]) / 200
    vol20 = sum(x["v"] for x in done[-21:-1]) / 20
    return {
        "sym": sym, "price": price, "ma200": ma200,
        "above": price > ma200,
        "rsi": wilder_rsi(closes),
        "volx": y["v"] / vol20 if vol20 else 0,
        "red3": all(x["c"] < x["o"] for x in done[-3:]),
        "lo20": y["c"] < min(x["l"] for x in done[-21:-1]),
    }


if __name__ == "__main__":
    pairs = [s for s in json.load(open(os.path.join(HERE, "trading_pairs.json")))
             if s not in EXCLUDE]
    now = dt.datetime.now(UTC)
    print(f"\n  СИГНАЛЫ · {now:%Y-%m-%d %H:%M} UTC")
    print("  историческая база: entries.py (2018-2026, 215 монет)")
    print("  " + "=" * 66)

    b = indicators("BTCUSDT")
    sig_a = b["above"] and b["volx"] >= 1.95
    print(f"\n  СИГНАЛ A — BTC: объём вчера >= 1.95x среднего И цена выше MA200")
    print(f"    цена {b['price']:,.0f}  MA200 {b['ma200']:,.0f} "
          f"({'выше' if b['above'] else 'НИЖЕ'})  объём {b['volx']:.2f}x")
    print(f"    >>> {'ЕСТЬ СИГНАЛ' if sig_a else 'сигнала нет'}"
          f"   (исторически: 64% случаев +3.5% за 3 дня, против 41% фона)")

    print(f"\n  СИГНАЛ B — альты: RSI14 < 30 (перепроданность)")
    print(f"    (исторически по 215 монетам: 72% случаев +3.5% за 3 дня)")
    print(f"    {'пара':<12}{'цена':>13}{'RSI':>7}{'MA200':>8}{'объём':>8}"
          f"{'3 красн.':>10}{'мин.20д':>9}")
    found = 0
    for s in pairs:
        if s == "BTCUSDT":
            continue
        try:
            d = indicators(s)
        except Exception:
            continue
        if d is None or d["rsi"] is None:
            continue
        mark = d["rsi"] < 30
        info = d["rsi"] < 40 or d["lo20"]   # близко к перепроданности
        if not info:
            continue
        found += mark
        print(f"    {s:<12}{d['price']:>13,.4g}{d['rsi']:>7.0f}"
              f"{'выше' if d['above'] else 'ниже':>8}{d['volx']:>7.1f}x"
              f"{'да' if d['red3'] else '—':>10}{'да' if d['lo20'] else '—':>9}"
              + ("   <<< СИГНАЛ" if mark else ""))
    if not found:
        print(f"    сегодня сигналов RSI<30 нет (показаны близкие: RSI<40)")
    print(f"\n  НЕ покупать: монеты после резкого роста (RSI>70, пробой максимума,"
          f"\n  всплеск объёма на альтах) — исторически это МИНУС на 3 днях.")
    print()
