#!/usr/bin/env python3
"""
Realtime crypto price monitor — Binance public WebSocket.
No API key, no registration, no rate limit on the stream.

usage:  python3 monitor.py BTCUSDT ETHUSDT SOLUSDT
"""
import asyncio
import json
import sys
import time

import websockets

WS_BASE = "wss://stream.binance.com:9443/stream?streams="
RECONNECT_DELAY = 2  # seconds, grows on repeated failures


def build_url(symbols):
    # miniTicker = last price + 24h open/high/low/volume, pushed ~1/sec
    streams = "/".join(f"{s.lower()}@miniTicker" for s in symbols)
    return WS_BASE + streams


def render(state):
    sys.stdout.write("\033[2J\033[H")  # clear screen, cursor home
    print(f"  Binance realtime  ·  {time.strftime('%H:%M:%S')}\n")
    print(f"  {'SYMBOL':<10} {'PRICE':>14} {'24h %':>9} {'24h HIGH':>14} {'24h LOW':>14}")
    print("  " + "-" * 65)
    for sym in sorted(state):
        d = state[sym]
        last, open_ = float(d["c"]), float(d["o"])
        pct = (last - open_) / open_ * 100 if open_ else 0.0
        color = "\033[32m" if pct >= 0 else "\033[31m"
        print(
            f"  {sym:<10} {last:>14,.4f} {color}{pct:>8.2f}%\033[0m "
            f"{float(d['h']):>14,.4f} {float(d['l']):>14,.4f}"
        )
    print("\n  Ctrl+C to exit")


async def run(symbols):
    state = {}
    delay = RECONNECT_DELAY
    while True:
        try:
            async with websockets.connect(build_url(symbols), ping_interval=20) as ws:
                delay = RECONNECT_DELAY  # connected, reset backoff
                async for raw in ws:
                    d = json.loads(raw)["data"]
                    state[d["s"]] = d
                    render(state)
        except (websockets.ConnectionClosed, OSError, asyncio.TimeoutError) as e:
            print(f"\n  reconnecting in {delay}s ({type(e).__name__})")
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30)


if __name__ == "__main__":
    syms = [s.upper() for s in sys.argv[1:]] or ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    try:
        asyncio.run(run(syms))
    except KeyboardInterrupt:
        print("\nbye")
