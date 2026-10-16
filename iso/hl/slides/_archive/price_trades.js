// The price, and the trades on it, kept quiet: a smooth weekly line, the small trades as faint dots on
// it, the one big trade bright and labelled, the average cost as a dashed level, and today called out.
// No gridlines, no axis numbers: only the two end dates. DATA.slide: { title, accent[], sub,
// prices: [{date, close}], trades: [{date, price, value}], avg, avgLabel, big: { head, sub }, now: { head, sub } }.
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);
let y = para(svg, M, 74, S.title, "title", { accent: S.accent });
type(svg, M, y + 16, S.sub, "body", { fill: TONE.muted });

const px = weekly(S.prices.map((p) => [dayOf(p.date), p.close]));
const t0 = px[0][0], t1 = px.at(-1)[0];
const vals = [...px.map((p) => p[1]), S.avg, ...S.trades.map((t) => t.price)];
const lo = Math.min(...vals), hi = Math.max(...vals), pad = (hi - lo) * 0.1;
const P0 = { ...PLOT, y0: y + 54, y1: 384 };
const xs = scale(t0, t1, P0.x0, P0.x1 - 58), ys = scale(lo - pad, hi + pad, P0.y1, P0.y0);
const g = mk("g", {}, svg);
const yOn = (t) => { // the line's height on a given day, so trade dots sit on the line, not at their fill price
  const i = px.findIndex(([tt]) => tt >= t);
  if (i <= 0) return px[Math.max(0, i)][1];
  const [ta, va] = px[i - 1], [tb, vb] = px[i];
  return va + ((t - ta) / (tb - ta)) * (vb - va);
};

// the line, with a whisper of fill
// straight weekly segments: curving through sparse points invents swings the price never made
const pts = px.map(([t, v]) => [xs(t), ys(v)]), line = pts.map(([x, yy], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${yy.toFixed(1)}`).join("");
const defs = mk("defs", {}, svg), lg = mk("linearGradient", { id: "pf", x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
mk("stop", { offset: 0, "stop-color": TONE.hi, "stop-opacity": 0.07 }, lg);
mk("stop", { offset: 1, "stop-color": TONE.hi, "stop-opacity": 0 }, lg);
mk("path", { d: `${line}L${pts.at(-1)[0]} ${P0.y1}L${pts[0][0]} ${P0.y1}Z`, style: "fill:url(#pf);stroke:none" }, g);
mk("path", { d: line, class: "nf", style: `stroke:${TONE.hi};stroke-width:1.8px` }, g);

// average cost
const ya = ys(S.avg);
mk("line", { x1: P0.x0, y1: ya, x2: P0.x1 - 58, y2: ya, class: "nf", style: "stroke:var(--acc);stroke-dasharray:2 4;stroke-width:1.1px" }, g);
// in the right gutter, level with the line: the price never runs there, so nothing crosses it
type(g, P0.x1 - 52, ya + 2.6, S.avgLabel, "label", { fill: "var(--acc)", size: 7.4, weight: 650 });

// trades: small ones faint, the big one bright and called out
const maxV = Math.max(...S.trades.map((t) => t.value));
for (const t of S.trades) {
  if (t.value === maxV) continue;
  mk("circle", { cx: xs(dayOf(t.date)), cy: ys(yOn(dayOf(t.date))), r: 2, style: "fill:var(--acc);opacity:.55" }, g);
}
const big = S.trades.find((t) => t.value === maxV), bx = xs(dayOf(big.date)), by = ys(yOn(dayOf(big.date)));
mk("circle", { cx: bx, cy: by, r: 9, style: "fill:var(--acc);fill-opacity:.18;stroke:none" }, g);
mk("circle", { cx: bx, cy: by, r: 4, style: "fill:var(--acc)" }, g);
const up = by > (P0.y0 + P0.y1) / 2, ty = up ? P0.y0 + 8 : P0.y1 - 20;
mk("line", { x1: bx, y1: by + (up ? -10 : 10), x2: bx, y2: ty + (up ? 12 : -16), class: "nf thin", style: `stroke:${TONE.faint}` }, g);
type(g, bx, ty, S.big.head, "label", { fill: "var(--acc)", size: 15, weight: 650, anchor: "middle" });
type(g, bx, ty + 11, S.big.sub, "label", { fill: TONE.muted, size: 7, anchor: "middle" });

// today
const [tn, vn] = px.at(-1), nx = xs(tn), ny = ys(vn);
mk("circle", { cx: nx, cy: ny, r: 3, style: `fill:${TONE.hi}` }, g);
type(g, nx + 7, ny - 2, S.now.head, "label", { size: 15, weight: 650 });
type(g, nx + 7, ny + 10, S.now.sub, "label", { size: 7.4, fill: TONE.muted });

// the two ends of time, nothing between
type(g, P0.x0, P0.y1 + 16, fmtDay(t0), "label", { fill: TONE.faint, size: 7 });
type(g, nx, P0.y1 + 16, fmtDay(tn), "label", { fill: TONE.faint, size: 7, anchor: "middle" });
