// Volume spike, direction D: two circles, their areas true to the volumes. A normal day is a small grey disc;
// today is a big accent disc that fills the frame, the small one tucked at its edge.
const D = DATA, L = D.lead, up = D.dir === "buy";
setAccent(D.dir);
const INK = up ? "#b2d2b9" : "#dc8d74", FILL = up ? "#81a789" : "#c07159";

const y0 = SAFE.top + 8;
// today's disc: as large as the frame allows; the normal disc's area is 1/ratio of it
const R = 128, r = R / Math.sqrt(L.ratio), cx = W - M - R + 6, cy = 330;
glow(cx, cy, R * 1.5, R * 1.5, 0.22);
mk("circle", { cx, cy, r: R, style: `fill:${FILL};fill-opacity:.22;stroke:${FILL};stroke-width:1.4px` }, svg);
mk("circle", { cx, cy, r: R * 0.995, style: `fill:none;stroke:${INK};stroke-width:.6px;stroke-dasharray:1.5 3;opacity:.6` }, svg);
const nx = Math.max(M + r + 4, cx - R - r - 10), ny = cy + R - r;
mk("circle", { cx: nx, cy: ny, r, style: `fill:${TONE.mid};stroke:${TONE.edge};stroke-width:.8px` }, svg);
type(svg, nx, ny + r + 14, "a normal day", "label", { fill: TONE.muted, size: 8, anchor: "middle" });
type(svg, nx, ny + r + 25, L.medianTxt, "label", { fill: TONE.faint, size: 7, anchor: "middle" });

// inside today's disc: the multiple and the volume
typeRun(svg, cx, cy + 22, [[L.ratioTxt, 110, 500, INK], ["×", 46, 400, INK]], { anchor: "middle" });
type(svg, cx, cy + 50, `${L.volumeTxt} shares today`, "label", { fill: TONE.hi, size: 10, weight: 650, anchor: "middle" });

mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "VOLUME SPIKE", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, D.company, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });
logoChip(svg, M + 20, y0 + 42, 20, L.logo, L.sym);
type(svg, M + 50, y0 + 47, L.sym, "hero", { size: 34, weight: 650 });
type(svg, M + 50, y0 + 61, L.name, "label", { fill: TONE.muted, size: 8.5 });

type(svg, M, SAFE.bottom - 4, `Price ${L.chgTxt} that day · busiest in ${L.rareHead}`, "label", { fill: TONE.hi, size: 9, weight: 600 });
type(svg, W - M, SAFE.bottom - 4, "sectors.app", "label", { fill: TONE.muted, size: 7.4, anchor: "end", weight: 650 });
grain(0.09);
