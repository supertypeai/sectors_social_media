// Style D, shrink: the stake before and after as two circles, area true to the percentages, sitting on
// the same baseline. The ring between them, the part that left, is the only thing in the accent.
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

let y = para(svg, M, 74, `${S.holder}'s stake in Bayan, before and after one filing`, "title", { accent: S.accent });

const RB = 92, RA = RB * Math.sqrt(S.after / S.before); // area ∝ stake
const CX = W - M - RB, BASE = 382, cyB = BASE - RB, cyA = BASE - RA;
// the sold ring: the big circle minus the small one, filled faintly in the accent
mk("path", { d: `M${CX - RB} ${cyB}a${RB} ${RB} 0 1 0 ${2 * RB} 0a${RB} ${RB} 0 1 0 ${-2 * RB} 0ZM${CX - RA} ${cyA}a${RA} ${RA} 0 1 1 ${2 * RA} 0a${RA} ${RA} 0 1 1 ${-2 * RA} 0Z`,
  style: "fill:var(--acc);fill-opacity:.16;fill-rule:evenodd;stroke:var(--acc);stroke-width:1.4px" }, svg);
mk("circle", { cx: CX, cy: cyA, r: RA, style: `fill:${TONE.ground};stroke:${TONE.hi};stroke-width:1.6px` }, svg);
mk("line", { x1: M, y1: BASE, x2: W - M, y2: BASE, class: "lo thin" }, svg);

// numbers: before at the top of the big circle, after inside the small one, the sold share on the ring
type(svg, CX, cyB - RB - 8, `${S.before.toFixed(2)}% before`, "label", { fill: TONE.muted, size: 8, anchor: "middle" });
type(svg, CX, cyA + 5, `${S.after.toFixed(2)}%`, "label", { fill: TONE.hi, size: 12, weight: 650, anchor: "middle" });
type(svg, CX, cyA + 16, "now", "label", { fill: TONE.muted, size: 6.6, anchor: "middle" });
// the hero, set left of the circle
typeRun(svg, M - 2, 250, [[`−${S.sold.pct.toFixed(1)}`, 46, 240, "var(--acc)"], ["%", 22, 260, TONE.muted]]);
type(svg, M, 266, "of the company", "label", { fill: TONE.muted, size: 8.5 });
type(svg, M, 278, `sold ${S.tradeDay}`, "label", { fill: TONE.muted, size: 8.5 });
type(svg, M, 404, S.line, "body", { fill: TONE.muted, size: 8 });
