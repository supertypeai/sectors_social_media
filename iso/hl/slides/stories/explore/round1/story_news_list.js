// News story, frame 1 (9:16): today's headlines as one tight list. Each row: logo, ticker and category,
// a short headline, and the one key number at the right. All inside storyFrame's safe band.
// DATA.slide: { title, rows: [{sym, logo, cat, headline, value, label}] }
const D = DATA, S = D.slide;
setAccent(D.direction);
dotField(0, 0, W, H, { fx: W * 0.85, fy: 40, reach: 300, op: 0.22 });
glow(W * 0.85, 60, 220, 160, 0.08);
const { top, bottom } = storyFrame(D);

type(svg, M, top + 12, S.title, "title", { size: 22 });
mk("line", { x1: M, y1: top + 24, x2: M + 32, y2: top + 24, style: "stroke:var(--acc);stroke-width:2px" }, svg);

const rows = S.rows.slice(0, 5), y0 = top + 42, rh = Math.min(66, (bottom - y0) / rows.length);
rows.forEach((r, i) => {
  const y = y0 + i * rh;
  if (i) mk("line", { x1: M, y1: y, x2: W - M, y2: y, class: "lo thin" }, svg);
  logoChip(svg, M + 11, y + 19, 11, r.logo, r.sym);
  const t = type(svg, M + 30, y + 17, r.sym, "label", { fill: TONE.hi, size: 10, weight: 700 });
  type(svg, M + 30 + r.sym.length * 6.6 + 6, y + 16.6, r.cat, "caps", { fill: TONE.faint, size: 5.6 });
  const hw = r.value ? W - 2 * M - 30 - 96 : W - 2 * M - 30;
  wrapText(r.headline, 8.4, hw, 0.52).slice(0, 2).forEach((l, j) =>
    type(svg, M + 30, y + 31 + j * 11, l, "body", { fill: TONE.muted, size: 8.4 }));
  if (r.value) {
    type(svg, W - M, y + 24, r.value, "num", { size: r.value.length > 8 ? 16 : 19, weight: 400, fill: i === 0 ? "var(--acc)" : TONE.hi, anchor: "end" });
    if (r.label) type(svg, W - M, y + 36, r.label, "caps", { fill: TONE.faint, size: 5.2, anchor: "end" });
  }
});
grain();
