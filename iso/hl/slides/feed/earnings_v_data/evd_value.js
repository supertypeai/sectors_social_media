// Earnings (data-led), slide 5: what the quarter did to the price tag. P/E on the last four quarters' profit,
// at today's price, before this report and after it; then the same number placed on a ruler of every
// sub-sector peer's P/E, with an arrow showing which way the report moved it.
// DATA.slide: { title, sub, before, now, q_before, q_now, peers: [{sym, pe}], sym, logo, line, cta }
const D = DATA, S = D.slide, up = D.direction === "buy";
setAccent(D.direction);
const INK = up ? "#b2d2b9" : "#dc8d74";
frame(D);
para(svg, M, 74, S.title, "title", { maxW: W - 2 * M });
const fmt = (v) => (v >= 100 ? v.toFixed(0) : v.toFixed(1)) + "×";

// before → after, big
const yb = 158;
type(svg, M, yb, fmt(S.before), "num", { size: 40, weight: 300, fill: TONE.muted });
const bw = fmt(S.before).length * 21;
mk("path", { d: `M${M + bw + 6} ${yb - 13}h22m-5 -4.5l5 4.5l-5 4.5`, class: "nf", style: `stroke:${TONE.edge};stroke-width:1.2px` }, svg);
type(svg, M + bw + 40, yb, fmt(S.now), "num", { size: 52, weight: 450, fill: TONE.hi });
type(svg, M, yb + 18, `P/E before ${S.q_now} results`, "label", { fill: TONE.muted, size: 7 });
type(svg, M + bw + 40, yb + 18, `after`, "label", { fill: INK, size: 7, weight: 650 });
para(svg, M, 204, S.sub, "body", { maxW: W - 2 * M, fill: TONE.muted });

// the ruler of peers
const pes = S.peers.map((p) => p.pe), all = [...pes, S.before, S.now];
const hiV = Math.min(60, Math.max(...all) * 1.08), xs = scale(0, hiV, M + 4, W - M - 4), ry = 326;
const g = mk("g", {}, svg);
type(g, M, 250, S.line || "", "label", { fill: TONE.hi, size: 10, weight: 650 });
mk("line", { x1: M, y1: ry, x2: W - M, y2: ry, style: `stroke:${TONE.mid};stroke-width:.8px` }, g);
for (const t of niceTicks(0, hiV, 4)) {
  mk("line", { x1: xs(t), y1: ry, x2: xs(t), y2: ry + 4, style: `stroke:${TONE.mid};stroke-width:.8px` }, g);
  type(g, xs(t), ry + 14, `${t}×`, "label", { fill: TONE.faint, size: 6.6, anchor: "middle" });
}
// peers as ticks, a few named (cheapest and dearest), names staggered so they never touch
const named = new Set([S.peers[0]?.sym, S.peers.at(-1)?.sym]);
S.peers.forEach((p) => {
  const x = xs(Math.min(p.pe, hiV));
  mk("line", { x1: x, y1: ry - 9, x2: x, y2: ry, style: `stroke:${TONE.edge};stroke-width:1px` }, g);
  if (named.has(p.sym)) type(g, x, ry - 13, p.sym, "label", { fill: TONE.faint, size: 6.4, anchor: "middle" });
});
// the company: before (hollow) → now (lit)
const xb = xs(Math.min(S.before, hiV)), xn = xs(Math.min(S.now, hiV)), cy = ry - 30;
mk("path", { d: `M${xb} ${cy}L${xn + (xn < xb ? 5 : -5)} ${cy}`, class: "nf", style: `stroke:${INK};stroke-width:1px;stroke-dasharray:2 2` }, g);
mk("circle", { cx: xb, cy, r: 3, style: `fill:${TONE.ground};stroke:${TONE.edge};stroke-width:1px` }, g);
glowDot(g, xn, cy, "var(--acc)", 3.4);
mk("line", { x1: xn, y1: cy + 4, x2: xn, y2: ry, style: `stroke:${INK};stroke-width:.8px` }, g);
type(g, xn, cy - 10, S.sym, "label", { fill: INK, size: 8.4, weight: 750, anchor: "middle" });

// the close
mk("line", { x1: M, y1: 358, x2: W - M, y2: 358, class: "lo thin" }, svg);
para(svg, M, 376, "A lower P/E means you pay less for each Rp of profit. One quarter doesn't make a trend, so check the next report too.", "body", { maxW: W - 2 * M, fill: TONE.muted });
type(svg, M, 404, S.cta, "label", { fill: TONE.hi, size: 8, weight: 650 });
grain(0.07);
