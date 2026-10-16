// News story, frame 2 (9:16): the lead story. Its photo full-bleed behind the top, fading into the ground;
// the ticker pill, a short headline, then the one number huge and at most two more side by side.
// DATA.slide: { sym, logo, photo, cat, headline, hero: {label, value, sub}, figures: [{label, value, sub}] }
const D = DATA, S = D.slide;
setAccent(D.direction);
if (S.photo) photo(S.photo, 0, 0, W, 360, { fade: 0.55, dim: 0.6 });
else glow(W * 0.7, 200, 240, 200, 0.1);
// a soft dark band behind the header so the kicker and date read over any photo
const hb = mk("linearGradient", { id: "hdrband", x1: 0, y1: 0, x2: 0, y2: 1 }, mk("defs", {}, svg));
[[0, 0], [0.35, 0.75], [0.65, 0.75], [1, 0]].forEach(([o, a]) => mk("stop", { offset: o, "stop-color": TONE.ground, "stop-opacity": a }, hb));
mk("rect", { x: 0, y: 70, width: W, height: 60, style: "fill:url(#hdrband);stroke:none" }, svg);
const { top, bottom } = storyFrame(D);

const py = top + 84;
const pw = logoPill(svg, M, py, S.sym, S.logo);
type(svg, M + pw + 8, py + 14.5, S.cat, "caps", { fill: TONE.hi, size: 6 });
let y = para(svg, M, py + 52, S.headline, "title", { maxW: W - 2 * M - 8, lh: 1.14 });

const figs = S.figures ?? [];
if (S.hero) {
  const big = S.hero.value.length > 9 ? 50 : 64;
  // sits under the headline, but its descenders always clear the rule over the small figures
  const limit = (figs.length ? bottom - 56 : bottom) - big * 0.2 - (S.hero.sub ? 20 : 0);
  const ty = Math.min(y + 40, limit - big * 0.9);
  type(svg, M, ty, S.hero.label, "caps", { fill: TONE.faint, size: 6.2 });
  type(svg, M - 2, ty + big * 0.9, S.hero.value, "num", { size: big, weight: 400, fill: "var(--acc)" });
  if (S.hero.sub) type(svg, M, ty + big * 0.9 + 20, S.hero.sub, "label", { fill: TONE.muted, size: 8.6 });
}
if (figs.length) {
  const FY = bottom - 30, cw = (W - 2 * M) / 2;
  mk("line", { x1: M, y1: FY - 16, x2: W - M, y2: FY - 16, class: "lo thin" }, svg);
  figs.forEach((f, i) => {
    const x = M + i * cw;
    if (i) mk("line", { x1: x - 10, y1: FY - 8, x2: x - 10, y2: FY + 26, class: "lo thin" }, svg);
    type(svg, x, FY, f.label, "caps", { fill: TONE.faint, size: 5.6 });
    type(svg, x, FY + 22, f.value, "num", { size: 20, weight: 300, fill: TONE.hi });
  });
}
grain();
