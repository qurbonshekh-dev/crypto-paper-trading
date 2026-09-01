#!/usr/bin/env python3
"""Собирает hft_dashboard.html: свежий прогон движка + шаблон."""
import json, os
import hft_engine

HERE = os.path.dirname(os.path.abspath(__file__))
data = hft_engine.fetch_all()
state = hft_engine.simulate(data)
tpl = open(os.path.join(HERE, "hft_template.html")).read()
html = tpl.replace("__DATA_JSON__", json.dumps(state, separators=(",", ":")))
open(os.path.join(HERE, "hft_dashboard.html"), "w").write(html)
json.dump(state, open(os.path.join(HERE, "hft_state.json"), "w"))  # для внешних проверок
eq = state["cash"] + sum(p["qty"]*p["now"] for p in state["positions"])
print(f"hft_dashboard.html собран: {len(html)/1024:.0f} КБ · счёт ${eq:.2f} · "
      f"сделок {len(state['trades'])} · открыто {len(state['positions'])}")
