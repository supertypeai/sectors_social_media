// Insider cover, approach 4 — image treatment: the holder as a poster. Their monogram (or their logo, when the
// holder is a listed company) as a two-tone ordered dither filling the top of the page, the name and the deal
// set over its fading lower edge. DATA.slide: the vp_cover payload plus slide.dither (a PNG data URI).
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

const pc = (v) => (v < 0.005 ? "0%" : (v >= 10 ? v.toFixed(1) : v.toFixed(2)).replace(/\.?0+$/, "") + "%");

/** The dither image melted into the page through a soft radial mask (no box edge anywhere). */
let vid = 0;
function vignetteImage(href, x, y, w, h, op = 1) {
  const id = `vg${++vid}`, defs = mk("defs", {}, svg);
  const rg = mk("radialGradient", { id: `${id}g`, cx: 0.5, cy: 0.45, r: 0.55 }, defs);
  [[0, 1], [0.6, 0.9], [0.85, 0.3], [1, 0]].forEach(([o, a]) => mk("stop", { offset: o, "stop-color": "#fff", "stop-opacity": a }, rg));
  const mask = mk("mask", { id: `${id}m`, maskUnits: "userSpaceOnUse", x, y, width: w, height: h }, defs);
  mk("rect", { x, y, width: w, height: h, style: `fill:url(#${id}g);stroke:none` }, mask);
  mk("image", { href, x, y, width: w, height: h, mask: `url(#${id}m)`, style: `opacity:${op};mix-blend-mode:lighten`, preserveAspectRatio: "xMidYMid slice" }, svg);
}
// the dithered monogram, big, right of centre, bleeding off the right edge
const iw = 236, ix = W - iw + 22, iy = 34;
vignetteImage(S.dither, ix, iy, iw, iw);
if (S.other && S.otherDither) {
  // the seller as a small, dimmer dither on the left: the stake came from them
  vignetteImage(S.otherDither, M - 14, iy + 40, 110, 110, 0.5);
  type(svg, M, iy + 150, `from ${S.other.name.split(" ").slice(0, 2).join(" ")}`, "label", { size: 7, fill: TONE.muted });
}
type(svg, M, iy + 22, S.other ? "The buyer" : S.sell ? "The seller" : "The buyer", "caps", { fill: "var(--acc)", weight: 750 });
if (S.holder.sym) type(svg, M, iy + 32, `Listed as ${S.holder.sym}`, "label", { size: 7, fill: TONE.muted });

// ---------------------------------------------------------------- the name and the deal over the fade
let size = 44, lines;
for (; size > 24; size -= 2) {
  lines = wrapText(S.holder.name, size, W - 2 * M, 0.5);
  if (lines.length <= 2 && Math.max(...lines.map((l) => l.length)) * size * 0.5 <= W - 2 * M) break;
}
let y = 290 - (lines.length - 1) * size * 0.5;
for (const l of lines) { type(svg, M - 2, y, l, "hero", { size, weight: 360 }); y += size * 0.98; }
const hs = 16, hl = wrapText(S.headline, hs, W - 2 * M, 0.47);
y += 2;
for (const l of hl.slice(0, 2)) {
  const t = type(svg, M, y, "", "title", { size: hs, weight: 500 });
  t.innerHTML = l.split(" ").map((w) => S.accent.includes(w) ? `<tspan style="fill:var(--acc)">${esc(w)}</tspan>` : esc(w)).join(" ");
  y += hs * 1.15;
}

// ---------------------------------------------------------------- a quiet stat strip
const ly = 398;
mk("line", { x1: M, y1: ly - 16, x2: W - M, y2: ly - 16, class: "lo thin" }, svg);
typeRun(svg, M, ly, [[pc(S.before), 12, 400, TONE.muted], ["  →  ", 10, 400, TONE.faint], [pc(S.after), 12, 600, TONE.hi], ["  stake", 7.5, 500, TONE.muted]]);
typeRun(svg, W - M, ly, [[S.value, 12, 450, "var(--acc)"], [`  ·  ${S.span}`, 7.5, 500, TONE.muted]], { anchor: "end" });
grain(0.05);
