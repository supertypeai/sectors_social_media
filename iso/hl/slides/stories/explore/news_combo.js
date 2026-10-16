// News compilation, mosaic × numbers: five photo tiles (the lead big across the top, four in a 2×2 grid). Each
// tile is its article photo darkened at the foot, with the logo and ticker, the story's one number set big,
// what that number is, and the headline.
const D = DATA, S = D.stories.slice(0, 5);
setAccent("buy");
const GI = "#b2d2b9", TI = "#dc8d74";

// a number that can't be the company's own (e.g. a national "Rp 2,900 T" target) is left out, not shown
const sane = (k) => {
  if (!k) return null;
  const m = /([\d.,]+)\s*T\b/.exec(k.value);
  return m && parseFloat(m[1].replace(/,/g, "")) > 1000 ? null : k;
};

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "IDX NEWS", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, D.company, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });
typeRun(svg, M, y0 + 40, [["Today's ", 30, 500, TONE.hi], [`${S.length} stories`, 30, 500, GI]]);

/** A small hairline icon per category, centred on (cx, cy). */
function catIcon(cat, cx, cy, s, color) {
  const st = `fill:none;stroke:${color};stroke-width:1px;stroke-linecap:round;stroke-linejoin:round`;
  const p = (d) => mk("path", { d, style: st }, svg);
  const c = cat.toLowerCase();
  if (c.includes("m&a") || c.includes("acqui")) { // two rings merging
    mk("circle", { cx: cx - s * 0.32, cy, r: s * 0.55, style: st }, svg); mk("circle", { cx: cx + s * 0.32, cy, r: s * 0.55, style: st }, svg);
  } else if (c.includes("earn")) { // rising bars
    p(`M${cx - s * 0.8} ${cy + s * 0.7}V${cy + s * 0.1}M${cx} ${cy + s * 0.7}V${cy - s * 0.3}M${cx + s * 0.8} ${cy + s * 0.7}V${cy - s * 0.8}`);
  } else if (c.includes("divid")) { // a coin
    mk("circle", { cx, cy, r: s * 0.8, style: st }, svg); mk("circle", { cx, cy, r: s * 0.4, style: st }, svg);
  } else if (c.includes("right")) { // a ticket
    p(`M${cx - s} ${cy - s * 0.6}H${cx + s}V${cy - s * 0.15}a${s * 0.15} ${s * 0.15} 0 0 0 0 ${s * 0.3}V${cy + s * 0.6}H${cx - s}V${cy + s * 0.15}a${s * 0.15} ${s * 0.15} 0 0 0 0 ${-s * 0.3}Z`);
  } else if (c.includes("analyst") || c.includes("rating")) { // a target
    mk("circle", { cx, cy, r: s * 0.8, style: st }, svg); mk("circle", { cx, cy, r: s * 0.3, style: st }, svg);
  } else { // a page
    p(`M${cx - s * 0.6} ${cy - s * 0.8}H${cx + s * 0.6}V${cy + s * 0.8}H${cx - s * 0.6}ZM${cx - s * 0.3} ${cy - s * 0.3}H${cx + s * 0.3}M${cx - s * 0.3} ${cy + s * 0.1}H${cx + s * 0.3}`);
  }
}
/** The category as a readable pill: dark fill, accent hairline, icon + label, right-aligned at xr. */
function catPill(cat, xr, cy, ink, big = false) {
  // compact on the small tiles; one step larger on the lead tile
  const fs = big ? 5.8 : 5, h = big ? 14 : 11, ic = big ? 3.4 : 2.7, pad = big ? 21 : 17;
  const t = type(svg, 0, cy + fs * 0.38, cat.toUpperCase(), "caps", { fill: PT.hi, size: fs, weight: 750 }), tw = t.getBBox().width;
  const w = tw + pad, x = xr - w;
  t.setAttribute("x", x + pad - 4.5);
  svg.insertBefore(mk("rect", { x, y: cy - h / 2, width: w, height: h, rx: h / 2, style: `fill:${PT.ground};fill-opacity:.8;stroke:${ink};stroke-width:.7px;stroke-opacity:.85` }), t);
  catIcon(cat, x + h / 2 + 1.5, cy, ic, ink);
}

let tid = 0;
// photo tiles stay dark in both themes (rgb() so the light-theme colour swap leaves them alone): text on a
// photo needs a dark scrim to be readable
const PT = { ground: "rgb(20,18,16)", card: "rgb(39,36,33)", mid: "rgb(72,66,61)", hi: "rgb(239,236,231)", muted: "rgb(176,170,156)",
  head: "rgb(228,224,216)", gi: "rgb(178,210,185)", ti: "rgb(220,141,116)" };
function tile(s, x, y, w, h, big) {
  const id = `tl${++tid}`, defs = mk("defs", {}, svg), k = sane(s.key), ink = s.bear ? PT.ti : PT.gi;
  mk("rect", { x, y, width: w, height: h, rx: 10 }, mk("clipPath", { id }, defs));
  const lg = mk("linearGradient", { id: `${id}g`, x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
  // darker overall, and a deep fade under the text block
  mk("stop", { offset: 0, "stop-color": PT.ground, "stop-opacity": 0.6 }, lg);
  mk("stop", { offset: 0.3, "stop-color": PT.ground, "stop-opacity": 0.45 }, lg);
  mk("stop", { offset: 0.55, "stop-color": PT.ground, "stop-opacity": 0.85 }, lg);
  mk("stop", { offset: 1, "stop-color": PT.ground, "stop-opacity": 0.98 }, lg);
  const g = mk("g", { "clip-path": `url(#${id})` }, svg);
  mk("rect", { x, y, width: w, height: h, style: `fill:${PT.card};stroke:none` }, g);
  if (s.photo) mk("image", { href: s.photo, x, y, width: w, height: h, preserveAspectRatio: "xMidYMid slice", style: "filter:saturate(.7) brightness(.78)" }, g);
  mk("rect", { x, y, width: w, height: h, style: `fill:url(#${id}g);stroke:none` }, g);
  mk("rect", { x, y, width: w, height: h, rx: 10, style: `fill:none;stroke:${PT.mid};stroke-width:.8px` }, svg);

  // top: logo, ticker, category
  logoChip(svg, x + 18, y + 18, 10, s.logo, s.sym);
  type(svg, x + 33, y + 21.5, s.sym, "label", { fill: PT.hi, size: 9.5, weight: 750 });
  catPill(s.cat, x + w - 9, y + 18, ink, big);

  // bottom, upwards: headline, then the number and what it is
  // a long headline steps down in size to fit 2 lines in its tile (it is never cut)
  const { size: hs, lines } = fitText(s.headline, { size: big ? 10.5 : 8, min: big ? 8.5 : 6.4, maxW: w - 20, lines: 2 });
  let by = y + h - 10 - (lines.length - 1) * hs * 1.25;
  lines.forEach((l, i) => type(svg, x + 10, by + i * hs * 1.25, l, "label", { fill: PT.head, size: hs, weight: 600 }));
  if (k) {
    const ns = big ? 30 : k.value.length > 9 ? 16 : 19;
    const ly = by - hs * 1.25 - 5;
    type(svg, x + 10, ly, k.label, "label", { fill: PT.muted, size: big ? 7.6 : 6.6 });
    type(svg, x + 9, ly - (big ? 16 : 13), k.value, "num", { size: ns, weight: 500, fill: ink });
  }
}
const top = y0 + 56, G = 8, Wd = W - 2 * M, hBig = 186, hS = (SAFE.bottom - 30 - top - hBig - 2 * G) / 2, wS = (Wd - G) / 2;
tile(S[0], M, top, Wd, hBig, true);
S.slice(1, 5).forEach((s, i) => tile(s, M + (i % 2) * (wS + G), top + hBig + G + Math.floor(i / 2) * (hS + G), wS, hS, false));

type(svg, M, SAFE.bottom - 4, "Every story on sectors.app/indonesia/news", "label", { fill: TONE.hi, size: 9, weight: 600 });
type(svg, W - M, SAFE.bottom - 4, "sectors.app", "label", { fill: TONE.muted, size: 7.4, anchor: "end", weight: 650 });
grain(0.09);
