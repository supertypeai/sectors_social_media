// Top movers, direction 1: editorial split. Winners in the top half, losers in the bottom half, each row a
// big rank, the logo and ticker, and the move large in its colour. Same language as the top-broker list.
const D = DATA, C = D.c;
setAccent("buy");
const GI = "#b2d2b9", TI = "#dc8d74";
const pct = (r) => `${r >= 0 ? "+" : "−"}${Math.abs(r * 100).toFixed(1)}%`;

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "TOP MOVERS", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, D.company, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });
// a one-sided session (85%+ of the top 100 moving the same way) says so in the headline: a crash or a rally is
// the story, the list under it is the detail
const B = C.breadth, n = C.universe || B.up + B.down || 1, red = B.down / n >= 0.85, green = B.up / n >= 0.85;
if (red || green) {
  type(svg, M, y0 + 44, red ? "A red day" : "A green day", "hero", { size: 34, weight: 500, fill: red ? TI : GI });
  typeRun(svg, M, y0 + 80, [[`${red ? B.down : B.up} of ${C.universe}`, 34, 500, TONE.hi], [red ? " fell" : " rose", 34, 500, red ? TI : GI]]);
} else {
  type(svg, M, y0 + 44, D.period === "day" ? "Today's" : "The week's", "hero", { size: 34, weight: 500 });
  typeRun(svg, M, y0 + 80, [["winners", 34, 500, GI], [" & ", 34, 500, TONE.hi], ["losers", 34, 500, TI]]);
}

// both blocks share the room between the title and the footer line, so the last row never reaches it
const t1 = y0 + 112, LAB = 22, GAP = 16, FOOT = SAFE.bottom - 26;
const RH = (FOOT - t1 - 2 * LAB - GAP) / (C.up.length + C.down.length);
function block(rows, top, ink, label) {
  type(svg, M, top, label, "caps", { fill: ink, size: 6, weight: 750 });
  rows.forEach((r, i) => {
    const cy = top + LAB - 4 + i * RH + RH / 2;
    type(svg, M, cy + 6, String(i + 1), "num", { size: 18, weight: 300, fill: TONE.faint });
    logoChip(svg, M + 34, cy, 11, r.logo, r.sym);
    type(svg, M + 54, cy - 1, r.sym, "label", { fill: TONE.hi, size: 12, weight: 700 });
    type(svg, M + 54, cy + 10, r.sector || r.name, "label", { fill: TONE.muted, size: 7 });
    type(svg, W - M, cy + 7, pct(r.ret), "num", { size: i ? 20 : 26, weight: 450, fill: ink, anchor: "end" });
    // the divider sits exactly between two rows, so each logo has air above and below it
    if (i < rows.length - 1) mk("line", { x1: M + 34, y1: cy + RH / 2, x2: W - M, y2: cy + RH / 2, class: "lo thin" }, svg);
  });
}
block(C.up, t1, GI, "WINNERS");
block(C.down, t1 + LAB + C.up.length * RH + GAP, TI, "LOSERS");
mk("line", { x1: M, y1: FOOT + 6, x2: W - M, y2: FOOT + 6, class: "lo thin" }, svg);

type(svg, M, SAFE.bottom - 4, `${C.ihsg ? `IHSG ${pct(C.ihsg.ret)} · ` : ""}${C.breadth.up} rose, ${C.breadth.down} fell of the top 100`, "label", { fill: TONE.hi, size: 9, weight: 600 });
type(svg, W - M, SAFE.bottom - 4, "sectors.app", "label", { fill: TONE.muted, size: 7.4, anchor: "end", weight: 650 });
grain(0.09);
