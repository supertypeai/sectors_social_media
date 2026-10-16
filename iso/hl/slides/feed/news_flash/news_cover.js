// News Flash, slide 1: the lead story's photo across the top, fading into the ground; over its foot the
// ticker huge and light with the company's logo, then the headline and the other tickers in today's flash.
// DATA.slide: { sym, logo, photo, headline, tag, date, more: [sym] }
const D = DATA, S = D.slide;
setAccent(D.direction);
photo(S.photo, 0, 0, W, 300, { fade: 0.6 });
// no photo: the company's sector icon, large and faint, fills the space the photo would have taken
if (!S.photo && S.sector) drawSectorIcon(mk("g", { opacity: 0.22 }, svg), S.sector, { cx: W * 0.64, cy: 118, S: 2.3 });
frame(D);

// a solid accent pill with white type (the header already names the flash and the date, so no pill repeats it)
const pill = (x, y, text) => {
  const w = text.length * 4.8 + 18;
  mk("rect", { x, y: y - 9.5, width: w, height: 14, rx: 7, style: "fill:var(--acc);stroke:none" }, svg);
  type(svg, x + w / 2, y + 1, text, "caps", { fill: "#ffffff", size: 6, weight: 750, anchor: "middle" });
  return w;
};

// the logo, in a hairline ring, level with the ticker
const LX = W - M - 30, LY = 214, LR = 26;
if (S.logo) {
  const cp = mk("clipPath", { id: "biglogo" }, mk("defs", {}, svg));
  mk("circle", { cx: LX, cy: LY, r: LR - 3 }, cp);
  mk("circle", { cx: LX, cy: LY, r: LR + 5, class: "nf", style: `stroke:${TONE.edge};stroke-width:.8px;opacity:.6` }, svg);
  mk("circle", { cx: LX, cy: LY, r: LR, style: `fill:#f2efe9;stroke:${TONE.edge}` }, svg);
  mk("image", { href: S.logo, x: LX - LR + 5, y: LY - LR + 5, width: 2 * LR - 10, height: 2 * LR - 10, "clip-path": "url(#biglogo)", preserveAspectRatio: "xMidYMid meet" }, svg);
}

// the ticker, huge and light, sized to clear the logo
const tsize = Math.min(96, (W - 2 * M - (S.logo ? 74 : 0)) / (S.sym.length * 0.66));
type(svg, M - 4, 244, S.sym, "hero", { size: tsize, weight: 420, fill: TONE.hi });
mk("line", { x1: M, y1: 262, x2: M + 40, y2: 262, style: "stroke:var(--acc);stroke-width:2px" }, svg);

// the headline; the tags only when there is room
// a long headline steps down in size until it fits 3 lines, so it keeps air above the "also today" row
const { size: hsize, lines: hl } = fitText(S.headline, { size: ROLES.title.size, min: 14, lines: 3 });
hl.forEach((l, i) => type(svg, M, 290 + i * hsize * 1.14, l, "title", { size: hsize }));
const y = 290 + (hl.length - 1) * hsize * 1.14;
if (S.tag && y < 340) type(svg, M, y + 18, S.tag, "caps", { fill: TONE.faint, size: 5.8 });

if (S.more?.length) {
  // the row sits well clear of the rule above it: label on its own line, then the pills
  const Y = H - 50;
  mk("line", { x1: M, y1: Y - 34, x2: W - M, y2: Y - 34, class: "lo thin" }, svg);
  // a plain label: the solid ticker pills below already carry the colour
  type(svg, M, Y - 15, "ALSO TODAY", "caps", { fill: TONE.muted, size: 6, weight: 750 });
  type(svg, W - M, Y - 17, "swipe →", "label", { fill: TONE.muted, size: 7, anchor: "end" });
  let x = M;
  for (const s of S.more) x += logoPill(svg, x, Y - 6, s.sym, s.logo, { h: 16, size: 8 }) + 7;
}
grain();
