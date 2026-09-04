#!/usr/bin/env python3
"""Собирает hft_dashboard.html: два счёта на одних 5-минутных свечах + шаблон.

  a — «Стоп −1%»: исходные правила, старт 30.08.2026
  b — «Стоп −3%»: то же, но стоп −3%, старт 04.09.2026 (добавлен по итогам
      проверки на трёх периодах; forward-тест, задним числом не досчитан)
"""
import json, os
import hft_engine

HERE = os.path.dirname(os.path.abspath(__file__))
data = hft_engine.fetch_all()
a = hft_engine.simulate(data)                                   # стоп 1%, с 30.08
b = hft_engine.simulate(data, start="2026-09-04", sl=0.03)      # стоп 3%, с 04.09
tpl = open(os.path.join(HERE, "hft_template.html")).read()
html = tpl.replace("__DATA_JSON__", json.dumps({"a": a, "b": b}, separators=(",", ":")))
open(os.path.join(HERE, "hft_dashboard.html"), "w").write(html)
json.dump(a, open(os.path.join(HERE, "hft_state.json"), "w"))       # для внешних проверок
json.dump(b, open(os.path.join(HERE, "hft_state_wide.json"), "w"))
for name, s in (("стоп −1%", a), ("стоп −3%", b)):
    eq = s["cash"] + sum(p["qty"] * p["now"] for p in s["positions"])
    print(f"  {name}: счёт ${eq:.2f} · сделок {len(s['trades'])} · открыто {len(s['positions'])}")
print(f"hft_dashboard.html собран: {len(html)/1024:.0f} КБ")
