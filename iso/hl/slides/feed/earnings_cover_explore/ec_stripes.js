// Earnings cover, approach 2: data-pattern art. Every quarter is one full-height stripe ("warming stripes"),
// its brightness = that quarter's profit; each stripe is woven from hairlines whose count is the profit too.
// DATA.slide: eo_cover data + quarters [{label, v}]
const D = DATA, S = D.slide;
setAccent(D.direction);
const up = S.up, INK = up ? "#b2d2b9" : "#dc8d74", ACC = up ? [129, 167, 137] : [192, 113, 89];
frame(D);

logoChip(svg, M + 15, 66, 15, S.logo, S.sym);
type(svg, M + 37, 70, S.sym, "label", { fill: TONE.hi, size: 14, weight: 800 });
type(svg, M + 37, 80, S.name, "label", { fill: TONE.muted, size: 7.4 });

type(svg, M - 3, 150, S.hero, "hero", { size: 66, weight: 650, fill: INK });
type(svg, M, 172, S.line, "title", { size: 15, fill: TONE.hi });

const qs = S.quarters, n = qs.length, vmax = Math.max(...qs.map((q) => Math.max(0, q.v)));
const x0 = M, x1 = W - M, top = 196, bot = 382, sw = (x1 - x0) / n;
const G = [20, 18, 16], mix = (t) => `rgb(${G.map((g, i) => Math.round(g + (ACC[i] - g) * t)).join(",")})`;
const isNow = (i) => i === n - 1, isPrev = (q) => q.label === qs.find((p) => p.label.slice(0, 2) === qs[n - 1].label.slice(0, 2) && +p.label.slice(-4) === +qs[n - 1].label.slice(-4) - 1)?.label;
qs.forEach((q, i) => {
  const t = Math.max(0, q.v) / vmax, x = x0 + i * sw;
  mk("rect", { x: x + 0.6, y: top, width: sw - 1.2, height: bot - top, style: `fill:${mix(0.08 + 0.92 * t ** 0.9)};stroke:none` }, svg);
  // the weave: horizontal hairlines, as many as the profit is big
  const lines = Math.round(4 + 46 * t);
  for (let j = 0; j < lines; j++) {
    const y = bot - ((j + 0.5) / lines) * (bot - top);
    mk("line", { x1: x + 3, y1: y, x2: x + sw - 3, y2: y, style: `stroke:rgba(239,236,231,${(0.05 + 0.18 * t).toFixed(2)});stroke-width:.5px` }, svg);
  }
  const lab = q.label.replace(/^(Q\d)\D*\d\d(\d\d)$/, "$1 ’$2");
  const hi = isNow(i) || isPrev(q);
  type(svg, x + sw / 2, bot + 12, lab, "label", { fill: isNow(i) ? INK : hi ? TONE.hi : TONE.faint, size: 6.6, weight: hi ? 700 : 500, anchor: "middle" });
});
// the two compared stripes get their value on them
qs.forEach((q, i) => {
  if (!(isNow(i) || isPrev(q))) return;
  const x = x0 + i * sw + sw / 2, t = Math.max(0, q.v) / vmax;
  type(svg, x, top - 6, isNow(i) ? S.now.s : S.prev.s, "label", { fill: isNow(i) ? INK : TONE.hi, size: isNow(i) ? 9 : 7.6, weight: 700, anchor: "middle" });
  mk("line", { x1: x, y1: top - 3, x2: x, y2: top + 6, style: `stroke:${isNow(i) ? INK : TONE.edge};stroke-width:.8px` }, svg);
});
type(svg, M, bot + 26, `${n} quarters · brighter stripe = more profit`, "label", { fill: TONE.faint, size: 6.4 });
grain(0.07);
