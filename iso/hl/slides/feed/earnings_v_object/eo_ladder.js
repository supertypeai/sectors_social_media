// Earnings (object direction), slide 2: the numbers are the chart. Each quarter's profit is set at a type
// size true to its value, so the quarter that matters is literally the loudest.
// DATA.slide: { title, verdict, rows: [{label, v, s, hi, pair}] }
const D = DATA, S = D.slide;
setAccent(D.direction);
const INK = D.direction === "buy" ? "#b2d2b9" : "#dc8d74";
dotField(0, 0, W, H, { fx: W * 0.8, fy: 120, reach: 240, op: 0.22 });
frame(D);

type(svg, M, 74, S.title, "title", { fill: TONE.hi });
type(svg, M, 90, S.verdict, "body", { fill: INK, weight: 560 });

const rows = S.rows, vmax = Math.max(...rows.map((r) => Math.abs(r.v)));
const size = (v) => 10 + 46 * Math.max(0, v) / vmax;
// fit the ladder into the band: scale every row by the same factor if it overflows
const top = 118, bot = 382, gap = 9;
let need = rows.reduce((a, r) => a + size(r.v) * 0.74 + gap, 0);
const k = Math.min(1, (bot - top) / need);
let y = top;
const lx = M, nx = M + 62;
for (const r of rows) {
  const s = size(r.v) * k, cap = s * 0.74;
  y += cap;
  const fill = r.hi ? INK : r.pair ? TONE.hi : TONE.muted;
  type(svg, lx, y, r.label.toUpperCase(), "caps", { fill: r.hi ? INK : TONE.faint, size: 6.4, weight: 750 });
  type(svg, nx, y, r.s, "num", { size: s, weight: r.hi ? 620 : r.pair ? 450 : 300, fill });
  if (r.hi || r.pair) {
    type(svg, W - M, y, r.hi ? "this quarter" : "a year ago", "label", { fill: r.hi ? INK : TONE.muted, size: 7, anchor: "end" });
  }
  mk("line", { x1: lx, y1: y + gap / 2 + 0.5, x2: W - M, y2: y + gap / 2 + 0.5, class: "lo thin" }, svg);
  y += gap;
}
type(svg, M, 400, "Type size = profit. Bigger number, bigger quarter.", "label", { fill: TONE.faint, size: 6.6 });
grain(0.08);
