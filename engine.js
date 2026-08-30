// Движок виртуального счёта — зеркало plat_engine.py. Логика 1:1.
const FEE = 0.001, LOT = 10.0, MAX_POS = 5, VOLX = 1.95, DIP_TH = -0.05;
const TIGHT_TH = -0.04, TIGHT_TP = 0.035, TIGHT_SL = 0.04;
const TP = 0.04, SL = 0.12, HOLD = 5, RSI_WIN = 250;
const EXCLUDE = new Set(["EURUSDT", "WBTCUSDT"]);

function wilderRsi(closes) {
  const n = 14;
  if (closes.length < n + 1) return null;
  let au = 0, ad = 0;
  for (let i = 1; i <= n; i++) {
    au += Math.max(closes[i] - closes[i-1], 0.0);
    ad += Math.max(closes[i-1] - closes[i], 0.0);
  }
  au /= n; ad /= n;
  for (let i = n + 1; i < closes.length; i++) {
    const u = Math.max(closes[i] - closes[i-1], 0.0);
    const d = Math.max(closes[i-1] - closes[i], 0.0);
    au = (au * (n-1) + u) / n;
    ad = (ad * (n-1) + d) / n;
  }
  return ad === 0 ? 100.0 : 100.0 - 100.0 / (1.0 + au / ad);
}

function dayDiff(a, b) {  // b - a в днях, ISO-строки
  return Math.round((Date.parse(b + "T00:00:00Z") - Date.parse(a + "T00:00:00Z")) / 86400000);
}

function addDays(iso, n) {
  const t = new Date(Date.parse(iso + "T00:00:00Z") + n * 86400000);
  return t.toISOString().slice(0, 10);
}

function simulate(data, start, testDays, mode, lastComplete) {
  mode = mode || "signals";
  const pairs = Object.keys(data).filter(s => !EXCLUDE.has(s));
  const idx = {};
  for (const s of pairs) {
    idx[s] = {};
    data[s].forEach((b, i) => { idx[s][b.d] = i; });
  }
  const btc = data["BTCUSDT"];
  const days = btc.filter(b => b.d > start).map(b => b.d);
  const endEntries = addDays(start, testDays);

  let cash = 100.0, positions = [], trades = [], curve = [], benchQty = null;

  const sigA = (day) => {
    const i = idx["BTCUSDT"][day];
    if (i === undefined || i < RSI_WIN) return false;
    let ma200 = 0; for (let k = i-200; k < i; k++) ma200 += btc[k].c; ma200 /= 200;
    let vol20 = 0; for (let k = i-21; k < i-1; k++) vol20 += btc[k].v; vol20 /= 20;
    return btc[i].o > ma200 && vol20 > 0 && btc[i-1].v >= VOLX * vol20;
  };
  const sigB = (sym, day) => {
    const i = idx[sym][day];
    if (i === undefined || i < RSI_WIN) return null;
    const closes = data[sym].slice(i - RSI_WIN, i).map(r => r.c);
    const r = wilderRsi(closes);
    return (r !== null && r < 30) ? r : null;
  };

  for (const day of days) {
    if (day <= endEntries) {
      const held = new Set(positions.map(p => p.sym));
      const cands = [];
      if (mode === "dip" || mode === "tight") {
        const th = mode === "dip" ? DIP_TH : TIGHT_TH;
        const tag = mode === "dip" ? "D" : "T";
        for (const s of pairs) {
          if (held.has(s)) continue;
          const i = idx[s][day];
          if (i === undefined || i < 2) continue;
          const r = data[s][i-1].c / data[s][i-2].c - 1;
          if (r <= th) cands.push([tag, s, r]);
        }
        cands.sort((x, y) => x[2] - y[2]);
      } else {
        if (!held.has("BTCUSDT") && sigA(day)) cands.push(["A", "BTCUSDT", -1.0]);
        for (const s of pairs) {
          if (s === "BTCUSDT" || held.has(s)) continue;
          const r = sigB(s, day);
          if (r !== null) cands.push(["B", s, r]);
        }
        cands.sort((x, y) => (x[0] !== "A") - (y[0] !== "A") || x[2] - y[2]);
      }
      for (const [kind, sym] of cands) {
        if (positions.length >= MAX_POS || cash < LOT) break;
        const i = idx[sym][day];
        if (i === undefined) continue;
        const px = data[sym][i].o;
        const qty = LOT * (1 - FEE) / px;
        cash -= LOT;
        const tpI = mode === "tight" ? TIGHT_TP : TP;
        const slI = mode === "tight" ? TIGHT_SL : SL;
        positions.push({sym, day, px, qty, sig: kind,
                        target: px * (1 + tpI), stop: px * (1 - slI)});
      }
    }

    const still = [];
    for (const p of positions) {
      const i = idx[p.sym][day];
      if (i === undefined) { still.push(p); continue; }
      const bar = data[p.sym][i];
      const age = dayDiff(p.day, day);
      let exitPx = null, reason = null;
      if (bar.l <= p.stop) { exitPx = p.stop; reason = "stop"; }
      else if (bar.h >= p.target) { exitPx = p.target; reason = "take"; }
      else if (age >= HOLD - 1 && (!lastComplete || day <= lastComplete)) { exitPx = bar.c; reason = "time"; }
      if (exitPx === null) still.push(p);
      else {
        const proceeds = p.qty * exitPx * (1 - FEE);
        cash += proceeds;
        trades.push({sym: p.sym, sig: p.sig, in_d: p.day, in_px: p.px,
                     out_d: day, out_px: exitPx, reason,
                     pnl_usd: proceeds - LOT, pnl_pct: (proceeds / LOT - 1) * 100});
      }
    }
    positions = still;

    const ib = idx["BTCUSDT"][day];
    if (benchQty === null && ib !== undefined) benchQty = 100.0 * (1 - FEE) / btc[ib].o;
    let mark = cash;
    for (const p of positions) {
      const ip = idx[p.sym][day];
      if (ip !== undefined) mark += p.qty * data[p.sym][ip].c;
    }
    curve.push({d: day, eq: mark,
                bench: ib !== undefined ? benchQty * btc[ib].c : null});
  }
  return {cash, positions, trades, curve, start, endEntries};
}

if (typeof module !== "undefined") module.exports = {simulate, wilderRsi};
