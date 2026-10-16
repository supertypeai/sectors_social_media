// Hook for BYAN: one focused chart, the company's hairline flame mark large and faint behind it.
// The chart: weekly close since April as one line with a soft fill; only three things are labelled —
// the peak, the sale day (the accent), and today. No grid, no axis numbers.
const D = DATA, S = D.slide;
setAccent(D.direction);

// the mark, behind everything: centred low, where the chart lives
drawFlameMark(mk("g", { opacity: 0.11 }, svg), { S: 2.9, cx: 214, cy: 300, dropCls: "sil", floorOn: false });
frame(D);

typeRun(svg, M - 3, 104, [[S.hero.num, 70, 220], [S.hero.unit, 30, 250, TONE.muted]]);
const sentence = S.deal ? `of ${S.name} changed owner in one deal` : `of ${S.name} was ${S.verb} by ${S.holder}`;
let y = para(svg, M, 132, sentence, "title", { accent: [] });
type(svg, M, y + 16, `Stake ${S.before.toFixed(2)}% → ${S.after.toFixed(2)}%`, "body", { fill: TONE.muted });

// ---------------------------------------------------------------- the chart
const px = weekly(S.prices.map((p) => [dayOf(p.date), p.close]));
const CB = { x0: M, x1: W - M - 6, y0: 236, y1: 384 };
const t0 = px[0][0], t1 = px.at(-1)[0];
const vals = px.map((p) => p[1]), lo = Math.min(...vals), hi = Math.max(...vals), pad = (hi - lo) * 0.18;
const xs = scale(t0, t1, CB.x0, CB.x1), ys = scale(lo - pad, hi + pad, CB.y1, CB.y0);
const pts = px.map(([t, v]) => [xs(t), ys(v)]);
const g = mk("g", {}, svg);
const line = smoothPath(pts);

// soft fill under the line, and a baseline
const defs = mk("defs", {}, svg), lg = mk("linearGradient", { id: "cf", x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
mk("stop", { offset: 0, "stop-color": TONE.hi, "stop-opacity": 0.1 }, lg);
mk("stop", { offset: 1, "stop-color": TONE.hi, "stop-opacity": 0 }, lg);
mk("path", { d: `${line}L${pts.at(-1)[0]} ${CB.y1}L${pts[0][0]} ${CB.y1}Z`, style: "fill:url(#cf);stroke:none" }, g);
mk("line", { x1: CB.x0, y1: CB.y1, x2: CB.x1, y2: CB.y1, class: "lo thin" }, g);
mk("path", { d: line, class: "nf", style: `stroke:${TONE.hi};stroke-width:1.8px` }, g);

// month ticks on the baseline
const m = new Date(t0); m.setUTCDate(1); m.setUTCMonth(m.getUTCMonth() + 1);
for (; m.getTime() <= t1; m.setUTCMonth(m.getUTCMonth() + 1)) {
  const x = xs(m.getTime());
  mk("line", { x1: x, y1: CB.y1, x2: x, y2: CB.y1 + 3, class: "lo thin" }, g);
  type(g, x, CB.y1 + 12, fmtMonth(m.getTime()), "label", { fill: TONE.faint, size: 6.4, anchor: "middle" });
}

const at = (t) => { // the line's screen y at time t
  const i = px.findIndex(([tt]) => tt >= t);
  if (i <= 0) return pts[0][1];
  const [ta] = px[i - 1], [tb] = px[i];
  return pts[i - 1][1] + ((t - ta) / (tb - ta)) * (pts[i][1] - pts[i - 1][1]);
};
const point = (x, yy, fill, r = 3) => mk("circle", { cx: x, cy: yy, r, style: `fill:${fill};stroke:${TONE.ground};stroke-width:1.5px` }, g);

// 1 · the peak
const pk = vals.indexOf(hi), [pkx, pky] = pts[pk];
point(pkx, pky, TONE.hi);
// set to the left of the dot, so the sale label above-right has the space to itself
type(g, pkx - 8, pky + 1, `Rp ${hi.toLocaleString("en-US")}`, "label", { size: 9, weight: 650, anchor: "end" });
type(g, pkx - 8, pky + 9, `peak · ${fmtDay(px[pk][0])}`, "label", { size: 6.4, fill: TONE.muted, anchor: "end" });

// 2 · the sale day, the accent
const saleT = dayOf(S.prices.find((p) => p.date >= "2026-10-07").date), sx = xs(saleT), sy = at(saleT);
mk("line", { x1: sx, y1: CB.y0 - 4, x2: sx, y2: CB.y1, style: "stroke:var(--acc);stroke-dasharray:2 3;stroke-width:1px" }, g);
mk("circle", { cx: sx, cy: sy, r: 8, style: "fill:var(--acc);fill-opacity:.18;stroke:none" }, g);
point(sx, sy, "var(--acc)", 3.6);
type(g, sx - 6, CB.y0 + 2, `${S.sold.pct.toFixed(1)}% sold`, "label", { size: 10, weight: 700, fill: "var(--acc)", anchor: "end" });
type(g, sx - 6, CB.y0 + 11, S.day, "label", { size: 6.6, fill: TONE.muted, anchor: "end" });

// 3 · today
const [lx, ly] = pts.at(-1), lv = vals.at(-1);
point(lx, ly, TONE.hi);
type(g, lx, ly + 16, `Rp ${lv.toLocaleString("en-US")}`, "label", { size: 9, weight: 650, anchor: "end" });
type(g, lx, ly + 24, "now", "label", { size: 6.4, fill: TONE.muted, anchor: "end" });
type(g, CB.x0, CB.y0 - 8, "BYAN · WEEKLY CLOSE", "caps", { fill: TONE.faint, size: 5.6 });
