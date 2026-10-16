// Earnings (data-led), slide 2: the profit bridge. A horizontal waterfall from the year-ago quarter's profit
// to this quarter's, one line of the income statement per row. Each step is green when it added to profit and
// red when it took from it; the biggest mover is named under the chart.
// DATA.slide: { title, sub, start: {label, v, s}, end: {…}, steps: [{label, v, s}], driver, note }
const D = DATA, S = D.slide, up = D.direction === "buy";
setAccent(D.direction);
const INK = up ? "#b2d2b9" : "#dc8d74";
frame(D);
const ty = para(svg, M, 74, S.title, "title");
type(svg, M, ty + 18, S.sub, "body", { fill: TONE.muted, size: 8.5 });

const rows = [{ ...S.start, kind: "start" }, ...S.steps.map((s) => ({ ...s, kind: "step" })), { ...S.end, kind: "end" }];
// running totals
let acc = 0;
for (const r of rows) {
  if (r.kind === "step") { r.a = acc; r.b = acc + r.v; acc = r.b; } else { r.a = 0; r.b = r.v; acc = r.v; }
}
// every step is coloured by what it did to profit, whatever the story: green added, red took away
const ADD = "#81a789", ADD_INK = "#b2d2b9", CUT = "#c07159", CUT_INK = "#dc8d74";
const LX = M, BX0 = 128, BX1 = W - M - 4;
const lo = Math.min(0, ...rows.map((r) => Math.min(r.a, r.b))), hi = Math.max(...rows.map((r) => Math.max(r.a, r.b)));
const xs = scale(lo, hi, BX0, BX1), z = xs(0);
const top = ty + 44, bottom = 372, rh = (bottom - top) / rows.length, bh = Math.min(15, rh * 0.56);
const g = mk("g", {}, svg);
mk("line", { x1: z, y1: top - 6, x2: z, y2: bottom, style: `stroke:${TONE.mid};stroke-width:.8px` }, g);
rows.forEach((r, i) => {
  const cy = top + i * rh + rh / 2, x0 = xs(Math.min(r.a, r.b)), x1 = xs(Math.max(r.a, r.b)), w = Math.max(1.5, x1 - x0);
  const isDriver = r.kind === "step" && r.label === S.driver, add = r.v >= 0;
  let style;
  if (r.kind === "start") style = `fill:${TONE.edge};stroke:none`;
  else if (r.kind === "end") style = `fill:var(--acc);stroke:none`;
  else style = `fill:${add ? ADD : CUT};fill-opacity:${isDriver ? 1 : 0.75};stroke:none`;
  mk("rect", { x: x0, y: cy - bh / 2, width: w, height: bh, rx: 2, style }, g);
  // connector: from where this row ends straight down to where the next one starts
  if (i < rows.length - 1) {
    const xe = xs(r.b), ny = top + (i + 1) * rh + rh / 2 - bh / 2;
    mk("line", { x1: xe, y1: cy + bh / 2, x2: xe, y2: ny, style: `stroke:${TONE.faint};stroke-width:.7px` }, g);
  }
  // the label at the left
  const bold = r.kind !== "step" || isDriver;
  type(g, LX, cy + 3, r.kind === "step" ? r.label : r.label.replace("-", " "), "label",
    { fill: bold ? TONE.hi : TONE.muted, size: r.kind === "step" ? 8.2 : 8.6, weight: bold ? 700 : 500 });
  // the value: right of the bar if there is room, else left of it; coloured like its bar
  const txt = r.s.replace("Rp ", ""), tw = txt.length * 4.6 + 6;
  const right = x1 + 5 + tw < W - M + 2;
  const fill = r.kind === "end" ? INK : r.kind === "start" ? TONE.hi : add ? ADD_INK : CUT_INK;
  type(g, right ? x1 + 5 : x0 - 5, cy + 3, txt, "label",
    { fill, size: 8.2, weight: r.kind === "step" && !isDriver ? 600 : 750, anchor: right ? "start" : "end" });
});
para(svg, M, 398, S.note, "body", { maxW: W - 2 * M, fill: TONE.hi });
grain(0.07);
