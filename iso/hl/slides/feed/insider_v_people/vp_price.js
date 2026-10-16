// Insider "people", slide 4: the deal price against the market, before and since. A dashed level at the deal
// price, the stock's line through it, and today's close against that level. Answers "where is it now?"
// DATA.slide: { prices[{date, close}], moveDate, dealPrice, sell, sym, last, lastDay, close? }
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

const num = (v) => Math.round(v).toLocaleString("en-US");
const vs = (S.last / S.dealPrice - 1) * 100;
para(svg, M, 74, `${S.sell ? "Sold" : "Bought"} at Rp ${num(S.dealPrice)}. Now Rp ${num(S.last)}.`, "title", { accent: [num(S.dealPrice)] });

const B = { x0: M, x1: W - M - 6, y0: 128, y1: 330 };
const px = S.prices.map((p) => [dayOf(p.date), p.close]);
const t0 = px[0][0], t1 = px.at(-1)[0];
const vals = px.map((p) => p[1]).concat([S.dealPrice]);
const lo = Math.min(...vals), hi = Math.max(...vals), pad = (hi - lo) * 0.12 || hi * 0.1;
const xs = scale(t0, t1, B.x0, B.x1), ys = scale(lo - pad, hi + pad, B.y1, B.y0);
const g = mk("g", {}, svg);
for (const v of niceTicks(lo - pad, hi + pad, 3)) {
  const y = ys(v);
  if (Math.abs(y - ys(S.dealPrice)) < 16) continue; // the deal level carries its own label there
  mk("line", { x1: B.x0, y1: y, x2: B.x1, y2: y, class: "lo thin" }, g);
  type(g, B.x0, y - 3, `Rp ${num(v)}`, "label", { fill: TONE.faint, size: 6.4 });
}
const xm = xs(dayOf(S.moveDate));
// before the deal: quiet; after: bright
const pts = px.map(([t, v]) => [xs(t), ys(v)]);
const pre = pts.filter((p) => p[0] <= xm), post = pts.filter((p) => p[0] >= xm);
if (pre.length > 1) mk("path", { d: smoothPath(pre), class: "nf", style: `stroke:${TONE.edge};stroke-width:1.3px` }, g);
if (post.length > 1) areaLine(g, post, B.y1, { color: TONE.hi, width: 1.9, fill: post.length > 15 ? 0.1 : 0 });
// the deal level
const dy = ys(S.dealPrice);
mk("line", { x1: B.x0, y1: dy, x2: B.x1, y2: dy, style: "stroke:var(--acc);stroke-dasharray:3 3;stroke-width:1.3px" }, g);
type(g, B.x1, dy + (dy > B.y1 - 20 ? -5 : 11), `deal price Rp ${num(S.dealPrice)}`, "label", { fill: "var(--acc)", size: 7.4, weight: 650, anchor: "end" });
// the deal day
mk("line", { x1: xm, y1: B.y0 - 6, x2: xm, y2: B.y1, style: `stroke:${TONE.edge};stroke-width:.8px;stroke-dasharray:1.5 2.5` }, g);
type(g, xm + (xm > W / 2 ? -4 : 4), B.y0 - 9, `deal · ${fmtDay(dayOf(S.moveDate))}`, "label", { size: 6.8, fill: TONE.muted, anchor: xm > W / 2 ? "end" : "start" });
glowDot(g, xm, dy, "var(--acc)", 3);
const lp = pts.at(-1);
glowDot(g, lp[0], lp[1], TONE.hi, 3);
xMonthsB();
function xMonthsB() {
  const d = new Date(t0); d.setUTCDate(1); d.setUTCMonth(d.getUTCMonth() + 1);
  for (; d.getTime() <= t1; d.setUTCMonth(d.getUTCMonth() + 1)) {
    const x = xs(d.getTime());
    type(g, x, B.y1 + 12, fmtMonth(d.getTime()), "label", { fill: TONE.faint, size: 6.4, anchor: "middle" });
  }
}

// ---------------------------------------------------------------- the read-out
let y = 372;
mk("line", { x1: M, y1: y - 18, x2: W - M, y2: y - 18, class: "lo thin" }, svg);
typeRun(svg, M, y + 8, [[`${vs >= 0 ? "+" : "−"}${Math.abs(vs).toFixed(Math.abs(vs) < 10 ? 1 : 0)}`, 34, 260, TONE.hi], ["%", 15, 300, TONE.muted]]);
const msg = S.sell
  ? (vs >= 0 ? `${S.sym} trades above the price the seller got.` : `${S.sym} trades below the price the seller got.`)
  : (vs >= 0 ? `${S.sym} trades above what the buyer paid.` : `${S.sym} trades below what the buyer paid.`);
type(svg, M + 100, y - 2, msg, "label", { size: 8.4, weight: 600 });
type(svg, M + 100, y + 10, `Close on ${S.lastDay} vs the deal price.`, "label", { size: 7.2, fill: TONE.muted });
