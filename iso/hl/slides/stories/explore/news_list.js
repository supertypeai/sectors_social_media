// News compilation, direction 1: editorial list (the top-broker language). "Today on the IDX", then each story
// as a row: rank, logo, ticker and category, the headline in two lines, and its one number at the right.
const D = DATA, S = D.stories.slice(0, 5);
setAccent("buy");
const GI = "#b2d2b9", TI = "#dc8d74";

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "IDX NEWS", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, D.company, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });
type(svg, M, y0 + 46, "Today on", "hero", { size: 36, weight: 500 });
type(svg, M, y0 + 84, "the IDX", "hero", { size: 36, weight: 500, fill: GI });

const TOP = y0 + 110, RH = (SAFE.bottom - 30 - TOP) / S.length;
S.forEach((s, i) => {
  const y = TOP + i * RH, ink = s.bear ? TI : GI;
  type(svg, M, y + 26, String(i + 1), "num", { size: 22, weight: 300, fill: TONE.faint });
  logoChip(svg, M + 34, y + 18, 13, s.logo, s.sym);
  typeRun(svg, M + 54, y + 15, [[s.sym, 10.5, 750, TONE.hi], [`  ${s.cat.toUpperCase()}`, 6.4, 700, ink]]);
  para(svg, M + 54, y + 29, s.headline, "body", { fill: "#d9d5cc", maxW: W - 2 * M - 54 - 74, lh: 1.32 });
  if (s.key) {
    type(svg, W - M, y + 24, s.key.value, "num", { size: s.key.value.length > 9 ? 13 : 16, weight: 500, fill: ink, anchor: "end" });
    const lab = s.key.label.length > 16 ? s.key.label.split(" ").slice(0, 2).join(" ") : s.key.label;
    type(svg, W - M, y + 35, lab, "label", { fill: TONE.faint, size: 6.4, anchor: "end" });
  }
  if (i < S.length - 1) mk("line", { x1: M + 34, y1: y + RH - 4, x2: W - M, y2: y + RH - 4, class: "lo thin" }, svg);
});

type(svg, M, SAFE.bottom - 4, "Read every story on sectors.app/indonesia/news", "label", { fill: TONE.hi, size: 9, weight: 600 });
grain(0.09);
