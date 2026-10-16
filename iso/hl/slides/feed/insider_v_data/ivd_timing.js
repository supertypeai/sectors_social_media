// Insider "story of the deal", slide 3: timing. A year of the price with the holder's own trades in this
// stock on it (each leg at its real price), the deal day marked, then a ruler: where that day's close sat
// between the year's low and high.
// DATA.slide: { title, answer, prices: [{date, close}], trades: [{date, price, buy, move}], moveDate, close, now, lo, hi, rank }
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

let y = para(svg, M, 74, S.title, "title", { maxW: W - 2 * M });
wrapText(S.answer, 10, W - 2 * M).forEach((l, i) => type(svg, M, y + 22 + i * 13, l, "body", { size: 10, fill: TONE.muted }));

// ---------------------------------------------------------------- the year, and the holder's trades on it
const B = { x0: M, x1: W - M - 4, y0: y + 62, y1: 290 };
const px = S.prices.map((p) => [dayOf(p.date), p.close]);
const t0 = px[0][0], t1 = px.at(-1)[0];
const vals = [...px.map((p) => p[1]), ...S.trades.map((t) => t.price)];
const lo = Math.min(...vals) * 0.9, hi = Math.max(...vals) * 1.06;
const xs = scale(t0, t1, B.x0, B.x1), ys = scale(lo, hi, B.y1, B.y0);
const pts = weekly(px).map(([t, v]) => [xs(t), ys(v)]);
pts.push([xs(t1), ys(px.at(-1)[1])]);
const g = mk("g", {}, svg);
for (const v of niceTicks(lo, hi, 3)) {
  mk("line", { x1: B.x0, y1: ys(v), x2: W - M, y2: ys(v), class: "lo thin" }, g);
  type(g, B.x0, ys(v) - 3, rp(v), "label", { fill: TONE.faint, size: 6.2 });
}
areaLine(g, pts, B.y1, { color: TONE.edge, width: 1.4, fill: 0.08 });
// month ticks
{
  const d = new Date(t0); d.setUTCDate(1); d.setUTCMonth(d.getUTCMonth() + 1);
  for (let k = 0; d.getTime() <= t1; d.setUTCMonth(d.getUTCMonth() + 1), k++) {
    if (k % 2 || Math.abs(xs(d.getTime()) - xs(dayOf(S.moveDate))) < 30) continue;
    type(g, xs(d.getTime()), B.y1 + 11, fmtMonth(d.getTime()), "label", { fill: TONE.faint, size: 6.2, anchor: "middle" });
  }
}
// the deal day
const xm = xs(dayOf(S.moveDate));
mk("line", { x1: xm, y1: B.y0 - 6, x2: xm, y2: B.y1, style: "stroke:var(--acc);stroke-dasharray:2 3;stroke-width:1px" }, g);
type(g, Math.min(xm, W - M - 14), B.y1 + 11, fmtDay(dayOf(S.moveDate)), "label", { fill: "var(--acc)", size: 7, weight: 700, anchor: "middle" });
// the holder's earlier trades: buys filled, sells hollow
for (const t of S.trades.filter((t) => !t.move)) {
  const x = xs(dayOf(t.date)), yy = ys(t.price);
  if (t.buy) mk("circle", { cx: x, cy: yy, r: 2.3, style: `fill:${TONE.hi};fill-opacity:.7;stroke:${TONE.ground};stroke-width:.6px` }, g);
  else mk("circle", { cx: x, cy: yy, r: 2.3, style: `fill:${TONE.ground};stroke:${TONE.hi};stroke-width:1px` }, g);
}
// this deal's legs, in the accent; the close that day on the line
const legs = S.trades.filter((t) => t.move);
const prices = [...new Set(legs.map((t) => t.price))];
prices.forEach((p) => glowDot(g, xs(dayOf(legs.find((t) => t.price === p).date)), ys(p), "var(--acc)", 3));
const cy = yAt(pts, xm);
mk("circle", { cx: xm, cy, r: 2.6, style: `fill:${TONE.hi};stroke:${TONE.ground};stroke-width:1px` }, g);
// label the deal price below its lowest dot, at the side with room
const pmin = Math.min(...prices), pmax = Math.max(...prices), left = xm > W * 0.6;
const lab = prices.length > 1 ? `deal: ${rp(pmin)}–${rp(pmax).replace("Rp ", "")}` : `deal: ${rp(pmin)}`;
const ly = B.y1 - 5; // the floor of the plot: the price line rarely runs along it next to the deal day
type(g, xm + (left ? -7 : 7), ly, lab, "label", { fill: "var(--acc)", size: 8.2, weight: 700, anchor: left ? "end" : "start" });
type(g, xm + (left ? -7 : 7), Math.max(B.y0 + 8, cy - 8), `close ${rp(S.close)}`, "label", { fill: TONE.hi, size: 7.4, weight: 600, anchor: left ? "end" : "start" });

// key
const earlier = S.trades.some((t) => !t.move);
if (earlier) {
  const ky = B.y1 + 24;
  mk("circle", { cx: M + 2.5, cy: ky - 2.4, r: 2.3, style: `fill:${TONE.hi};fill-opacity:.7;stroke:none` }, svg);
  type(svg, M + 8, ky, "earlier buy", "label", { fill: TONE.muted, size: 6.6 });
  mk("circle", { cx: M + 54, cy: ky - 2.4, r: 2.3, style: `fill:none;stroke:${TONE.hi};stroke-width:1px` }, svg);
  type(svg, M + 60, ky, "earlier sell", "label", { fill: TONE.muted, size: 6.6 });
  mk("circle", { cx: M + 107, cy: ky - 2.4, r: 2.3, style: "fill:var(--acc);stroke:none" }, svg);
  type(svg, M + 113, ky, "this deal", "label", { fill: TONE.muted, size: 6.6 });
}

// ---------------------------------------------------------------- the ruler: the deal day in the year's range
const RY = 362, rx0 = M + 6, rx1 = W - M - 6, rs = scale(S.lo, S.hi, rx0, rx1);
mk("line", { x1: M, y1: RY - 37, x2: W - M, y2: RY - 37, class: "lo thin" }, svg);
type(svg, M, RY - 25, "The deal day in the past year's range", "caps", { fill: TONE.muted });
mk("rect", { x: rx0, y: RY - 3, width: rx1 - rx0, height: 6, rx: 3, style: `fill:${TONE.lo};stroke:none` }, svg);
for (const f of [1 / 3, 2 / 3]) mk("line", { x1: rx0 + f * (rx1 - rx0), y1: RY - 5, x2: rx0 + f * (rx1 - rx0), y2: RY + 5, style: `stroke:${TONE.ground};stroke-width:1.4px` }, svg);
const xc = rs(S.close);
mk("rect", { x: rx0, y: RY - 3, width: Math.max(3, xc - rx0), height: 6, rx: 3, style: "fill:var(--acc);fill-opacity:.45;stroke:none" }, svg);
glowDot(svg, xc, RY, "var(--acc)", 4);
type(svg, Math.min(Math.max(xc, rx0 + 30), rx1 - 30), RY - 9, `${S.rank}% of days lower`, "label", { fill: "var(--acc)", size: 8, weight: 700, anchor: "middle" });
// today, as a hollow ring on the ruler; at either end it joins that end's label instead of crowding it
const xn = rs(Math.min(Math.max(S.now, S.lo), S.hi));
const atHi = rx1 - xn < 40, atLo = xn - rx0 < 40;
type(svg, rx0, RY + 15, `low ${rp(S.lo)}${atLo ? " · today " + rp(S.now) : ""}`, "label", { fill: atLo ? TONE.hi : TONE.faint, size: 6.6 });
type(svg, rx1, RY + 15, `${atHi ? "today " + rp(S.now) + " · " : ""}high ${rp(S.hi)}`, "label", { fill: atHi ? TONE.hi : TONE.faint, size: 6.6, anchor: "end" });
if (!atHi || Math.abs(xn - xc) > 8) mk("circle", { cx: xn, cy: RY, r: 3.2, style: `fill:${TONE.ground};stroke:${TONE.hi};stroke-width:1.2px` }, svg);
if (!atHi && !atLo) mk("line", { x1: xn, y1: RY + 4, x2: xn, y2: RY + 19, class: "thin", style: `stroke:${TONE.edge}` }, svg);
if (!atHi && !atLo) type(svg, xn, RY + 27, `today ${rp(S.now)}`, "label", { fill: TONE.hi, size: 6.6, weight: 600, anchor: "middle" });
grain(0.05);
