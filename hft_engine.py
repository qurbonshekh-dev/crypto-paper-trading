#!/usr/bin/env python3
"""
Счёт «Частая торговля»: вход по импульсу, тейк +1.5%, стоп -1%, до 20 сделок в день.
Работает на 5-минутных свечах OKX (15м→5м в день старта, 30.08), журнал считается здесь, а не в браузере:
сырых свечей слишком много, чтобы вкладывать их в страницу.

Правила зафиксированы 30.08.2026:
  вселенная  — 15 ликвидных пар
  вход       — цена выросла >= 1% за последний час (12 баров), берём сильнейшие
  выход      — тейк +1.5% | стоп -1% | по времени через 24 часа
  деньги     — $100, лот $10, максимум 10 позиций одновременно (5→10 в день старта)
  комиссия   — 0.075% на сторону (тариф пользователя с оплатой в BNB)
"""
import json, os, sys, datetime as dt
import okx_data

HERE = os.path.dirname(os.path.abspath(__file__))
PAIRS = ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","BNBUSDT","DOGEUSDT","ADAUSDT",
         "AVAXUSDT","LINKUSDT","LTCUSDT","BCHUSDT","TRXUSDT","ZECUSDT","WLDUSDT","SUIUSDT"]
START      = "2026-08-30"      # первый день теста
TEST_DAYS  = 30
FEE        = 0.00075
LOT, MAXPOS = 10.0, 10   # слотов 5→10 по решению пользователя 30.08, в первый день теста
TP, SL     = 0.015, 0.01
MOM_BARS, MOM_PCT = 12, 1.0    # импульс: +1% за 12 баров (час)
MAX_HOLD   = 288               # 24 часа в 5-минутках
UTC = dt.timezone.utc


def fetch_all():
    # берём с запасом назад, чтобы импульс считался уже на первом баре теста
    t0 = int(dt.datetime.fromisoformat(START).replace(tzinfo=UTC).timestamp() * 1000)
    t0 -= MOM_BARS * 5 * 60 * 1000
    return {s: okx_data.m5(s, t0) for s in PAIRS}


def simulate(data, start=START, sl=SL, tp=TP, test_days=TEST_DAYS):
    syms = [s for s in data if data[s]]
    if not syms: return None
    n = min(len(data[s]) for s in syms)
    start_ms = int(dt.datetime.fromisoformat(start).replace(tzinfo=UTC).timestamp() * 1000)

    cash, pos, trades, curve = 100.0, [], [], []
    end_ms = start_ms + test_days * 86400 * 1000

    for i in range(MOM_BARS + 1, n):
        ts = data[syms[0]][i]["t"]
        if ts < start_ms:
            continue

        # выходы: стоп проверяем раньше тейка (консервативно)
        keep = []
        for p in pos:
            b = data[p["s"]][i]
            ex = why = None
            if b["l"] <= p["sl"]:      ex, why = p["sl"], "stop"
            elif b["h"] >= p["tp"]:    ex, why = p["tp"], "take"
            elif i - p["i"] >= MAX_HOLD: ex, why = b["c"], "time"
            if ex is None:
                keep.append(p)
            else:
                pr = p["q"] * ex * (1 - FEE)
                cash += pr
                trades.append({"sym": p["s"], "in_t": p["t"], "in_px": p["px"],
                               "out_t": b["t"], "out_px": ex, "reason": why,
                               "pnl_usd": round(pr - LOT, 4),
                               "pnl_pct": round((pr / LOT - 1) * 100, 3)})
        pos = keep

        # входы по импульсу, только пока идёт период теста
        if ts <= end_ms and len(pos) < MAXPOS and cash >= LOT:
            held = {p["s"] for p in pos}
            cand = []
            for s in syms:
                if s in held: continue
                r = data[s]
                base = r[i - 1 - MOM_BARS]["c"]
                if base > 0 and r[i-1]["c"] / base - 1 >= MOM_PCT / 100:
                    cand.append((r[i-1]["c"] / base - 1, s))
            cand.sort(reverse=True)
            for _, s in cand:
                if len(pos) >= MAXPOS or cash < LOT: break
                px = data[s][i]["o"]
                cash -= LOT
                pos.append({"s": s, "i": i, "t": data[s][i]["t"], "px": px,
                            "q": LOT * (1 - FEE) / px,
                            "tp": px * (1 + tp), "sl": px * (1 - sl)})

        mark = cash + sum(p["q"] * data[p["s"]][i]["c"] for p in pos)
        curve.append({"t": ts, "eq": round(mark, 4)})

    if len(curve) > 2000:                      # к концу месяца кривая была бы ~9000 точек
        step = len(curve) // 2000 + 1
        curve = curve[::step]

    last = {s: data[s][n-1]["c"] for s in syms}
    return {"cash": round(cash, 4), "trades": trades, "curve": curve,
            "positions": [{"sym": p["s"], "t": p["t"], "px": p["px"], "qty": p["q"],
                           "tp": p["tp"], "sl": p["sl"],
                           "now": last[p["s"]]} for p in pos],
            "last": last, "start": start, "days": test_days, "sl_pct": sl * 100, "tp_pct": tp * 100,
            "generated": dt.datetime.now(UTC).isoformat(timespec="seconds")}


if __name__ == "__main__":
    data = fetch_all()
    r = simulate(data)
    json.dump(r, open(os.path.join(HERE, "hft_state.json"), "w"))
    eq = r["cash"] + sum(p["qty"] * p["now"] for p in r["positions"])
    t = r["trades"]
    w = sum(1 for x in t if x["pnl_usd"] > 0)
    days = max((dt.datetime.now(UTC) - dt.datetime.fromisoformat(START).replace(tzinfo=UTC)).total_seconds()/86400, 0.01)
    print(f"счёт ${eq:.2f}  сделок {len(t)} ({len(t)/days:.1f}/день)  "
          f"winrate {w/len(t)*100 if t else 0:.0f}%  открыто {len(r['positions'])}")
