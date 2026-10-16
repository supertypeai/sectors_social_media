// Post #1, slide 2: the deal price against the market. The stock's price as a line on a scale from Rp 0,
// the deal price as a dashed level, and the gap between them on the deal day bracketed and shaded.
// DATA.slide: { prices: [{date, close}], moveDate, salePrice, close, day, verb, shares, value }
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

const gap = (S.salePrice / S.close - 1) * 100, below = gap < 0;
const num = (v) => Math.round(v).toLocaleString("en-US");
para(svg, M, 74, `${S.verb === "bought" ? "Bought" : "Sold"} at ${rp(S.salePrice)}. The market closed at ${rp(S.close)}.`, "title",
  { accent: [num(S.salePrice).replace(/,/g, "")], maxW: W - 2 * M });

// ---------------------------------------------------------------- the chart, from Rp 0
const B = { x0: M, x1: W - M - 70, y0: 150, y1: 352 };
const px = S.prices.map((p) => [dayOf(p.date), p.close]);
const t0 = px[0][0], t1 = px.at(-1)[0], top = Math.max(...px.map((p) => p[1]), S.close, S.salePrice) * 1.12;
const xs = scale(t0, t1, B.x0, B.x1), ys = scale(0, top, B.y1, B.y0);
const pts = px.map(([t, v]) => [xs(t), ys(v)]);
const g = mk("g", {}, svg);

mk("line", { x1: B.x0, y1: B.y1, x2: W - M, y2: B.y1, class: "lo thin" }, g);
type(g, B.x0, B.y1 + 11, "Rp 0", "label", { fill: TONE.faint, size: 6.4 });
areaLine(g, pts, B.y1, { color: TONE.hi, width: 1.7, fill: 0.1 });

// the deal price: one dashed level across the whole chart
const sy = ys(S.salePrice), xm = xs(Math.min(Math.max(dayOf(S.moveDate), t0), t1)), cy = yAt(pts, xm);
mk("line", { x1: B.x0, y1: sy, x2: W - M, y2: sy, style: "stroke:var(--acc);stroke-dasharray:3 3;stroke-width:1.3px" }, g);
type(g, B.x0, sy + 12, `${S.verb === "bought" ? "deal" : "sale"} price ${rp(S.salePrice)}`, "label", { fill: "var(--acc)", size: 7.6, weight: 650 });

// the gap on the deal day: shaded between the line and the deal level, with a bracket and the number
mk("rect", { x: xm - 7, y: Math.min(cy, sy), width: 14, height: Math.abs(sy - cy), style: "fill:var(--acc);fill-opacity:.16;stroke:none" }, g);
const bx = W - M - 58;
mk("path", { d: `M${xm + 9} ${cy}H${bx}M${xm + 9} ${sy}H${bx}`, class: "nf thin", style: "stroke:var(--acc);stroke-dasharray:1 2.5" }, g);
mk("path", { d: `M${bx} ${cy}h4V${sy}h-4`, class: "nf", style: "stroke:var(--acc);stroke-width:1.3px" }, g);
glowDot(g, xm, cy, TONE.hi, 3);
glowDot(g, xm, sy, "var(--acc)", 3.2);
const mid = (cy + sy) / 2;
typeRun(svg, bx + 8, mid + 10, [[`${below ? "−" : "+"}${Math.abs(gap).toFixed(0)}`, 30, 260, "var(--acc)"], ["%", 14, 300, TONE.muted]]);
type(svg, bx + 9, mid + 22, "vs the close", "label", { fill: TONE.muted, size: 6.6 });
// the close label sits above the line's highest point near the deal day, so it never sits on the line
const near = pts.filter((p) => Math.abs(p[0] - xm) < 70), peak = Math.min(...near.map((p) => p[1]), cy);
mk("path", { d: `M${xm} ${cy - 5}V${peak - 10}`, class: "nf thin", style: `stroke:${TONE.edge}` }, g);
type(g, xm - 4, peak - 14, `close ${rp(S.close)} · ${S.day}`, "label", { fill: TONE.hi, size: 7.4, weight: 600, anchor: "end" });

// the honest footnote
mk("line", { x1: M, y1: 382, x2: W - M, y2: 382, class: "lo thin" }, svg);
para(svg, M, 398, `${S.value} for ${S.shares}. Trades this far from the market price are usually negotiated deals, not sales on the open market.`, "body", { fill: TONE.muted, maxW: W - 2 * M, lh: 1.4 });
