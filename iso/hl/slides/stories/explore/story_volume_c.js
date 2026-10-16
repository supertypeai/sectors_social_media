// Volume spike, direction C: "one day = 17 normal days". A normal day is one block; today is drawn as a tower
// of 17 such blocks stacked beside it. The count IS the chart.
const D = DATA, L = D.lead, up = D.dir === "buy";
setAccent(D.dir);
const INK = up ? "#b2d2b9" : "#dc8d74", FILL = up ? "#81a789" : "#c07159";
dotField(0, 0, W, H, { fx: W * 0.6, fy: 330, reach: 320, op: 0.3 });

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "VOLUME SPIKE", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, D.company, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });
logoChip(svg, M + 20, y0 + 42, 20, L.logo, L.sym);
type(svg, M + 50, y0 + 47, L.sym, "hero", { size: 34, weight: 650 });
type(svg, M + 50, y0 + 61, L.name, "label", { fill: TONE.muted, size: 8.5 });

// the headline
typeRun(svg, M, y0 + 112, [["1 day", 30, 600, TONE.hi], [" = ", 30, 300, TONE.muted], [`${L.ratioTxt} normal days`, 30, 600, INK]]);
type(svg, M, y0 + 132, `of trading, all at once · ${L.volumeTxt} shares`, "label", { fill: TONE.muted, size: 9 });

// the towers: a normal day (1 block) and today (N blocks), bottom-aligned
const n = Math.round(L.ratio), base = SAFE.bottom - 52, room = base - (y0 + 160);
const bh = Math.min(16, (room - (n - 1) * 3) / n), gap = Math.min(3, bh * 0.2), bw = 92;
const block = (x, y, fill, op = 1) => mk("rect", { x, y, width: bw, height: bh, rx: 2.2, style: `fill:${fill};fill-opacity:${op};stroke:none` }, svg);
const xN = M + 26, xT = W - M - bw - 26;
block(xN, base - bh, TONE.mid);
type(svg, xN + bw / 2, base + 16, "a normal day", "label", { fill: TONE.muted, size: 8, anchor: "middle" });
type(svg, xN + bw / 2, base + 27, `${L.medianTxt} shares`, "label", { fill: TONE.faint, size: 7, anchor: "middle" });
for (let i = 0; i < n; i++) block(xT, base - (i + 1) * bh - i * gap, FILL, 0.55 + 0.45 * (i / n));
type(svg, xT + bw / 2, base + 16, "today", "label", { fill: INK, size: 8, weight: 650, anchor: "middle" });
type(svg, xT + bw / 2, base + 27, `${L.volumeTxt} shares`, "label", { fill: TONE.faint, size: 7, anchor: "middle" });
// count ticks beside today's tower
const topT = base - n * bh - (n - 1) * gap;
type(svg, xT - 10, topT + 14, `${n}×`, "num", { size: 40, weight: 500, fill: INK, anchor: "end" });
mk("line", { x1: M, y1: base, x2: W - M, y2: base, class: "lo thin" }, svg);

type(svg, M, SAFE.bottom - 4, `Price ${L.chgTxt} that day · busiest in ${L.rareHead}`, "label", { fill: TONE.hi, size: 9, weight: 600 });
type(svg, W - M, SAFE.bottom - 4, "sectors.app", "label", { fill: TONE.muted, size: 7.4, anchor: "end", weight: 650 });
grain(0.09);
