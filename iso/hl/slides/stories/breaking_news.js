// Breaking news story: the approved News Flash cover at 9:16. The article photo full-bleed across the top
// two-thirds, fading into the ground; over its foot the ticker huge with the logo; the headline; one number.
// DATA.slide: { sym, logo, photo, headline, tag, hero: {label, value} }
const D = DATA, S = D.slide;
setAccent(D.direction);
photo(S.photo, 0, 0, W, 430, { fade: 0.55 });

const y0 = SAFE.top + 8;
const cap = (x, text, fill, anchor = "start") => {
  const t = type(svg, x, y0, text, "caps", { fill, weight: 750, anchor }), b = t.getBBox();
  svg.insertBefore(mk("rect", { x: b.x - 8, y: y0 - 9.5, width: b.width + 16, height: 15, rx: 7.5, style: `fill:${TONE.ground};fill-opacity:.8;stroke:${TONE.mid};stroke-width:.6px` }), t);
  return t;
};
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
cap(M + 10, "BREAKING", TONE.hi);
if (D.date) cap(W - M, D.date, TONE.hi, "end");

// the ticker, huge, with the logo, on the photo's foot
const tsize = Math.min(112, (W - 2 * M - 70) / (S.sym.length * 0.64));
logoChip(svg, W - M - 30, 318, 30, S.logo, S.sym);
type(svg, M - 4, 352, S.sym, "hero", { size: tsize, weight: 500, fill: TONE.hi });
mk("line", { x1: M, y1: 368, x2: M + 44, y2: 368, style: "stroke:var(--acc);stroke-width:2.4px" }, svg);
if (S.tag) type(svg, M + 54, 371, S.tag.toUpperCase(), "caps", { fill: "var(--acc)", size: 6 });

let y = para(svg, M, 400, S.headline, "title", { maxW: W - 2 * M, lh: 1.14 });
if (S.hero) {
  const hy = Math.max(y + 58, 482);
  type(svg, M, hy - 40, S.hero.label.toUpperCase(), "caps", { fill: TONE.faint, size: 6 });
  type(svg, M - 2, hy, S.hero.value, "num", { size: 44, weight: 450, fill: "var(--acc)" });
}
type(svg, M, SAFE.bottom - 14, "Read the full story on sectors.app/indonesia/news", "label", { fill: TONE.muted, size: 8, weight: 600 });
grain(0.09);
