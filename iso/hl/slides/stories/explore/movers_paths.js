// Top movers, direction 2: the week as a race. Every mover's path from last Friday's close (0%) through each
// session, all on one chart; gainers fan up in green, losers down in terracotta, each labelled with its logo at
// the finish. IHSG is the dashed line in the middle.
const D = DATA, C = D.c;
setAccent("buy");
const G = "#81a789", T = "#c07159", GI = "#b2d2b9", TI = "#dc8d74";
const pct = (r) => `${r >= 0 ? "+" : "−"}${Math.abs(r * 100).toFixed(1)}%`;

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "TOP MOVERS", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, D.company, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });
type(svg, M, y0 + 44, "How the week's", "hero", { size: 32, weight: 500 });
typeRun(svg, M, y0 + 78, [["biggest moves", 32, 500, GI], [" ran", 32, 500, TONE.hi]]);

const all = C.up.concat(C.down);
const series = (r) => [0].concat(r.path.map((p) => p.close / r.base - 1));
const vals = all.flatMap(series), lo = Math.min(...vals), hi = Math.max(...vals);
const B = { x0: M + 4, x1: W - M - 60, y0: y0 + 110, y1: SAFE.bottom - 50 };
const xs = (i) => B.x0 + (i / 5) * (B.x1 - B.x0), ys = scale(lo * 1.05, hi * 1.1, B.y1, B.y0);
// day guides
["Fri", "Mon", "Tue", "Wed", "Thu", "Fri"].forEach((d, i) => {
  mk("line", { x1: xs(i), y1: B.y0, x2: xs(i), y2: B.y1, class: "lo thin" }, svg);
  type(svg, xs(i), B.y1 + 12, i ? d.toUpperCase() : "START", "caps", { fill: TONE.faint, size: 5.2, anchor: "middle" });
});
mk("line", { x1: B.x0, y1: ys(0), x2: B.x1, y2: ys(0), style: `stroke:${TONE.edge};stroke-width:.8px` }, svg);
// IHSG
const ih = [0].concat(C.ihsg.path.map((p) => p.close / C.ihsg.base - 1));
mk("path", { d: smoothPath(ih.map((v, i) => [xs(i), ys(v)])), class: "nf", style: `stroke:${TONE.hi};stroke-width:1.2px;stroke-dasharray:3 3;opacity:.7` }, svg);
// movers
const ends = [];
// the best and the worst are the story: bold, with a soft fill and a glowing end; the rest fade back
const lead = new Set([C.up[0].sym, C.down[0].sym]);
const drawn = all.map((r) => {
  const s = series(r), up = r.ret >= 0, pts = s.map((v, i) => [xs(i), ys(v)]);
  ends.push({ r, y: pts[5][1], up, hot: lead.has(r.sym) });
  return { r, pts, up, hot: lead.has(r.sym) };
});
drawn.filter((d) => !d.hot).forEach((d) =>
  mk("path", { d: smoothPath(d.pts), class: "nf", style: `stroke:${d.up ? G : T};stroke-width:1.2px;opacity:.22` }, svg));
drawn.filter((d) => d.hot).forEach((d) => {
  // the shaded area reads heavier on a light page, so it is lighter there
  areaLine(svg, d.pts, ys(0), { color: d.up ? G : T, width: 2.8, fill: DATA.theme === "light" ? 0.06 : 0.16 });
  glowDot(svg, ...d.pts[5], d.up ? G : T, 3.4);
});
// end labels, spread so they never overlap
ends.sort((a, b) => a.y - b.y);
for (let i = 1; i < ends.length; i++) if (ends[i].y - ends[i - 1].y < 21) ends[i].y = ends[i - 1].y + 21;
const shift = Math.max(0, ends.at(-1).y - (B.y1 + 4));
ends.forEach((e) => {
  const ly = e.y - shift, x = B.x1 + 8;
  // every label looks the same: only the lines carry the highlight
  logoChip(svg, x + 8, ly, 8, e.r.logo, e.r.sym);
  type(svg, x + 20, ly - 1, e.r.sym, "label", { fill: TONE.hi, size: 7.6, weight: 700 });
  type(svg, x + 20, ly + 8, pct(e.r.ret), "label", { fill: e.up ? GI : TI, size: 7, weight: 650 });
});
type(svg, B.x0 + 4, ys(ih.at(-1)) - 5, `IHSG ${pct(C.ihsg.ret)}`, "label", { fill: TONE.hi, size: 7, weight: 600 });

type(svg, M, SAFE.bottom - 4, `${C.breadth.up} rose, ${C.breadth.down} fell of the 100 largest stocks`, "label", { fill: TONE.hi, size: 9, weight: 600 });
type(svg, W - M, SAFE.bottom - 4, "sectors.app", "label", { fill: TONE.muted, size: 7.4, anchor: "end", weight: 650 });
grain(0.09);
