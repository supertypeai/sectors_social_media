// Crossing 5%, variant B: the volume-spike E layout for a stake. Two numbers up top (the new stake and what it
// cost), then one big step chart of the holder's stake over time with the 5% line; the step that crosses lights up.
const D = DATA, S = D.s;
setAccent("buy");
const INK = "#b2d2b9", FILL = "#81a789";
dotField(0, 0, W, H, { fx: W * 0.8, fy: 300, reach: 320, op: 0.3 });

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "NEW MAJOR SHAREHOLDER", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, S.day, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });
logoChip(svg, M + 20, y0 + 42, 20, S.logo, S.sym);
type(svg, M + 50, y0 + 47, S.sym, "hero", { size: 34, weight: 650 });
type(svg, M + 50, y0 + 61, S.holder, "label", { fill: TONE.muted, size: 8.5 });

// two numbers
typeRun(svg, M, y0 + 132, [[S.now.toFixed(2), 58, 500, INK], ["%", 24, 400, INK]]);
type(svg, M, y0 + 150, `stake now · from ${S.before.toFixed(2)}%`, "label", { fill: TONE.muted, size: 9 });
const sp = S.facts.find((f) => f.label === "spent");
if (sp) {
  type(svg, W - M, y0 + 132, sp.value, "num", { size: 22, weight: 450, fill: TONE.hi, anchor: "end" });
  type(svg, W - M, y0 + 150, "spent", "label", { fill: TONE.muted, size: 9, anchor: "end" });
}

// the stake as solid steps
const st = S.stake.map((p) => [dayOf(p.date), p.pct]);
const B = { x0: M, x1: W - M, y0: y0 + 190, y1: SAFE.bottom - 44 };
const xs = scale(st[0][0], st.at(-1)[0], B.x0, B.x1), ys = scale(0, Math.max(12, S.now * 1.2), B.y1, B.y0);
const pts = [];
st.forEach(([t, v], i) => { if (i) pts.push([xs(t), ys(st[i - 1][1])]); pts.push([xs(t), ys(v)]); });
mk("path", { d: `M${pts.map((p) => p.join(" ")).join("L")}L${B.x1} ${B.y1}L${B.x0} ${B.y1}Z`, style: `fill:${TONE.hi};fill-opacity:.07;stroke:none` }, svg);
mk("path", { d: `M${pts.map((p) => p.join(" ")).join("L")}`, class: "nf", style: `stroke:${TONE.hi};stroke-width:2px` }, svg);
// the crossing step in the accent, filled from the step to the floor
const k = st.findIndex(([, v], i) => i && st[i - 1][1] < 5 && v >= 5);
if (k > 0) {
  const x = xs(st[k][0]), x2 = xs(st.at(-1)[0]);
  mk("rect", { x, y: ys(st[k][1]), width: Math.max(4, x2 - x), height: B.y1 - ys(st[k][1]), style: `fill:${FILL};fill-opacity:.35;stroke:none` }, svg);
  mk("path", { d: `M${x} ${ys(st[k - 1][1])}V${ys(st[k][1])}H${x2}`, class: "nf", style: `stroke:${FILL};stroke-width:3px` }, svg);
  glowDot(svg, x, ys(st[k][1]), FILL, 4);
  type(svg, x - 6, ys(st[k][1]) - 8, `crossed 5% · ${S.day}`, "label", { fill: INK, size: 8, weight: 650, anchor: "end" });
}
const fy = ys(5);
mk("line", { x1: B.x0, y1: fy, x2: B.x1, y2: fy, style: `stroke:${TONE.hi};stroke-width:1px;stroke-dasharray:3 3;opacity:.8` }, svg);
type(svg, B.x0, fy - 5, "5% · major shareholder line", "label", { fill: TONE.hi, size: 7.6 });
mk("line", { x1: B.x0, y1: B.y1, x2: B.x1, y2: B.y1, class: "lo thin" }, svg);
type(svg, B.x0, B.y1 + 12, fmtDay(st[0][0]), "label", { fill: TONE.faint, size: 7 });
type(svg, B.x1, B.y1 + 12, "now", "label", { fill: TONE.faint, size: 7, anchor: "end" });

const F = S.facts.filter((f) => f.label !== "spent").map((f) => `${f.value} ${f.label}`).join("  ·  ");
type(svg, M, SAFE.bottom - 4, F, "label", { fill: TONE.hi, size: 9, weight: 600 });
grain(0.09);
