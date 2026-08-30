#!/usr/bin/env python3
"""
Движок виртуального счёта $100 — правила PLAN.md, зафиксированы.
Детерминированный: весь журнал — функция от дневных свечей и даты старта.

  вход:  сигнал A (BTC: объём>=2x И открытие>MA200) или B (альт: RSI14<30)
  лот $10, максимум 5 позиций, по одной на монету
  выход: тейк +4% | стоп -12% (стоп раньше тейка) | закрытие 5-го дня
  комиссия 0.1% на сторону
"""
import json, os, datetime as dt
import okx_data

HERE = os.path.dirname(os.path.abspath(__file__))
FEE = 0.001
LOT, MAX_POS = 10.0, 5
TP, SL, HOLD = 0.04, 0.12, 5           # HOLD=5: выход на закрытии 5-го дня (entry+4)
VOLX = 1.95                            # порог объёма сигнала A (1.95 с 25.08, до первой сделки)
RSI_WIN = 250
START = "2026-08-25"                   # сигналы этого дня -> первый вход 26-го
TEST_DAYS = 30
EXCLUDE = {"EURUSDT", "WBTCUSDT"}
UTC = dt.timezone.utc


def pairs():
    """Список пар зафиксирован; отобраны те, что есть на OKX."""
    f = os.path.join(HERE, "trading_pairs_okx.json")
    if not os.path.exists(f):
        f = os.path.join(HERE, "trading_pairs.json")
    return [x for x in json.load(open(f)) if x not in EXCLUDE]


def klines(symbol, limit=400):
    return okx_data.daily(symbol, limit)


def fetch_all(limit=400):
    return {s: klines(s, limit) for s in pairs()}


def wilder_rsi(closes):
    """RSI14 по Уайлдеру на фиксированном окне (детерминизм Python == JS)."""
    n = 14
    if len(closes) < n + 1:
        return None
    au = sum(max(closes[i]-closes[i-1], 0.0) for i in range(1, n+1)) / n
    ad = sum(max(closes[i-1]-closes[i], 0.0) for i in range(1, n+1)) / n
    for i in range(n+1, len(closes)):
        u = max(closes[i]-closes[i-1], 0.0)
        d = max(closes[i-1]-closes[i], 0.0)
        au = (au*(n-1)+u)/n
        ad = (ad*(n-1)+d)/n
    return 100.0 if ad == 0 else 100.0 - 100.0/(1.0 + au/ad)


DIP_TH = -0.05                         # счёт 2: вчерашнее падение >= 5%
TIGHT_TH, TIGHT_TP, TIGHT_SL = -0.04, 0.035, 0.04   # счёт 3: вход -4%, тейк +3.5%, стоп -4%


def simulate(data, start=START, mode="signals", last_complete=None):
    """last_complete — последний ЗАКРЫТЫЙ день; время-стоп срабатывает только на нём
    и раньше, чтобы не записать выход по промежуточной цене незакрытой свечи."""
    """data: {sym: [{d,o,h,l,c,v}...]}  ->  полное состояние счёта."""
    idx = {s: {b["d"]: i for i, b in enumerate(rows)} for s, rows in data.items()}
    btc = data["BTCUSDT"]
    days = [b["d"] for b in btc if b["d"] > start]      # торговые дни теста
    end_entries = (dt.date.fromisoformat(start) + dt.timedelta(days=TEST_DAYS)).isoformat()

    cash, positions, trades, curve = 100.0, [], [], []
    bench_qty = None

    def sig_A(day):
        i = idx["BTCUSDT"].get(day)
        if i is None or i < RSI_WIN:
            return False
        rows = btc
        ma200 = sum(r["c"] for r in rows[i-200:i]) / 200
        vol20 = sum(r["v"] for r in rows[i-21:i-1]) / 20
        return rows[i]["o"] > ma200 and vol20 > 0 and rows[i-1]["v"] >= VOLX*vol20

    def sig_B(sym, day):
        i = idx[sym].get(day)
        if i is None or i < RSI_WIN:
            return None
        closes = [r["c"] for r in data[sym][i-RSI_WIN:i]]
        r = wilder_rsi(closes)
        return r if (r is not None and r < 30) else None

    for day in days:
        # --- входы на открытии дня (сигналы по завершённым дням) ---
        if day <= end_entries:
            cands = []
            held = {p["sym"] for p in positions}
            if mode in ("dip", "tight"):
                th = DIP_TH if mode == "dip" else TIGHT_TH
                tag = "D" if mode == "dip" else "T"
                for s in pairs():
                    if s in held:
                        continue
                    i = idx[s].get(day)
                    if i is None or i < 2:
                        continue
                    r = data[s][i-1]["c"] / data[s][i-2]["c"] - 1
                    if r <= th:
                        cands.append((tag, s, r))
                cands.sort(key=lambda x: x[2])
            else:
                if "BTCUSDT" not in held and sig_A(day):
                    cands.append(("A", "BTCUSDT", -1.0))
                for s in pairs():
                    if s == "BTCUSDT" or s in held:
                        continue
                    r = sig_B(s, day)
                    if r is not None:
                        cands.append(("B", s, r))
                cands.sort(key=lambda x: (x[0] != "A", x[2]))
            for kind, sym, _ in cands:
                if len(positions) >= MAX_POS or cash < LOT:
                    break
                i = idx[sym].get(day)
                if i is None:
                    continue
                px = data[sym][i]["o"]
                qty = LOT * (1-FEE) / px
                cash -= LOT
                tp_i, sl_i = (TIGHT_TP, TIGHT_SL) if mode == "tight" else (TP, SL)
                positions.append({"sym": sym, "day": day, "px": px, "qty": qty,
                                  "sig": kind, "target": px*(1+tp_i), "stop": px*(1-sl_i)})

        # --- выходы в течение дня ---
        still = []
        for p in positions:
            i = idx[p["sym"]].get(day)
            if i is None:
                still.append(p); continue
            bar = data[p["sym"]][i]
            age = (dt.date.fromisoformat(day) - dt.date.fromisoformat(p["day"])).days
            exit_px = reason = None
            if bar["l"] <= p["stop"]:
                exit_px, reason = p["stop"], "stop"        # консервативно: стоп раньше тейка
            elif bar["h"] >= p["target"]:
                exit_px, reason = p["target"], "take"
            elif age >= HOLD - 1 and (last_complete is None or day <= last_complete):
                exit_px, reason = bar["c"], "time"
            if exit_px is None:
                still.append(p)
            else:
                proceeds = p["qty"] * exit_px * (1-FEE)
                cash += proceeds
                trades.append({"sym": p["sym"], "sig": p["sig"],
                               "in_d": p["day"], "in_px": round(p["px"], 8),
                               "out_d": day, "out_px": round(exit_px, 8),
                               "reason": reason,
                               "pnl_usd": round(proceeds - LOT, 4),
                               "pnl_pct": round((proceeds/LOT - 1)*100, 3)})
        positions = still

        # --- бенчмарк и кривая капитала (по закрытию дня) ---
        ib = idx["BTCUSDT"].get(day)
        if bench_qty is None and ib is not None:
            bench_qty = 100.0 * (1-FEE) / btc[ib]["o"]
        mark = cash + sum(
            p["qty"] * data[p["sym"]][idx[p["sym"]][day]]["c"]
            for p in positions if day in idx[p["sym"]])
        curve.append({"d": day, "eq": round(mark, 4),
                      "bench": round(bench_qty * btc[ib]["c"], 4) if ib is not None else None})

    return {"cash": round(cash, 4), "positions": positions, "trades": trades,
            "curve": curve, "start": start, "end_entries": end_entries}


if __name__ == "__main__":
    import sys
    start = sys.argv[1] if len(sys.argv) > 1 else START
    data = fetch_all()
    json.dump(data, open(os.path.join(HERE, "plat_data.json"), "w"))
    r = simulate(data, start)
    print(f"старт {r['start']}, входы до {r['end_entries']}")
    print(f"сделок закрыто: {len(r['trades'])}, открыто позиций: {len(r['positions'])}, "
          f"кэш {r['cash']:.2f}")
    for t in r["trades"]:
        print(f"  {t['sig']} {t['sym']:<10} {t['in_d']} {t['in_px']:>12,.6g} -> "
              f"{t['out_d']} {t['out_px']:>12,.6g}  {t['reason']:<5} {t['pnl_pct']:>+7.2f}%")
    for p in r["positions"]:
        print(f"  ОТКРЫТА {p['sym']:<10} с {p['day']} по {p['px']:,.6g}")
    if r["curve"]:
        last = r["curve"][-1]
        print(f"итог: счёт {last['eq']:.2f}  бенчмарк BTC {last['bench']:.2f}")
