// Weekly calendar, slide 2: the dividends you can still buy into, ranked by yield. Each row: logo and ticker,
// Rp a share, the last day to buy (cum date) and the pay date; the yield large at the right with a true-scale bar.
// DATA.slide: { title, rows: [{ sym, logo, amount, yield, cum, pay }] }
const D = DATA, S = D.slide;
setAccent(D.direction);
dotField(0, 0, W, H, { fx: W * 0.85, fy: 60, reach: 280, op: 0.38 });
watermark(W + 4, 120, "%", 150, { anchor: "end", op: 0.06 });
glow(W - M - 30, 112 + 22, 120, 50, 0.14);
frame(D);

para(svg, M, 74, S.title, "title");
type(svg, M, 92, "Ranked by yield at the last close. Buy by the cum date to get it.", "body", { fill: TONE.muted, size: 8 });

const rows = S.rows, TOP = 112, RH = Math.min(48, (H - 50 - TOP) / rows.length);
const maxY = Math.max(...rows.map((r) => r.yield ?? 0)) || 1;
const amt = (v) => `Rp ${v >= 100 ? Math.round(v).toLocaleString("en-US") : String(+v.toFixed(2))}`;
rows.forEach((r, i) => {
  const y = TOP + i * RH, g = mk("g", {}, svg), lead = i === 0;
  mk("line", { x1: M, y1: y, x2: W - M, y2: y, class: "lo thin" }, g);
  const by = y + RH / 2 + 1;
  tickerChip(g, M, by - 3, r.sym, r.logo, { size: 11, fill: TONE.hi });
  type(g, M + 22, by + 10, `${amt(r.amount)} a share`, "label", { fill: TONE.muted, size: 7.2 });
  // dates in the middle
  type(g, 160, by - 5, "BUY BY", "caps", { fill: TONE.faint, size: 5 });
  type(g, 160, by + 7, r.cum, "label", { fill: TONE.hi, size: 9, weight: 650 });
  type(g, 208, by - 5, "PAID", "caps", { fill: TONE.faint, size: 5 });
  type(g, 208, by + 7, r.pay, "label", { fill: TONE.muted, size: 9 });
  // the yield, large, with its bar under it
  if (r.yield != null) {
    typeRun(g, W - M, by + 5, [[r.yield.toFixed(1), lead ? 22 : 18, 280, lead ? "var(--acc)" : TONE.hi], ["%", 9, 300, TONE.muted]], { anchor: "end" });
    const bw = 64 * (r.yield / maxY);
    mk("line", { x1: W - M - 64, y1: by + 12, x2: W - M, y2: by + 12, class: "lo thin" }, g);
    mk("line", { x1: W - M - bw, y1: by + 12, x2: W - M, y2: by + 12, style: `stroke:${lead ? "var(--acc)" : TONE.edge};stroke-width:2px` }, g);
  }
});
mk("line", { x1: M, y1: TOP + rows.length * RH, x2: W - M, y2: TOP + rows.length * RH, class: "lo thin" }, svg);
grain();
