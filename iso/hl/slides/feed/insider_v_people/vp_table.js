// Insider "people", last slide: who sits at the table, before and after. Two 100% cap-table bars, the same
// holders in the same order on both, the mover in the accent; then the list and a question to the reader.
// DATA.slide: { sym, rows[{name, before, after, role}], sell, paired, question, cta }
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

para(svg, M, 74, `Who holds ${S.sym} now`, "title", { accent: [S.sym] });
type(svg, M, 90, S.sell && !S.paired
  ? "Holders with 1% or more. No buyer has filed yet, so the sold stake sits in everyone else."
  : "Before and after the deal. Holders with 1% or more.", "body", { fill: TONE.muted, size: S.sell && !S.paired ? 8.2 : undefined });

const rows = S.rows;
const greys = [0.42, 0.28, 0.18, 0.11];
let gi = 0;
for (const r of rows) r.style = r.role === "mover" ? "fill:var(--acc);stroke:none"
  : `fill:${TONE.hi};fill-opacity:${greys[gi++] ?? 0.08};stroke:none`;

const X0 = M + 42, X1 = W - M, BH = 26;
const bar = (y, key, label) => {
  type(svg, M, y + BH / 2 + 3, label, "caps", { size: 6, fill: TONE.muted });
  mk("rect", { x: X0, y, width: X1 - X0, height: BH, rx: 3, style: `fill:none;stroke:${TONE.mid};stroke-width:.8px;stroke-dasharray:2 2` }, svg);
  let x = X0;
  for (const r of rows) {
    const w = ((X1 - X0) * r[key]) / 100;
    if (w < 0.3) continue;
    mk("rect", { x: x + 0.4, y: y + 0.4, width: Math.max(0, w - 0.8), height: BH - 0.8, rx: 2, style: r.style }, svg);
    if (r.role === "mover" && w > 26) type(svg, x + w / 2, y + BH / 2 + 3.5, `${r[key].toFixed(r[key] >= 10 ? 0 : 1)}%`, "label", { size: 9, weight: 700, anchor: "middle", fill: TONE.ground });
    x += w;
  }
  const rest = 100 - rows.reduce((s, r) => s + r[key], 0);
  if (rest > 3) type(svg, X1 - 4, y + BH / 2 + 3, "everyone else", "label", { size: 6.4, anchor: "end", fill: TONE.faint });
};
bar(112, "before", "Before");
bar(150, "after", "After");

// ---------------------------------------------------------------- the list
let y = 208;
type(svg, M, y, "HOLDER", "caps", { size: 5.6, fill: TONE.faint });
type(svg, W - M - 58, y, "BEFORE", "caps", { size: 5.6, fill: TONE.faint, anchor: "end" });
type(svg, W - M, y, "AFTER", "caps", { size: 5.6, fill: TONE.faint, anchor: "end" });
y += 6;
mk("line", { x1: M, y1: y, x2: W - M, y2: y, class: "lo thin" }, svg);
y += 15;
for (const r of rows) {
  mk("rect", { x: M, y: y - 7, width: 7, height: 7, rx: 1.5, style: r.style }, svg);
  const nm = r.name.length > 32 ? r.name.slice(0, 31) + "…" : r.name;
  type(svg, M + 13, y, nm, "label", { size: 8.2, weight: r.role === "mover" ? 650 : 500, fill: r.role === "other" ? TONE.muted : TONE.hi });
  const changed = Math.abs(r.after - r.before) >= 0.01;
  type(svg, W - M - 58, y, `${r.before.toFixed(2)}%`, "label", { size: 8, anchor: "end", fill: changed ? TONE.muted : TONE.faint });
  type(svg, W - M, y, `${r.after.toFixed(2)}%`, "label", { size: 8.4, weight: 650, anchor: "end", fill: r.role === "mover" ? "var(--acc)" : TONE.hi });
  y += 16;
}

// ---------------------------------------------------------------- the question
{
  const qs = 17, ql = wrapText(S.question, qs, W - 2 * M, 0.47);
  let qy = 398 - 20 - (ql.length - 1) * qs * 1.15; // the question sits on the footer, the CTA under it
  mk("line", { x1: M, y1: qy - 24, x2: W - M, y2: qy - 24, class: "lo thin" }, svg);
  for (const l of ql) { type(svg, M, qy, l, "title", { size: qs, weight: 520 }); qy += qs * 1.15; }
  type(svg, M, qy + 2, S.cta, "label", { size: 7.6, fill: "var(--acc)", weight: 600 });
}
