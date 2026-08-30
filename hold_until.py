#!/usr/bin/env python3
"""
"Держим, пока не будет +X%, потом продаём. В убыток не закрываем никогда."

Считаем ДВЕ вещи по отдельности:
  1. журнал закрытых сделок  — все они прибыльные по определению
  2. фактическое состояние счёта — включая позицию, которая на конец
     периода всё ещё открыта и сидит в минусе

Расхождение между 1 и 2 и есть ответ на вопрос "почему минус".
"""
import sys
from data import fetch

FEE = 0.001
MA_LEN = 200


def run(c, tp, use_filter=False, fee=FEE):
    closes = [x["c"] for x in c]
    ma = [None]*len(c)
    s = sum(closes[:MA_LEN])
    for i in range(MA_LEN, len(c)):
        ma[i] = s/MA_LEN
        s += closes[i] - closes[i-MA_LEN]

    cash, coin = 1.0, 0.0
    entry, target, blocked = None, None, -1
    entry_i = None
    wins, losses, profits, waits = 0, 0, [], []
    curve = []
    stuck_max = 0

    for i in range(MA_LEN, len(c)):
        o, h, cl = c[i]["o"], c[i]["h"], c[i]["c"]

        if coin > 0 and h >= target:                  # единственный выход — в плюс
            cash, coin = coin*target*(1-fee), 0.0
            pnl = (target*(1-fee))/(entry*(1+fee)) - 1
            profits.append(pnl)
            waits.append(i - entry_i)
            wins += pnl > 0
            losses += pnl <= 0
            blocked = i + 1                           # вход не раньше следующего дня

        if coin == 0 and cash > 0 and i >= blocked:
            if (not use_filter) or (ma[i] and o > ma[i]):
                coin, cash = cash*(1-fee)/o, 0.0
                entry, target, entry_i = o, o*(1+tp), i

        if coin > 0:
            stuck_max = max(stuck_max, i - entry_i)
        curve.append(cash + coin*cl)

    open_pos = None
    if coin > 0:
        open_pos = {"entry": entry, "now": c[-1]["c"],
                    "pnl": (c[-1]["c"]*(1-fee))/(entry*(1+fee)) - 1,
                    "days": len(c)-1-entry_i}
    return {"curve": curve, "closed": len(profits), "wins": wins, "losses": losses,
            "profits": profits, "waits": waits, "open": open_pos,
            "stuck_max": stuck_max, "eq": curve[-1]}


def show(sym, tp, use_filter=False):
    c = fetch(sym)
    if len(c) < MA_LEN + 200:
        return None
    r = run(c, tp/100, use_filter)
    days = (c[-1]["t"] - c[MA_LEN]["t"])/1000/86400
    yrs = days/365.25
    bh_qty = (1-FEE)/c[MA_LEN]["o"]
    bh = bh_qty * c[-1]["c"]

    print(f"\n  {sym}   тейк +{tp}%   {'фильтр MA200' if use_filter else 'без фильтра'}")
    print("  " + "-"*66)
    print(f"    ЖУРНАЛ СДЕЛОК (то, что ты видел бы в отчёте брокера)")
    print(f"      закрытых сделок        {r['closed']}")
    print(f"      из них прибыльных      {r['wins']}   убыточных {r['losses']}")
    print(f"      winrate                {r['wins']/max(r['closed'],1)*100:.1f}%")
    if r["profits"]:
        tot = 1.0
        for p in r["profits"]:
            tot *= 1+p
        print(f"      сумма всех закрытий    {(tot-1)*100:+,.0f}%")
        print(f"      среднее ожидание входа {sum(r['waits'])/len(r['waits']):.0f} дн., "
              f"самое долгое {max(r['waits'])} дн.")
    print(f"\n    ФАКТИЧЕСКИЙ СЧЁТ")
    print(f"      итог                   ×{r['eq']:.2f}   годовых "
          f"{((r['eq']**(1/yrs)-1)*100 if r['eq']>0 else -100):+.1f}%")
    print(f"      купить и держать       ×{bh:.2f}   годовых "
          f"{((bh**(1/yrs)-1)*100 if bh>0 else -100):+.1f}%")
    if r["open"]:
        o = r["open"]
        print(f"      ОТКРЫТАЯ ПОЗИЦИЯ: вход {o['entry']:,.4f} → сейчас {o['now']:,.4f}"
              f"  ({o['pnl']*100:+.1f}%), висит {o['days']} дн.")
    else:
        print(f"      открытых позиций нет")
    return r


if __name__ == "__main__":
    for tp in (3.0, 5.0):
        show("BTCUSDT", tp)
