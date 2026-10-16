// Earnings cover, approach 3: brand-led. The company's logo becomes a halftone poster; last year's logo and
// this year's are printed at area-true sizes, so the brand itself grows (or shrinks) by the profit change.
// DATA.slide: eo_cover data + ink (n x n, 0..1 per cell, from the logo)
const D = DATA, S = D.slide;
setAccent(D.direction);
const up = S.up, INK = up ? "#b2d2b9" : "#dc8d74";
frame(D);

type(svg, M - 3, 104, S.hero, "hero", { size: 66, weight: 650, fill: INK });
type(svg, M, 126, S.line, "title", { size: 15, fill: TONE.hi });
type(svg, M, 140, `${S.sym} · ${S.name}`, "label", { fill: TONE.muted, size: 8 });

const qs = S.quarters, vNow = qs[qs.length - 1].v;
const vPrev = (qs.find((q) => q.label.slice(0, 2) === qs[qs.length - 1].label.slice(0, 2) && +q.label.slice(-4) === +qs[qs.length - 1].label.slice(-4) - 1) || qs[0]).v;
const ink = S.ink || [[1]], n = ink.length;
const k = Math.sqrt(Math.min(vNow, vPrev) / Math.max(vNow, vPrev));

/** The logo as dots in a box of side `size`, bottom-left at (x, by). */
function half(x, by, size, fill, op = 1) {
  const g = mk("g", { opacity: op }, svg), c = size / n;
  for (let r = 0; r < n; r++) for (let q = 0; q < n; q++) {
    const v = ink[r][q];
    if (v < 0.06) continue;
    mk("circle", { cx: x + (q + 0.5) * c, cy: by - size + (r + 0.5) * c, r: (c * 0.52 * Math.sqrt(v)).toFixed(2), style: `fill:${fill};stroke:none` }, g);
  }
}
const BIG = 200, base = 392;
const sPrev = up ? BIG * k : BIG, sNow = up ? BIG : BIG * k;
const xNow = W - M - sNow;
if (up) {
  half(M, base, sPrev, TONE.edge, 0.85);
  half(xNow, base, sNow, INK);
} else {
  half(W - M - sPrev, base, sPrev, TONE.edge, 0.45); // last year, dimmed
  half(M, base, sNow, INK);                           // what is left, beside it
}
mk("line", { x1: M, y1: base + 8, x2: W - M, y2: base + 8, class: "lo thin" }, svg);
const left = up ? S.prev : S.now, right = up ? S.now : S.prev;
type(svg, M, base + 20, `${left.label} · ${left.s}`, "label", { fill: up ? TONE.muted : INK, size: up ? 7.2 : 8, weight: up ? 600 : 750 });
type(svg, W - M, base + 20, `${right.label} · ${right.s}`, "label", { fill: up ? INK : TONE.muted, size: up ? 8 : 7.2, weight: up ? 750 : 600, anchor: "end" });
grain(0.07);
