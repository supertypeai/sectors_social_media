// Ranked: who did it, by value. Editorial rows: rank, name, a light numeral, and a hairline bar true to
// scale (outline only; the top row's in the accent).
// DATA.slide: { title, accent[], sub, rows: [{ name, value, display, note }] } biggest first.
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

let y = para(svg, M, 74, S.title, "title", { accent: S.accent, size: 24 });
type(svg, M, y + 16, S.sub, "body", { fill: TONE.muted });

const rows = S.rows.slice(0, 5), TOP = y + 44, RH = (H - 52 - TOP) / rows.length;
const max = Math.max(...rows.map((r) => r.value)), BAR0 = M, BARW = W - 2 * M;
rows.forEach((r, i) => {
  // the highlighted row is the one the post is about (`hi`), else the biggest
  const top = TOP + i * RH, g = mk("g", {}, svg), lead = rows.some((x) => x.hi) ? !!r.hi : i === 0;
  mk("line", { x1: M, y1: top, x2: W - M, y2: top, class: "lo thin" }, g);
  type(g, M, top + 15, String(i + 1).padStart(2, "0"), "caps", { fill: TONE.faint });
  type(g, M + 18, top + 15, r.name, "label", { fill: lead ? TONE.hi : TONE.muted, weight: lead ? 650 : 500, size: 8.6 });
  if (r.note) type(g, W - M, top + 15, r.note, "label", { fill: TONE.faint, size: 7, anchor: "end" });
  type(g, M - 1.5, top + 39, r.display, "num", { fill: lead ? "var(--acc)" : TONE.hi, size: lead ? 26 : 22, weight: lead ? 300 : 260 });
  // the bar, under the numeral: a rounded hairline outline, true to scale; tiny values keep a 3-unit tick
  const len = Math.max(3, (r.value / max) * BARW), by = top + RH - 9;
  mk("path", { d: `M${BAR0 + 2} ${by}H${BAR0 + len - 2}a2 2 0 0 1 0 4H${BAR0 + 2}a2 2 0 0 1 0 -4Z`, class: lead ? "acc nf" : "sil nf" }, g);
  if (lead) mk("path", { d: `M${BAR0 + 2} ${by + 2}H${BAR0 + len - 2}`, class: "acc nf thin", "stroke-dasharray": "1 3" }, g);
});
