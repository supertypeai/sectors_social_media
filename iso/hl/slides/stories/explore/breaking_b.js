// Breaking news, B · headline-led. The photo fills the whole frame, heavily darkened; the headline is the hero,
// huge and left-aligned in the lower half with the deal number in the accent; ticker and logo sit above it.
const D = DATA, S = D.slide;
setAccent(D.direction);
const INK = "#b2d2b9";
if (S.photo) {
  const g = mk("g", {}, svg);
  mk("image", { href: S.photo, x: -60, y: 0, width: W + 120, height: H, preserveAspectRatio: "xMidYMid slice", style: "filter:saturate(.6) brightness(.55)" }, g);
}
const og = mk("linearGradient", { id: "ov", x1: 0, y1: 0, x2: 0, y2: 1 }, mk("defs", {}, svg));
[[0, 0.7], [0.28, 0.35], [0.5, 0.72], [0.72, 0.95], [1, 1]].forEach(([o, a]) => mk("stop", { offset: o, "stop-color": TONE.ground, "stop-opacity": a }, og));
mk("rect", { x: 0, y: 0, width: W, height: H, style: "fill:url(#ov);stroke:none" }, svg);

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 3, cy: y0 - 2.6, r: 3, style: "fill:var(--acc)" }, svg);
mk("circle", { cx: M + 3, cy: y0 - 2.6, r: 6.5, style: "fill:none;stroke:var(--acc);stroke-width:1px;opacity:.5" }, svg);
type(svg, M + 13, y0, "BREAKING NEWS", "caps", { fill: TONE.hi, weight: 800, size: 7 });
type(svg, W - M, y0, D.date ?? "", "caps", { fill: TONE.hi, weight: 750, anchor: "end" });

// ticker + logo
const ty = 268;
logoChip(svg, M + 18, ty, 18, S.logo, S.sym);
type(svg, M + 44, ty + 2, S.sym, "label", { fill: TONE.hi, size: 15, weight: 800 });
type(svg, M + 44, ty + 14, `${S.name ?? ""}${S.tag ? " · " + S.tag : ""}`, "label", { fill: TONE.muted, size: 8.5 });

// the headline, huge
const lines = wrapText(S.headline, 30, W - 2 * M, 0.48).slice(0, 4);
lines.forEach((l, i) => type(svg, M - 1, ty + 62 + i * 33, l, "hero", { size: 30, weight: 650 }));
const hy = ty + 62 + (lines.length - 1) * 33;

// the number
if (S.hero) {
  type(svg, M, hy + 46, S.hero.label.toUpperCase(), "caps", { fill: TONE.muted, size: 6 });
  type(svg, M - 2, hy + 84, S.hero.value, "num", { size: 40, weight: 500, fill: INK });
}
type(svg, M, SAFE.bottom - 4, `Source: ${S.source} · full story on sectors.app`, "label", { fill: TONE.muted, size: 8 });
grain(0.09);
