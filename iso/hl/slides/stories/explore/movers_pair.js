// Top movers, direction 4: the two extremes. The week's best and worst stock as two big panels, each with the
// move huge and its week as a sparkline; the next four on each side as a quiet line of logos.
const D = DATA, C = D.c;
setAccent("buy");
const G = "#81a789", T = "#c07159", GI = "#b2d2b9", TI = "#dc8d74";
const pct = (r) => `${r >= 0 ? "+" : "−"}${Math.abs(r * 100).toFixed(1)}%`;

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "TOP MOVERS", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, D.company, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });

function panel(r, rest, top, fill, ink, label) {
  const h = 214;
  mk("rect", { x: M - 8, y: top, width: W - 2 * M + 16, height: h, rx: 14, style: `fill:${fill};fill-opacity:.1;stroke:${fill};stroke-opacity:.5;stroke-width:1px` }, svg);
  type(svg, M + 6, top + 22, label, "caps", { fill: ink, size: 6, weight: 750 });
  logoChip(svg, M + 22, top + 50, 16, r.logo, r.sym);
  type(svg, M + 46, top + 50, r.sym, "label", { fill: TONE.hi, size: 18, weight: 700 });
  type(svg, M + 46, top + 62, r.name, "label", { fill: TONE.muted, size: 8 });
  type(svg, M + 2, top + 122, pct(r.ret), "num", { size: 58, weight: 500, fill: ink });
  type(svg, M + 6, top + 138, `Rp ${Math.round(r.base).toLocaleString("en-US")} → Rp ${Math.round(r.last).toLocaleString("en-US")}`, "label", { fill: TONE.muted, size: 8 });
  // sparkline of the week, right side
  const s = [r.base].concat(r.path.map((p) => p.close)), lo = Math.min(...s), hi = Math.max(...s);
  const bx0 = W - M - 110, bx1 = W - M - 8, by0 = top + 80, by1 = top + 140;
  const pts = s.map((v, i) => [bx0 + (i / 5) * (bx1 - bx0), scale(lo, hi, by1, by0)(v)]);
  areaLine(svg, pts, by1, { color: fill, width: 2, fill: 0.22 });
  glowDot(svg, ...pts.at(-1), fill, 3);
  // the next four
  let x = M + 6;
  rest.forEach((q) => {
    logoChip(svg, x + 9, top + h - 26, 9, q.logo, q.sym);
    type(svg, x + 22, top + h - 28, q.sym, "label", { fill: TONE.hi, size: 8, weight: 700 });
    type(svg, x + 22, top + h - 18, pct(q.ret), "label", { fill: ink, size: 7.4, weight: 650 });
    x += 76;
  });
}
panel(C.up[0], C.up.slice(1, 5), y0 + 20, G, GI, "BEST OF THE WEEK");
panel(C.down[0], C.down.slice(1, 5), y0 + 250, T, TI, "WORST OF THE WEEK");

type(svg, M, SAFE.bottom - 4, `IHSG ${pct(C.ihsg.ret)} · ${C.breadth.up} rose, ${C.breadth.down} fell`, "label", { fill: TONE.hi, size: 9, weight: 600 });
type(svg, W - M, SAFE.bottom - 4, "sectors.app", "label", { fill: TONE.muted, size: 7.4, anchor: "end", weight: 650 });
grain(0.09);
