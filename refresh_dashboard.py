#!/usr/bin/env python3
"""Собирает dashboard.html: свежие свечи + шаблон + движок."""
import json, os, datetime as dt
from plat_engine import fetch_all

HERE = os.path.dirname(os.path.abspath(__file__))
now = dt.datetime.now(dt.timezone.utc)
data = fetch_all(limit=330)
blob = {"generated": now.isoformat(timespec="seconds"),
        "lastComplete": (now.date() - dt.timedelta(days=1)).isoformat(),
        "candles": data}
tpl = open(os.path.join(HERE, "dashboard_template.html")).read()
eng = open(os.path.join(HERE, "engine.js")).read()
html = (tpl.replace("__ENGINE_JS__", eng)
           .replace("__DATA_JSON__", json.dumps(blob, separators=(",", ":"))))
open(os.path.join(HERE, "dashboard.html"), "w").write(html)
print(f"dashboard.html собран: {len(html)/1024:.0f} КБ, данные на {blob['lastComplete']}")
