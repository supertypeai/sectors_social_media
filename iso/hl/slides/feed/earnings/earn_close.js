// Earnings, last slide: three facts as tiles, the question, the CTA.
// DATA.slide: { title, sym, logo, facts: [{value, label, accent}], question, cta }
const D = DATA, S = D.slide, up = D.direction === "buy";
setAccent(D.direction);
const INK = up ? "#b2d2b9" : "#dc8d74";
frame(D);
logoChip(svg, M + 15, 70, 15, S.logo, S.sym);
type(svg, M + 37, 75, S.title, "title", { size: 19 });

const G = 8, tw = (W - 2 * M - 2 * G) / 3, th = 78, ty = 112;
S.facts.slice(0, 3).forEach((f, i) => {
  const x = M + i * (tw + G);
  mk("rect", { x, y: ty, width: tw, height: th, rx: 10, style: f.accent ? "fill:var(--acc);fill-opacity:.14;stroke:var(--acc);stroke-width:1px" : `fill:${TONE.card};stroke:${TONE.mid};stroke-width:.8px` }, svg);
  type(svg, x + 10, ty + 44, f.value, "num", { size: f.value.length > 8 ? 17 : 22, weight: 550, fill: f.accent ? INK : TONE.hi });
  wrapText(f.label, 7, tw - 20).slice(0, 2).forEach((l, k) => type(svg, x + 10, ty + 60 + k * 9, l, "label", { fill: TONE.muted, size: 7 }));
});
para(svg, M, 268, S.question, "title", { fill: TONE.hi, maxW: W - 2 * M });
type(svg, M, H - 48, S.cta, "label", { fill: "var(--acc)", size: 8.5, weight: 650 });
type(svg, W - M, H - 48, "Not financial advice.", "label", { fill: TONE.faint, size: 6.6, anchor: "end" });
grain(0.08);
