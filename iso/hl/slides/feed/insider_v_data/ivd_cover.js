// Insider "story of the deal", slide 1: the deal in one number. The share of the company that moved, huge,
// in the accent; who did it and for how much in one line; three plain facts underneath.
// DATA.slide: { sym, name, logoSym, big, of, verbLine, line, strip: [{v, l}] }
const D = DATA, S = D.slide;
setAccent(D.direction);
dotField(0, 60, W, 300, { fx: W * 0.78, fy: 150, reach: 230, op: 0.28 });
glow(W * 0.42, 180, 200, 120, 0.15);
frame(D);

logoPill(svg, M, 64, S.sym, S.logoSym, { h: 22, size: 11.5 });

// the number
const size = S.big.length <= 3 ? 150 : S.big.length <= 5 ? 122 : 100;
type(svg, M - 5, 206, S.big, "hero", { size, weight: 230, fill: "var(--acc)" });
let y = para(svg, M, 240, S.of, "title", { maxW: W - 2 * M, lh: 1.1, fill: TONE.hi });
type(svg, M, y + 20, S.verbLine, "label", { fill: TONE.muted, size: 10.5, weight: 500 });

// who, and for how much
wrapText(S.line, 13, W - 2 * M, 0.5).forEach((l, i) => type(svg, M, y + 56 + i * 17, l, "body", { size: 13, weight: 420, fill: TONE.hi }));

// three plain facts
const FY = 360, cw = (W - 2 * M) / 3;
mk("line", { x1: M, y1: FY - 20, x2: W - M, y2: FY - 20, class: "lo thin" }, svg);
S.strip.forEach((f, i) => {
  const x = M + i * cw;
  if (i) mk("line", { x1: x - 8, y1: FY - 11, x2: x - 8, y2: FY + 20, class: "lo thin" }, svg);
  type(svg, x, FY + 2, f.v, "num", { size: f.v.length > 11 ? 13.5 : f.v.length > 8 ? 17 : 19, weight: 320 });
  type(svg, x, FY + 16, f.l, "label", { fill: TONE.muted, size: 6.6 });
});
type(svg, W - M, H - 46, "Swipe for the story →", "label", { fill: TONE.faint, size: 7, anchor: "end" });
grain(0.06);
