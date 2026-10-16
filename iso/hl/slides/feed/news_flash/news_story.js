// News Flash, one story per slide: the photo across the top, the ticker pill with its logo, a short headline,
// then the one number that matters set huge and at most two more beside each other. No paragraph.
// DATA.slide: { sym, logo, photo, headline, hero: {label, value, sub}, figures: [{label, value, sub}], source }
const D = DATA, S = D.slide;
setAccent(D.direction);
if (S.photo) photo(S.photo, 0, 0, W, 200, { fade: 0.62 });
// no photo: the sector icon as a faint backdrop at the top right, behind the headline
else if (S.sector) drawSectorIcon(mk("g", { opacity: 0.16 }, svg), S.sector, { cx: W - 92, cy: 150, S: 1.9 });
frame(D);

logoPill(svg, M, S.photo ? 120 : 64, S.sym, S.logo);
// a long headline steps down in size so it stays within 3 lines under a photo (4 without one)
const hl = fitText(S.headline, { size: ROLES.title.size, min: 15, maxW: W - 2 * M - 10, lines: S.photo ? 3 : 4 });
const hy0 = (S.photo ? 120 : 64) + 46;
hl.lines.forEach((l, i) => type(svg, M, hy0 + i * hl.size * 1.16, l, "title", { size: hl.size }));
let y = hy0 + (hl.lines.length - 1) * hl.size * 1.16;

// the hero figure: label, the number huge, what it means under it
const figs = S.figures ?? [];
const zone = H - 44 - (figs.length ? 64 : 0);  // where the hero must end, above the two small figures
if (S.hero) {
  // the number shrinks too when the headline leaves less room, so it never reaches the figures row below
  const room = (figs.length ? H - 116 : H - 52) - (y + 34) - (S.hero.sub ? 22 : 0);
  const big = Math.max(26, Math.min(S.hero.value.length > 10 ? 40 : 52, room / 0.92));
  const top = Math.max(y + 34, Math.min(y + 60, zone - big - 30));
  type(svg, M, top, S.hero.label, "caps", { fill: TONE.faint, size: 6 });
  type(svg, M - 2, top + big * 0.92, S.hero.value, "num", { size: big, weight: 400, fill: TONE.hi });
  if (S.hero.sub) type(svg, M, top + big * 0.92 + 22, S.hero.sub, "label", { fill: TONE.muted, size: 8.4 });
}

// at most two more figures, side by side
if (figs.length) {
  const FY = H - 96, cw = (W - 2 * M) / 2;
  mk("line", { x1: M, y1: FY - 14, x2: W - M, y2: FY - 14, class: "lo thin" }, svg);
  figs.slice(0, 2).forEach((f, i) => {
    const x = M + i * cw;
    if (i) mk("line", { x1: x - 10, y1: FY - 6, x2: x - 10, y2: FY + 34, class: "lo thin" }, svg);
    type(svg, x, FY, f.label, "caps", { fill: TONE.faint, size: 5.6 });
    type(svg, x, FY + 20, f.value, "num", { size: f.value.length > 10 ? 15 : 19, weight: 300, fill: TONE.hi });
    if (f.sub) type(svg, x, FY + 36, f.sub, "label", { fill: TONE.muted, size: 6.8 });
  });
}
type(svg, W - M, H - 40, S.source, "label", { fill: TONE.faint, size: 6, anchor: "end" });
grain(); // fine noise also hides any banding in the photo's fade
