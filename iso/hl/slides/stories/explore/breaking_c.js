// Breaking news, C · card. A rounded photo card at the top (the BREAKING chip and ticker on it), then an
// editorial block: headline, the lead in two lines, and three numbers as tiles.
const D = DATA, S = D.slide;
setAccent(D.direction);
const INK = "#b2d2b9";
dotField(0, 0, W, H, { fx: W * 0.5, fy: 420, reach: 320, op: 0.28 });

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "BREAKING NEWS", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, D.date ?? "", "caps", { fill: TONE.muted, weight: 700, anchor: "end" });

// the photo card
const cx = M, cy = y0 + 18, cw = W - 2 * M, ch = 200;
const defs = mk("defs", {}, svg);
mk("rect", { x: cx, y: cy, width: cw, height: ch, rx: 14 }, mk("clipPath", { id: "card" }, defs));
const lg = mk("linearGradient", { id: "cardg", x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
[[0, 0.15], [0.6, 0.25], [1, 0.85]].forEach(([o, a]) => mk("stop", { offset: o, "stop-color": TONE.ground, "stop-opacity": a }, lg));
const g = mk("g", { "clip-path": "url(#card)" }, svg);
if (S.photo) mk("image", { href: S.photo, x: cx, y: cy, width: cw, height: ch, preserveAspectRatio: "xMidYMid slice", style: "filter:saturate(.75) brightness(.85)" }, g);
mk("rect", { x: cx, y: cy, width: cw, height: ch, style: "fill:url(#cardg);stroke:none" }, g);
mk("rect", { x: cx, y: cy, width: cw, height: ch, rx: 14, style: `fill:none;stroke:${TONE.mid};stroke-width:.8px` }, svg);
logoPill(svg, cx + 12, cy + ch - 34, S.sym, S.logo, { h: 22, size: 12 });
if (S.tag) {
  const t = S.tag.toUpperCase(), tw = t.length * 4.6 + 16;
  mk("rect", { x: cx + cw - 12 - tw, y: cy + ch - 30, width: tw, height: 14, rx: 7, style: `fill:${TONE.ground};fill-opacity:.8;stroke:var(--acc);stroke-width:.8px` }, svg);
  type(svg, cx + cw - 12 - tw / 2, cy + ch - 20.5, t, "caps", { fill: "var(--acc)", size: 5.8, anchor: "middle" });
}

// headline + lead
const lines = wrapText(S.headline, 21, W - 2 * M, 0.5).slice(0, 3);
lines.forEach((l, i) => type(svg, M, cy + ch + 36 + i * 25, l, "title", { size: 21, fill: TONE.hi }));
const hy = cy + ch + 36 + (lines.length - 1) * 25;
// the lead's first clause only, never cut with "…"; dropped if even that is too long
const clause = (S.lead || "").split(/,\s| — /)[0];
const lead = wrapText(clause, 9, W - 2 * M);
if (lead.length <= 2) lead.forEach((l, i) => type(svg, M, hy + 24 + i * 13, l, "label", { fill: TONE.muted, size: 9 }));

// three number tiles
const facts = [S.hero].concat(S.figures || []).slice(0, 3), tw = (W - 2 * M - 16) / 3, th = 58, ty = SAFE.bottom - 30 - th;
facts.forEach((f, i) => {
  const x = M + i * (tw + 8);
  mk("rect", { x, y: ty, width: tw, height: th, rx: 10, style: `fill:${TONE.card};stroke:${i ? TONE.mid : "var(--acc)"};stroke-width:.8px` }, svg);
  type(svg, x + 10, ty + 28, f.value.replace(" shares", ""), "num", { size: f.value.length > 9 ? 14 : 17, weight: 550, fill: i ? TONE.hi : INK });
  type(svg, x + 10, ty + 44, f.label + (f.value.includes("shares") ? " (shares)" : ""), "label", { fill: TONE.muted, size: 6.6 });
});
type(svg, M, SAFE.bottom - 4, `Source: ${S.source} · full story on sectors.app`, "label", { fill: TONE.muted, size: 8 });
grain(0.09);
