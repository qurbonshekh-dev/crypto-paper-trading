#!/usr/bin/env python3
"""
Бэктест схемы "держу до N дней, выхожу по тейку +X% или по рынку".
Комиссии учтены. Вход — на открытии дня, когда позиции нет.
"""
import datetime
from data import fetch

FEE = 0.001  # 0.1% на сторону, спот Binance без BNB-скидки


def backtest(candles, tp_pct, hold_days, sl_pct=None):
    """
    tp_pct   — тейк-профит, напр. 3.5
    hold_days— выйти по рынку, если тейк не сработал
    sl_pct   — стоп-лосс в %, None = без стопа
    """
    tp, sl = tp_pct / 100, (sl_pct / 100 if sl_pct else None)
    trades, equity, peak, max_dd = [], 1.0, 1.0, 0.0
    i = 0
    while i + hold_days < len(candles):
        entry = candles[i]["o"]
        target = entry * (1 + tp)
        stop = entry * (1 - sl) if sl else None
        exit_px, reason, held = None, None, hold_days

        for d in range(1, hold_days + 1):
            bar = candles[i + d]
            hit_sl = stop and bar["l"] <= stop
            hit_tp = bar["h"] >= target
            # консервативно: если за день задело и стоп и тейк — считаем стоп
            if hit_sl:
                exit_px, reason, held = stop, "stop", d
                break
            if hit_tp:
                exit_px, reason, held = target, "take", d
                break
        if exit_px is None:
            exit_px, reason = candles[i + hold_days]["c"], "time"

        gross = exit_px / entry - 1
        net = (exit_px * (1 - FEE)) / (entry * (1 + FEE)) - 1
        equity *= 1 + net
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak)
        trades.append({"net": net, "gross": gross, "reason": reason,
                       "t": candles[i]["t"], "held": held})
        i += held + 1  # вход не раньше СЛЕДУЮЩЕГО дня после выхода:
                       # вход на открытии дня выхода = цена до момента выхода

    return trades, equity, max_dd


def report(name, candles, tp, hold, sl=None):
    tr, eq, dd = backtest(candles, tp, hold, sl)
    wins = [t for t in tr if t["net"] > 0]
    losses = [t for t in tr if t["net"] <= 0]
    takes = sum(1 for t in tr if t["reason"] == "take")
    stops = sum(1 for t in tr if t["reason"] == "stop")
    years = (candles[-1]["t"] - candles[0]["t"]) / 1000 / 86400 / 365.25
    apy = (eq ** (1 / years) - 1) * 100

    avg_w = sum(t["net"] for t in wins) / len(wins) * 100 if wins else 0
    avg_l = sum(t["net"] for t in losses) / len(losses) * 100 if losses else 0

    sl_txt = f" SL{sl}%" if sl else " без стопа"
    print(f"\n  {name}  TP{tp}% / {hold}д{sl_txt}")
    print(f"    сделок {len(tr):>4}   тейк {takes:>4} ({takes/len(tr)*100:.0f}%)"
          + (f"   стоп {stops} ({stops/len(tr)*100:.0f}%)" if sl else ""))
    print(f"    winrate {len(wins)/len(tr)*100:>5.1f}%   ср.прибыль {avg_w:+.2f}%   ср.убыток {avg_l:+.2f}%")
    print(f"    итог капитала ×{eq:.2f}   годовых {apy:+.1f}%   макс.просадка {dd*100:.1f}%")
    return eq, apy, dd


if __name__ == "__main__":
    btc = fetch("BTCUSDT")
    # buy & hold для сравнения
    bh = btc[-1]["c"] / btc[0]["o"]
    years = (btc[-1]["t"] - btc[0]["t"]) / 1000 / 86400 / 365.25
    print(f"\n  ЭТАЛОН — купил и держал BTC {years:.1f} года:"
          f"  ×{bh:.1f}   годовых {((bh**(1/years))-1)*100:+.1f}%")

    print("\n" + "=" * 68)
    print("  ТВОЯ СХЕМА: тейк +3.5%, выход по рынку через 3 дня")
    print("=" * 68)
    report("BTC", btc, 3.5, 3)
    report("BTC", btc, 3.5, 3, sl=3.5)
    report("BTC", btc, 3.5, 3, sl=7)
