// Volume spike, direction F: the month as a dial. Each trading day is a radial bar around a circle, like a
// clock face read clockwise from the top; today's bar shoots out far past the ring in the accent.
const D = DATA, L = D.lead, up = D.dir === "buy";
setAccent(D.dir);
const INK = up ? "#b2d2b9" : "#dc8d74", FILL = up ? "#81a789" : "#c07159";

const y0 = SAFE.top + 8, cx = W / 2, cy = 338, R0 = 62, R1 = 172;
const bars = L.bars, n = bars.length, vmax = Math.max(...bars.map((b) => b.v));
// square-root scale so the quiet days still show as a texture
const len = (v) => (R1 - R0) * Math.sqrt(v / vmax);
// cap others so the quiet days read as a ring of texture, not lost lines
glow(cx, cy, 190, 190, 0.16);
mk("circle", { cx, cy, r: R0 + len(L.median), style: `fill:none;stroke:${TONE.hi};stroke-width:.7px;stroke-dasharray:1.5 3;opacity:.6` }, svg);
bars.forEach((b, i) => {
  // clockwise from just past twelve o'clock, so today lands at twelve and points straight up
  const a = -Math.PI / 2 + ((i + 1) / n) * Math.PI * 2, last = i === n - 1;
  const r2 = Math.min(R0 + len(b.v), last ? R1 : R1 * 0.82), w = last ? 7 : 5;
  const [c, s] = [Math.cos(a), Math.sin(a)];
  mk("line", { x1: cx + R0 * c, y1: cy + R0 * s, x2: cx + r2 * c, y2: cy + r2 * s,
    style: `stroke:${last ? FILL : TONE.mid};stroke-width:${w}px;stroke-linecap:round` }, svg);
  if (last) glowDot(svg, cx + r2 * c, cy + r2 * s, FILL, 4.5);
});
// the centre: the multiple
typeRun(svg, cx, cy + 14, [[L.ratioTxt, 52, 500, INK], ["×", 22, 400, INK]], { anchor: "middle" });
type(svg, cx, cy + 30, "normal volume", "label", { fill: TONE.muted, size: 8, anchor: "middle" });
type(svg, cx, cy - R1 - 12, "TODAY", "caps", { fill: INK, size: 6, anchor: "middle" });

mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "VOLUME SPIKE", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, D.company, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });
logoChip(svg, M + 20, y0 + 42, 20, L.logo, L.sym);
type(svg, M + 50, y0 + 47, L.sym, "hero", { size: 34, weight: 650 });
type(svg, M + 50, y0 + 61, L.name, "label", { fill: TONE.muted, size: 8.5 });

type(svg, M, SAFE.bottom - 4, `${L.volumeTxt} shares · price ${L.chgTxt} · busiest in ${L.rareHead}`, "label", { fill: TONE.hi, size: 9, weight: 600 });
type(svg, W - M, SAFE.bottom - 4, "sectors.app", "label", { fill: TONE.muted, size: 7.4, anchor: "end", weight: 650 });
grain(0.09);
