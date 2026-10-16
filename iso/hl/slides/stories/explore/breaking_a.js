// Breaking news, A · refined cover. Photo full-bleed over the top 60% with a deep, eased fade; a solid accent
// "BREAKING" tab; ticker pill with logo and the company name; the headline large; then a facts strip of three
// numbers in a hairline row; source at the foot.
const D = DATA, S = D.slide;
setAccent(D.direction);
const INK = "#b2d2b9";
photo(S.photo, 0, 0, W, 400, { fade: 0.62 });
// extra darkening at the very top for the header
const tg = mk("linearGradient", { id: "topd", x1: 0, y1: 0, x2: 0, y2: 1 }, mk("defs", {}, svg));
mk("stop", { offset: 0, "stop-color": TONE.ground, "stop-opacity": 0.75 }, tg);
mk("stop", { offset: 1, "stop-color": TONE.ground, "stop-opacity": 0 }, tg);
mk("rect", { x: 0, y: 0, width: W, height: SAFE.top + 60, style: "fill:url(#topd);stroke:none" }, svg);

const y0 = SAFE.top + 8;
// BREAKING badge: a live dot with a halo, the word, then "IDX" in a dark half; the date in a matching capsule
{
  const h = 20, by = y0 - 13, wA = 76, wB = 30;
  mk("rect", { x: M, y: by, width: wA + wB, height: h, rx: h / 2, style: `fill:${TONE.ground};fill-opacity:.85;stroke:var(--acc);stroke-width:1px` }, svg);
  mk("path", { d: `M${M + h / 2} ${by}H${M + wA}V${by + h}H${M + h / 2}a${h / 2} ${h / 2} 0 0 1 0 ${-h}Z`, style: "fill:var(--acc);stroke:none" }, svg);
  mk("circle", { cx: M + 11, cy: by + h / 2, r: 5.5, style: `fill:${TONE.ground};fill-opacity:.25` }, svg);
  mk("circle", { cx: M + 11, cy: by + h / 2, r: 2.6, style: `fill:${TONE.ground}` }, svg);
  type(svg, M + 20, by + h / 2 + 2.6, "BREAKING", "caps", { fill: TONE.ground, size: 7, weight: 800 });
  type(svg, M + wA + wB / 2, by + h / 2 + 2.6, "IDX", "caps", { fill: TONE.hi, size: 7, weight: 800, anchor: "middle" });
  const dt = D.date ?? "", dw = dt.length * 5.6 + 18;
  mk("rect", { x: W - M - dw, y: by, width: dw, height: h, rx: h / 2, style: `fill:${TONE.ground};fill-opacity:.85;stroke:${TONE.mid};stroke-width:.8px` }, svg);
  type(svg, W - M - dw / 2, by + h / 2 + 2.6, dt, "caps", { fill: TONE.hi, size: 7, weight: 750, anchor: "middle" });
}

// ticker row
const ty = 300;
logoPill(svg, M, ty, S.sym, S.logo, { h: 24, size: 13 });
type(svg, M + S.sym.length * 8 + 46, ty + 16, S.name ?? "", "label", { fill: TONE.hi, size: 10, weight: 600 });
if (S.tag) type(svg, W - M, ty + 16, S.tag.toUpperCase(), "caps", { fill: "var(--acc)", size: 6.4, weight: 750, anchor: "end" });

// headline
// a long headline steps down in size to fit 3 lines (it is never cut)
const { size: hs, lines } = fitText(S.headline, { size: 23, min: 16, lines: 3 });
lines.forEach((l, i) => type(svg, M, ty + 58 + i * hs * 1.17, l, "title", { size: hs, fill: TONE.hi }));
const hy = ty + 58 + (lines.length - 1) * hs * 1.17;

// three number tiles: short caps label on top, the value big, its unit under it; the lead tile tinted
const short = (l) => l.replace(/^Total transaction value$/i, "Deal value").replace(/^Shares acquired$/i, "Shares bought").replace(/^Transaction price$/i, "Price");
const facts = [S.hero].concat(S.figures || []).slice(0, 3).map((f) => {
  let v = f.value, unit = f.sub || "";
  if (/ shares$/.test(v)) { v = v.replace(/ shares$/, ""); unit = "shares"; }
  return { label: short(f.label).toUpperCase(), v, unit };
});
const G = 8, tw = (W - 2 * M - G * (facts.length - 1)) / facts.length, th = 66, fy = Math.max(hy + 40, SAFE.bottom - 32 - th);
facts.forEach((f, i) => {
  const x = M + i * (tw + G), lead = i === 0;
  mk("rect", { x, y: fy, width: tw, height: th, rx: 10, style: lead ? `fill:var(--acc);fill-opacity:.14;stroke:var(--acc);stroke-width:1px` : `fill:${TONE.card};fill-opacity:.85;stroke:${TONE.mid};stroke-width:.8px` }, svg);
  type(svg, x + 10, fy + 16, f.label, "caps", { fill: lead ? INK : TONE.muted, size: 5.6, weight: 750 });
  type(svg, x + 10, fy + 42, f.v, "num", { size: f.v.length > 8 ? 17 : 20, weight: 550, fill: lead ? INK : TONE.hi });
  if (f.unit) type(svg, x + 10, fy + 56, f.unit, "label", { fill: TONE.muted, size: 7 });
});

type(svg, M, SAFE.bottom - 4, `Source: ${S.source}`, "label", { fill: TONE.muted, size: 8 });
type(svg, W - M, SAFE.bottom - 4, "sectors.app", "label", { fill: TONE.muted, size: 7.4, anchor: "end", weight: 650 });
grain(0.09);
