// Crossing 5%, direction 2: where they bought (the volume-spike E layout). Two numbers up top, then three months
// of the price with the buy day marked, their average price as a dashed level, and today's close.
const D = DATA, S = D.s;
setAccent("buy");
const INK = "#b2d2b9", FILL = "#81a789";
dotField(0, 0, W, H, { fx: W * 0.8, fy: 280, reach: 320, op: 0.3 });

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "NEW MAJOR SHAREHOLDER", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, S.day, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });
logoChip(svg, M + 20, y0 + 40, 20, S.logo, S.sym);
type(svg, M + 50, y0 + 45, S.sym, "hero", { size: 32, weight: 650 });
type(svg, M + 50, y0 + 59, S.name, "label", { fill: TONE.muted, size: 8.5 });

type(svg, M, y0 + 96, `${S.holder} now owns`, "label", { fill: TONE.hi, size: 10, weight: 600 });
typeRun(svg, M - 2, y0 + 150, [[S.now.toFixed(2), 54, 500, INK], ["%", 22, 400, INK]]);
type(svg, M, y0 + 168, `up from ${S.before.toFixed(2)}%`, "label", { fill: TONE.muted, size: 9 });
const spent = S.facts.find((f) => f.label === "spent");
if (spent) {
  type(svg, W - M, y0 + 150, spent.value, "num", { size: 26, weight: 450, fill: TONE.hi, anchor: "end" });
  type(svg, W - M, y0 + 168, "spent on the stake", "label", { fill: TONE.muted, size: 9, anchor: "end" });
}

// the price, three months
const P = D.prices, B = { x0: M, x1: W - M, y0: y0 + 200, y1: SAFE.bottom - 46 };
const vals = P.map((p) => p.close).concat(D.avg ? [D.avg] : []), lo = Math.min(...vals), hi = Math.max(...vals), pad = (hi - lo) * 0.18;
const t0 = dayOf(P[0].date), t1 = dayOf(P.at(-1).date), xs = scale(t0, t1, B.x0, B.x1), ys = scale(lo - pad, hi + pad, B.y1, B.y0);
const pts = P.map((p) => [xs(dayOf(p.date)), ys(p.close)]);
areaLine(svg, pts, B.y1, { color: TONE.hi, width: 1.8, fill: 0.08 });
mk("line", { x1: B.x0, y1: B.y1, x2: B.x1, y2: B.y1, class: "lo thin" }, svg);
if (D.avg) {
  const ay = ys(D.avg);
  mk("line", { x1: B.x0, y1: ay, x2: B.x1, y2: ay, style: `stroke:${FILL};stroke-width:1.2px;stroke-dasharray:3 3` }, svg);
  type(svg, B.x0, ay - 5, `their average price Rp ${Math.round(D.avg).toLocaleString("en-US")}`, "label", { fill: INK, size: 7.6, weight: 650 });
}
const bx = xs(dayOf(D.cross)), by = yAt(pts, bx);
mk("line", { x1: bx, y1: B.y0 - 4, x2: bx, y2: B.y1, style: `stroke:${FILL};stroke-width:.8px;stroke-dasharray:1.5 2.5` }, svg);
glowDot(svg, bx, by, FILL, 3.6);
type(svg, bx - 6, B.y0 + 6, `crossed 5% · ${S.day}`, "label", { fill: INK, size: 7.6, weight: 650, anchor: "end" });
const [ex, ey] = pts.at(-1);
mk("circle", { cx: ex, cy: ey, r: 2.6, style: `fill:${TONE.hi};stroke:${TONE.ground};stroke-width:1.2px` }, svg);
type(svg, ex, ey + 14, `Rp ${P.at(-1).close.toLocaleString("en-US")} now`, "label", { fill: TONE.hi, size: 7.6, weight: 650, anchor: "end" });

type(svg, M, SAFE.bottom - 4, "Owning 5% or more makes you a major shareholder", "label", { fill: TONE.hi, size: 8.6, weight: 600 });
grain(0.09);
