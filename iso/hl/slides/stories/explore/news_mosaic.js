// News compilation, direction 3: photo mosaic. Five tiles like a magazine contents page: the lead big across the
// top, four below in a 2×2 grid; every tile is its article photo with the logo pill and headline on a fade.
const D = DATA, S = D.stories.slice(0, 5);
setAccent("buy");
const GI = "#b2d2b9", TI = "#dc8d74";

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "IDX NEWS", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, D.company, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });
type(svg, M, y0 + 40, "Today's 5 stories", "hero", { size: 30, weight: 500 });

let tid = 0;
function tile(s, x, y, w, h, big) {
  const id = `tl${++tid}`, defs = mk("defs", {}, svg);
  mk("rect", { x, y, width: w, height: h, rx: 10 }, mk("clipPath", { id }, defs));
  const lg = mk("linearGradient", { id: `${id}g`, x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
  mk("stop", { offset: 0, "stop-color": TONE.ground, "stop-opacity": 0.05 }, lg);
  mk("stop", { offset: 0.45, "stop-color": TONE.ground, "stop-opacity": 0.35 }, lg);
  mk("stop", { offset: 1, "stop-color": TONE.ground, "stop-opacity": 0.95 }, lg);
  const g = mk("g", { "clip-path": `url(#${id})` }, svg);
  mk("rect", { x, y, width: w, height: h, style: `fill:${TONE.card};stroke:none` }, g);
  if (s.photo) mk("image", { href: s.photo, x, y, width: w, height: h, preserveAspectRatio: "xMidYMid slice", style: "filter:saturate(.75) brightness(.8)" }, g);
  mk("rect", { x, y, width: w, height: h, style: `fill:url(#${id}g);stroke:none` }, g);
  mk("rect", { x, y, width: w, height: h, rx: 10, style: `fill:none;stroke:${TONE.mid};stroke-width:.8px` }, svg);
  const ink = s.bear ? TI : GI;
  logoChip(svg, x + 18, y + 18, 10, s.logo, s.sym);
  type(svg, x + 33, y + 21.5, s.sym, "label", { fill: TONE.hi, size: 9.5, weight: 750 });
  type(svg, x + 10, y + h - (big ? 52 : 46), s.cat.toUpperCase(), "caps", { fill: ink, size: 5.6 });
  const lines = wrapText(s.headline, big ? 12 : 8.8, w - 20).slice(0, big ? 2 : 3);
  lines.forEach((l, i) => type(svg, x + 10, y + h - (big ? 36 : 33) + i * (big ? 14 : 10.5), l, "label", { fill: TONE.hi, size: big ? 12 : 8.8, weight: 650 }));
  if (s.key && big) type(svg, x + w - 10, y + 24, s.key.value, "num", { size: 20, weight: 500, fill: ink, anchor: "end" });
}
const top = y0 + 56, G = 8, Wd = W - 2 * M, hBig = 178, hS = (SAFE.bottom - 30 - top - hBig - 2 * G) / 2, wS = (Wd - G) / 2;
tile(S[0], M, top, Wd, hBig, true);
S.slice(1, 5).forEach((s, i) => tile(s, M + (i % 2) * (wS + G), top + hBig + G + Math.floor(i / 2) * (hS + G), wS, hS, false));

type(svg, M, SAFE.bottom - 4, "Read every story on sectors.app/indonesia/news", "label", { fill: TONE.hi, size: 9, weight: 600 });
grain(0.09);
