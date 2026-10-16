// Volume spike, direction E: what the price did. The month's price as a large line on top, the volume as bars
// underneath sharing the same days; today's bar and today's price point light up together.
const D = DATA, L = D.lead, up = D.dir === "buy";
setAccent(D.dir);
const INK = up ? "#b2d2b9" : "#dc8d74", FILL = up ? "#81a789" : "#c07159";
dotField(0, 0, W, H, { fx: W * 0.8, fy: 260, reach: 320, op: 0.3 });

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "VOLUME SPIKE", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, D.company, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });
logoChip(svg, M + 20, y0 + 42, 20, L.logo, L.sym);
type(svg, M + 50, y0 + 47, L.sym, "hero", { size: 34, weight: 650 });
type(svg, M + 50, y0 + 61, L.name, "label", { fill: TONE.muted, size: 8.5 });

// the size of the spike first (what traded, in shares and rupiah), then how unusual it was
const rpv = (v) => (v >= 1e12 ? `Rp ${(v / 1e12).toFixed(1)} T` : v >= 1e9 ? `Rp ${(v / 1e9).toFixed(1)} B` : `Rp ${Math.round(v / 1e6)} M`);
typeRun(svg, M, y0 + 124, [[rpv(+L.value), 44, 550, INK]]);
type(svg, M, y0 + 145, `traded in one day · ${L.volumeTxt} shares`, "label", { fill: TONE.hi, size: 9.5, weight: 600 });
const sy = y0 + 196, cw = (W - 2 * M) / 2;
mk("line", { x1: M, y1: sy - 30, x2: W - M, y2: sy - 30, class: "lo thin" }, svg);
typeRun(svg, M, sy, [[`${L.ratioTxt}×`, 22, 550, TONE.hi]]);
type(svg, M, sy + 16, `a normal day (${L.medianTxt} shares)`, "label", { fill: TONE.muted, size: 7.6 });
typeRun(svg, M + cw, sy, [[L.chgTxt, 22, 550, TONE.hi]]);
type(svg, M + cw, sy + 16, "price that day", "label", { fill: TONE.muted, size: 7.6 });

// price line (top) and volume bars (bottom) on the same days
const bars = L.bars, n = bars.length, X0 = M, X1 = W - M, bw = (X1 - X0) / n;
const xs = (i) => X0 + (i + 0.5) * bw;
const P = { y0: y0 + 252, y1: y0 + 362 }, V = { y0: y0 + 382, y1: SAFE.bottom - 40 };
const cs = bars.map((b) => b.c), lo = Math.min(...cs), hi = Math.max(...cs), pad = (hi - lo) * 0.15 || hi * 0.05;
const py = scale(lo - pad, hi + pad, P.y1, P.y0);
const pts = bars.map((b, i) => [xs(i), py(b.c)]);
areaLine(svg, pts, P.y1, { color: TONE.hi, width: 1.8, fill: 0.08 });
mk("path", { d: `M${pts[n - 2].join(" ")}L${pts[n - 1].join(" ")}`, class: "nf", style: `stroke:${INK};stroke-width:2.6px` }, svg);
glowDot(svg, ...pts[n - 1], FILL, 4);
type(svg, pts[n - 1][0] - 8, pts[n - 1][1] - 10, rp(cs[n - 1]), "label", { fill: INK, size: 9, weight: 650, anchor: "end" });
type(svg, X0, P.y0 - 6, "PRICE", "caps", { fill: TONE.faint, size: 5.6 });

const vmax = Math.max(...bars.map((b) => b.v)), vy = scale(0, vmax, V.y1, V.y0);
bars.forEach((b, i) => {
  const last = i === n - 1;
  mk("rect", { x: X0 + i * bw + 1, y: vy(b.v), width: bw - 2, height: V.y1 - vy(b.v), rx: 1, style: `fill:${last ? FILL : TONE.mid};stroke:none` }, svg);
});
mk("line", { x1: xs(n - 1), y1: pts[n - 1][1] + 6, x2: xs(n - 1), y2: vy(bars[n - 1].v) - 2, style: `stroke:${FILL};stroke-width:.8px;stroke-dasharray:1.5 2.5` }, svg);
type(svg, X0, V.y0 - 6, "VOLUME", "caps", { fill: TONE.faint, size: 5.6 });
mk("line", { x1: X0, y1: V.y1, x2: X1, y2: V.y1, class: "lo thin" }, svg);

type(svg, M, SAFE.bottom - 4, `Busiest in ${L.rareHead} · ${L.volumeTxt} shares`, "label", { fill: TONE.hi, size: 9, weight: 600 });
type(svg, W - M, SAFE.bottom - 4, "sectors.app", "label", { fill: TONE.muted, size: 7.4, anchor: "end", weight: 650 });
grain(0.09);
