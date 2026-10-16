// Top movers, direction 3: one bold diverging chart. Thick horizontal bars from a centre line, gainers growing
// right in green, losers left in terracotta, true to scale; the logo sits at the bar's root, the move at its tip.
const D = DATA, C = D.c;
setAccent("buy");
const G = "#81a789", T = "#c07159", GI = "#b2d2b9", TI = "#dc8d74";
const pct = (r) => `${r >= 0 ? "+" : "−"}${Math.abs(r * 100).toFixed(1)}%`;

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "TOP MOVERS", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, D.company, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });
type(svg, M, y0 + 44, "Up and down", "hero", { size: 34, weight: 500 });
type(svg, M, y0 + 64, `The 100 largest IDX stocks · IHSG ${pct(C.ihsg.ret)} this week`, "label", { fill: TONE.muted, size: 9 });

const rows = C.up.concat(C.down.slice().reverse()), cx = W / 2;
const max = Math.max(...rows.map((r) => Math.abs(r.ret))), half = W / 2 - M - 4;
const TOP = y0 + 92, RH = (SAFE.bottom - 40 - TOP) / rows.length;
mk("line", { x1: cx, y1: TOP - 6, x2: cx, y2: TOP + rows.length * RH, style: `stroke:${TONE.edge};stroke-width:1px` }, svg);
rows.forEach((r, i) => {
  const up = r.ret >= 0, cy = TOP + i * RH + RH / 2, len = half * Math.abs(r.ret) / max, bh = Math.min(22, RH * 0.62);
  const x = up ? cx : cx - len;
  mk("rect", { x, y: cy - bh / 2, width: len, height: bh, rx: 3, style: `fill:${up ? G : T};fill-opacity:${0.35 + 0.6 * Math.abs(r.ret) / max};stroke:none` }, svg);
  // logo + ticker on the other side of the centre line
  const lx = up ? cx - 14 : cx + 14;
  logoChip(svg, lx, cy, 10, r.logo, r.sym);
  type(svg, up ? lx - 15 : lx + 15, cy + 3.5, r.sym, "label", { fill: TONE.hi, size: 9.5, weight: 700, anchor: up ? "end" : "start" });
  // the move at the bar's tip, inside if the bar is long, else outside
  const inside = len > 60, tx = up ? (inside ? cx + len - 6 : cx + len + 5) : (inside ? cx - len + 6 : cx - len - 5);
  type(svg, tx, cy + 4, pct(r.ret), "label", { fill: inside ? TONE.ground : up ? GI : TI, size: 10, weight: 750,
    anchor: up ? (inside ? "end" : "start") : (inside ? "start" : "end") });
  if (i === C.up.length - 1) mk("line", { x1: M, y1: cy + RH / 2, x2: W - M, y2: cy + RH / 2, class: "lo thin", "stroke-dasharray": "2 3" }, svg);
});

type(svg, M, SAFE.bottom - 4, `${C.breadth.up} rose, ${C.breadth.down} fell`, "label", { fill: TONE.hi, size: 9, weight: 600 });
type(svg, W - M, SAFE.bottom - 4, "sectors.app", "label", { fill: TONE.muted, size: 7.4, anchor: "end", weight: 650 });
grain(0.09);
