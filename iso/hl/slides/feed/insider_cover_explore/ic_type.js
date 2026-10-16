// Insider cover, approach 1 — editorial typography: the stake itself is the illustration. The old stake struck
// through, the move as one huge cut numeral, the stake left after it; the holder's name as the masthead line.
// DATA.slide: the vp_cover payload from image_generator/insider_v_people.build().
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);
grain(0.05);

const pc = (v) => (v < 0.005 ? "0%" : (v >= 10 ? v.toFixed(1) : v.toFixed(2)).replace(/\.?0+$/, "") + "%");
const moved = Math.abs(S.after - S.before);
const big = pc(moved).slice(0, -1);
const verb = S.other ? "took" : S.sell ? (S.after < 0.005 ? "sold all" : "sold") : "bought";

// ---------------------------------------------------------------- masthead: who
type(svg, M, 64, S.other ? "The buyer" : S.sell ? "The seller" : "The buyer", "caps", { fill: "var(--acc)", weight: 750 });
let size = 30, lines;
for (; size > 18; size -= 1) { lines = wrapText(S.holder.name, size, W - 2 * M, 0.5); if (lines.length <= 2) break; }
let y = 64 + size * 1.02;
for (const l of lines) { type(svg, M - 1, y, l, "hero", { size, weight: 380 }); y += size * 1.0; }

// ---------------------------------------------------------------- the old stake, struck through
y += 22;
type(svg, M, y, "held", "caps", { fill: TONE.faint });
const old = type(svg, M + 52, y + 1, pc(S.before), "num", { size: 20, weight: 300, fill: TONE.muted });
const ob = old.getBBox();
mk("line", { x1: ob.x - 2, y1: ob.y + ob.height * 0.55, x2: ob.x + ob.width + 2, y2: ob.y + ob.height * 0.55, class: "acc", style: "stroke-width:1.6px" }, svg);

// ---------------------------------------------------------------- the move: one huge numeral, cut in two
type(svg, M, y + 26, verb, "caps", { fill: "var(--acc)", size: 8, weight: 750 });
const ny = y + 140, nsize = 140;
const ng = mk("g", {}, svg);
const numText = (g, dx) => typeRun(g, M - 6 + dx, ny, [[big, nsize, 220, "var(--acc)"], ["%", nsize * 0.42, 300, "var(--acc)"]]);
const defs = mk("defs", {}, svg);
const cutY = ny - nsize * 0.36;
mk("rect", { x: 0, y: 0, width: W, height: cutY }, mk("clipPath", { id: "cutTop" }, defs));
mk("rect", { x: 0, y: cutY + 2.2, width: W, height: H }, mk("clipPath", { id: "cutBot" }, defs));
numText(mk("g", { "clip-path": "url(#cutTop)" }, ng), 0);
numText(mk("g", { "clip-path": "url(#cutBot)" }, ng), S.sell ? 5 : -5); // the slice slides the way the stake went
mk("line", { x1: M - 10, y1: cutY + 1.1, x2: W - M, y2: cutY + 1.1, style: `stroke:${TONE.hi};stroke-width:.5px;stroke-dasharray:2 2.5;opacity:.5` }, svg);

// ---------------------------------------------------------------- what is left, and from whom
let by = ny + 30;
type(svg, M, by, "holds now", "caps", { fill: TONE.faint });
typeRun(svg, M + 52, by + 1, [[pc(S.after), 20, 500, TONE.hi], [`  of ${S.name}`, 10, 450, TONE.muted]]);
if (S.other) {
  by += 22;
  type(svg, M, by, "from", "caps", { fill: TONE.faint });
  typeRun(svg, M + 52, by + 1, [[S.other.name, 10, 600, TONE.hi], [`  ${pc(S.otherBefore)} → ${pc(S.otherAfter)}`, 10, 450, TONE.muted]]);
}

// ---------------------------------------------------------------- byline
const ly = 398;
mk("line", { x1: M, y1: ly - 16, x2: W - M, y2: ly - 16, class: "lo thin" }, svg);
typeRun(svg, M, ly, [[S.value, 13, 450, "var(--acc)"], ["  deal value", 7.5, 500, TONE.muted]]);
type(svg, W - M, ly, `${S.span} ${S.year}`, "label", { size: 7.5, fill: TONE.muted, anchor: "end" });
