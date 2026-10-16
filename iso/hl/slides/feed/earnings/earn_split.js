// Earnings, slide 3: sales vs profit, year on year. Two rows, each a pair of thick bars (last year grey, this
// year in the accent) on its own scale, with the growth big at the right; a one-line verdict under them.
// DATA.slide: { title, q_now, q_prev, rows: [{label, prev, now, ps, ns, g}], verdict }
const D = DATA, S = D.slide, up = D.direction === "buy";
setAccent(D.direction);
const FILL = up ? "#81a789" : "#c07159", INK = up ? "#b2d2b9" : "#dc8d74";
frame(D);
para(svg, M, 74, S.title, "title");
type(svg, M, 92, `${S.q_prev} → ${S.q_now}`, "body", { fill: TONE.muted, size: 8.5 });

const pct = (g) => `${g >= 0 ? "+" : "−"}${Math.abs(g * 100).toFixed(0)}%`;
let y = 136;
S.rows.forEach((r) => {
  const max = Math.max(r.prev, r.now), span = W - 2 * M - 90, gx = W - M;
  type(svg, M, y, r.label.toUpperCase(), "caps", { fill: TONE.muted, size: 6.4, weight: 750 });
  typeRun(svg, gx, y + 30, [[pct(r.g), 30, 600, r.g >= 0 ? (up ? INK : "#b2d2b9") : "#dc8d74"]], { anchor: "end" });
  const b1 = y + 14, b2 = y + 42, bh = 20;
  mk("rect", { x: M, y: b1, width: Math.max(3, span * (r.prev / max)), height: bh, rx: 3, style: `fill:${TONE.mid};stroke:none` }, svg);
  type(svg, M + 8, b1 + 13.5, `${S.q_prev} · ${r.ps}`, "label", { fill: TONE.hi, size: 8, weight: 600 });
  const wn = Math.max(3, span * (r.now / max)), inside = wn > 110;
  mk("rect", { x: M, y: b2, width: wn, height: bh, rx: 3, style: `fill:${FILL};stroke:none` }, svg);
  // the label sits inside a long bar, after a short one
  type(svg, inside ? M + 8 : M + wn + 6, b2 + 13.5, `${S.q_now} · ${r.ns}`, "label", { fill: inside ? TONE.ground : INK, size: 8, weight: 750 });
  y += 110;
});
mk("line", { x1: M, y1: y - 10, x2: W - M, y2: y - 10, class: "lo thin" }, svg);
para(svg, M, y + 18, S.verdict, "title", { size: 17, fill: TONE.hi });
grain(0.08);
