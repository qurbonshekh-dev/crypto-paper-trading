#!/usr/bin/env python3
"""Полный пересчёт на исправленном движке: есть ли ХОТЬ КАКОЙ-ТО набор параметров, который работает."""
from fair import sim, equity_stats, btc, MA, ma

days = (btc[-1]["t"] - btc[MA]["t"]) / 1000 / 86400


def apy(tp, hold, fee=None, use_filter=True):
    if use_filter:
        c = sim(MA, len(btc), "trade", tp=tp/100, hold=hold, fee=fee)
    else:
        c = sim_nofilter(tp/100, hold, fee)
    return equity_stats(c, days)


def sim_nofilter(tp, hold, fee=None):
    """Тот же исправленный движок, но без фильтра MA200."""
    from fair import FEE
    f = FEE if fee is None else fee
    cash, coin, curve = 1.0, 0.0, []
    target, exit_at, blocked = None, -1, -1
    for i in range(MA, len(btc)):
        o, h, c = btc[i]["o"], btc[i]["h"], btc[i]["c"]
        exited = False
        if coin > 0:
            if h >= target:
                cash, coin, exited = coin*target*(1-f), 0.0, True
            elif i >= exit_at:
                cash, coin, exited = coin*c*(1-f), 0.0, True
        if exited:
            blocked = i + 1
        if coin == 0 and cash > 0 and i >= blocked:
            coin, cash = cash*(1-f)/o, 0.0
            target, exit_at = o*(1+tp), i+hold
        curve.append(cash + coin*c)
    return curve


print("\n  ПЕРЕСЧЁТ НА ИСПРАВЛЕННОМ ДВИЖКЕ — годовых % (просадка)")
print("  эталон: купить и держать = +25.8%\n")
print("  С ФИЛЬТРОМ MA200")
print(f"    {'':8}" + "".join(f"{h}дн".rjust(14) for h in (2, 3, 4, 5, 7)))
for tp in (2.5, 3.0, 3.5, 4.0, 5.0, 8.0):
    row = []
    for hold in (2, 3, 4, 5, 7):
        _, a, dd = apy(tp, hold)
        row.append(f"{a:+.0f}% ({dd:.0f}dd)".rjust(14))
    print(f"    TP{tp:<5}" + "".join(row) + ("  <- твоя" if tp == 3.5 else ""))

print("\n  БЕЗ ФИЛЬТРА")
print(f"    {'':8}" + "".join(f"{h}дн".rjust(14) for h in (2, 3, 4, 5, 7)))
for tp in (3.0, 3.5, 5.0, 8.0):
    row = []
    for hold in (2, 3, 4, 5, 7):
        _, a, dd = apy(tp, hold, use_filter=False)
        row.append(f"{a:+.0f}% ({dd:.0f}dd)".rjust(14))
    print(f"    TP{tp:<5}" + "".join(row))

print("\n  ВЛИЯНИЕ КОМИССИИ на TP3.5%/3д + MA200")
for f, lbl in [(0.0, "0%   — комиссии нет вообще"),
               (0.00075, "0.075% — с BNB-скидкой"),
               (0.001, "0.1%  — обычный спот")]:
    eq, a, _ = apy(3.5, 3, fee=f)
    print(f"    {lbl:<30} ×{eq:>6.2f}   годовых {a:>+6.1f}%")
