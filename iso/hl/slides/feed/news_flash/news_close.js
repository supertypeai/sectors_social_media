// News Flash, last slide: today's stories as a numbered index, the question, the CTA.
// DATA.slide: { title, items: [{sym, headline}], question, cta }
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

let y = para(svg, M, 74, S.title, "title");
y += 24;
S.items.forEach((it, i) => {
  mk("line", { x1: M, y1: y, x2: W - M, y2: y, class: "lo thin" }, svg);
  logoChip(svg, M + 10, y + 18, 10, it.logo, it.sym);
  type(svg, M + 30, y + 16, it.sym, "label", { fill: "var(--acc)", size: 9.5, weight: 700 });
  const end = para(svg, M + 30, y + 29, it.headline, "body", { fill: "#d6d3d1", maxW: W - 2 * M - 30, lh: 1.35 });
  y = end + 16;
});
mk("line", { x1: M, y1: y, x2: W - M, y2: y, class: "lo thin" }, svg);
// the question sits just above the CTA, never on it
const qLines = wrapText(S.question, ROLES.title.size, W - 2 * M).length;
para(svg, M, Math.min(y + 36, H - 66 - (qLines - 1) * ROLES.title.size * 1.12), S.question, "title", { fill: TONE.hi, maxW: W - 2 * M });
type(svg, M, H - 46, S.cta, "label", { fill: "var(--acc)", size: 8.5, weight: 650 });
type(svg, W - M, H - 46, "Not financial advice.", "label", { fill: TONE.faint, size: 6.6, anchor: "end" });
