// Earnings (object direction), slide 5: three facts and the question, beside one coin stamped with the logo.
// DATA.slide: { sym, name, logo, up, facts: [{value, label, accent}], question, cta }
const D = DATA, S = D.slide;
setAccent(D.direction);
const INK = S.up ? "#b2d2b9" : "#dc8d74";
dotField(0, 0, W, H, { fx: W * 0.75, fy: 150, reach: 220, op: 0.22 });
frame(D);

logoChip(svg, M + 15, 66, 15, S.logo, S.sym);
type(svg, M + 37, 70, S.sym, "label", { fill: TONE.hi, size: 14, weight: 800 });
type(svg, M + 37, 80, S.name, "label", { fill: TONE.muted, size: 7.4 });
type(svg, M, 116, "The short version", "caps", { fill: TONE.muted, size: 7, weight: 750 });

// the coin: a short stack with the logo on top, at the right of the facts
{ const cx = W - M - 52, by = 240, r = 40, t = 7, n = 3, ry = r * 0.5;
  glow(cx, by - 30, 90, 60, 0.12);
  for (let i = 0; i < n; i++) {
    const b = by - i * t, ty = b - t, last = i === n - 1;
    mk("path", { d: `M${cx - r} ${ty}L${cx - r} ${b}A${r} ${ry} 0 0 0 ${cx + r} ${b}L${cx + r} ${ty}Z`, style: `fill:${TONE.ground};stroke:${last ? "var(--acc)" : TONE.edge};stroke-width:1px` }, svg);
    mk("ellipse", { cx, cy: ty, rx: r, ry, style: `fill:${TONE.ground};stroke:${last ? "var(--acc)" : TONE.edge};stroke-width:1px` }, svg);
  }
  const ty = by - n * t;
  mk("ellipse", { cx, cy: ty, rx: r * 0.78, ry: ry * 0.78, style: `fill:none;stroke:var(--acc);stroke-width:.6px;opacity:.6` }, svg);
  // the logo, squashed onto the coin's face
  const gg = mk("g", { transform: `translate(${cx} ${ty}) scale(1 0.5) translate(${-cx} ${-ty})` }, svg);
  logoChip(gg, cx, ty, r * 0.55, S.logo, S.sym); }

let y = 160;
S.facts.forEach((f, i) => {
  type(svg, M, y, f.value, "num", { size: i === 0 ? 40 : 28, weight: f.accent ? 620 : 380, fill: f.accent ? INK : TONE.hi });
  type(svg, M, y + 13, f.label.toUpperCase(), "caps", { fill: f.accent ? INK : TONE.muted, size: 6.4, weight: 700 });
  mk("line", { x1: M, y1: y + 23, x2: i === 0 ? W - M : 220, y2: y + 23, class: "lo thin" }, svg);
  y += i === 0 ? 62 : 52;
});

const qy = para(svg, M, 340, S.question, "title", { size: 18, maxW: W - 2 * M });
type(svg, M, Math.max(qy + 26, 392), S.cta, "label", { fill: INK, size: 8, weight: 650 });
grain(0.08);
