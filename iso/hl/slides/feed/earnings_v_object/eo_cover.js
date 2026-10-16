// Earnings (object direction), slide 1: the multiple huge, then last year's profit and this year's as two
// piles of hairline coins. One coin is a fixed rupiah amount, so the count of coins is the chart.
// DATA.slide: { sym, name, logo, up, hero, line, unit, prev: {label, n, s}, now: {label, n, s} }
const D = DATA, S = D.slide;
setAccent(D.direction);
const up = S.up, INK = up ? "#b2d2b9" : "#dc8d74";
dotField(0, 0, W, H, { fx: W * 0.6, fy: 330, reach: 260, op: 0.26 });
frame(D);

/** One iso coin: bottom face centre (cx, by), radius r, thickness t. */
function coin(g, cx, by, r, t, { stroke = TONE.edge, top = TONE.ground, rim = true } = {}) {
  const ry = r * 0.5, ty = by - t;
  mk("path", { d: `M${cx - r} ${ty}L${cx - r} ${by}A${r} ${ry} 0 0 0 ${cx + r} ${by}L${cx + r} ${ty}Z`, style: `fill:${TONE.ground};stroke:${stroke};stroke-width:1px` }, g);
  mk("ellipse", { cx, cy: ty, rx: r, ry, style: `fill:${top};stroke:${stroke};stroke-width:1px` }, g);
  if (rim) mk("ellipse", { cx, cy: ty, rx: r * 0.7, ry: ry * 0.7, style: `fill:none;stroke:${stroke};stroke-width:.6px;opacity:.55` }, g);
}
/** The slots of a pile, back to front: a centre stack, then stacks around it. */
const SLOTS = [[0, -16], [-34, -4], [34, -4], [-17, 12], [17, 12], [-52, 14], [52, 14]];
function pileStacks(n, cap) {
  const k = Math.min(SLOTS.length, Math.ceil(n / cap)), hs = Array(k).fill(0);
  for (let i = 0; i < n; i++) hs[i % k]++; // even-ish stacks
  hs.sort((a, b) => b - a);
  return hs.map((h, i) => ({ h, dx: SLOTS[i][0], dy: SLOTS[i][1] })).sort((a, b) => a.dy - b.dy || a.dx - b.dx);
}
const R = 20, T = 6, CAP = 7;
function pile(g, cx, base, n, opts) {
  const st = pileStacks(n, CAP);
  for (const s of st) for (let i = 0; i < s.h; i++) coin(g, cx + s.dx, base + s.dy - i * T, R, T, opts);
  return base - 13 - Math.max(...st.map((s) => s.h)) * T - R * 0.5; // top of the pile, screen y
}
/** Dashed cylinders where coins used to be: what is gone. */
function ghostPile(g, cx, base, n) {
  for (const s of pileStacks(n, CAP)) {
    const x = cx + s.dx, by = base + s.dy, ty = by - s.h * T, ry = R * 0.5;
    mk("path", { d: `M${x - R} ${ty}L${x - R} ${by}A${R} ${ry} 0 0 0 ${x + R} ${by}L${x + R} ${ty}`, class: "nf", style: `stroke:${TONE.mid};stroke-width:.9px;stroke-dasharray:2 3` }, g);
    mk("ellipse", { cx: x, cy: ty, rx: R, ry, class: "nf", style: `stroke:${TONE.mid};stroke-width:.9px;stroke-dasharray:2 3` }, g);
  }
}

// the company
logoChip(svg, M + 15, 66, 15, S.logo, S.sym);
type(svg, M + 37, 70, S.sym, "label", { fill: TONE.hi, size: 14, weight: 800 });
type(svg, M + 37, 80, S.name, "label", { fill: TONE.muted, size: 7.4 });

// the hook
type(svg, M - 4, 158, S.hero, "hero", { size: S.hero.length > 5 ? 76 : 90, weight: 600, fill: INK });
type(svg, M, 182, S.line, "title", { size: 16, fill: TONE.hi });
type(svg, M, 197, `${S.now.label} vs ${S.prev.label}`, "label", { fill: TONE.muted, size: 8.5 });

// the two piles
const base = 338, xl = 104, xr = 256;
glow(xr, base - 30, 120, 70, up ? 0.14 : 0.08);
const g = mk("g", {}, svg);
mk("line", { x1: M, y1: base + 22, x2: W - M, y2: base + 22, class: "lo thin" }, g);
const tl = pile(g, xl, base, S.prev.n, { stroke: TONE.edge });
let tr;
if (up) tr = pile(g, xr, base, S.now.n, { stroke: "var(--acc)", top: "rgba(129,167,137,.10)" });
else {
  ghostPile(g, xr, base, S.prev.n);
  tr = pile(g, xr, base, S.now.n, { stroke: "var(--acc)", top: "rgba(192,113,89,.12)" });
  tr = Math.min(tr, tl);
}
type(g, xl, tl - 8, S.prev.s, "num", { size: 14, weight: 500, fill: TONE.hi, anchor: "middle" });
type(g, xr, (up ? tr : tl) - 8, S.now.s, "num", { size: 18, weight: 650, fill: INK, anchor: "middle" });
type(g, xl, base + 36, S.prev.label.toUpperCase(), "caps", { fill: TONE.muted, size: 6.6, weight: 750, anchor: "middle" });
type(g, xr, base + 36, S.now.label.toUpperCase(), "caps", { fill: INK, size: 6.6, weight: 750, anchor: "middle" });
if (!up) type(g, xr, base + 47, "dashed = gone", "label", { fill: TONE.faint, size: 6.4, anchor: "middle" });

// the key: what one coin is worth
const kx = W / 2;
coin(svg, kx - 30, 404, 5, 2, { stroke: TONE.muted, rim: false });
type(svg, kx - 21, 404, `1 coin = ${S.unit} profit`, "label", { fill: TONE.muted, size: 7 });
grain(0.08);
