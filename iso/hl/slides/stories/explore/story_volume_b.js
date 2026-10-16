// Volume spike story, direction B: chart-led. The month of daily volume IS the frame: solid bars rising from
// the bottom edge, the spike one tall accent bar running almost to the top, with the multiple sitting on it.
const D = DATA, L = D.lead, up = D.dir === "buy";
setAccent(D.dir);
const INK = up ? "#b2d2b9" : "#dc8d74", FILL = up ? "#81a789" : "#c07159";

const y0 = SAFE.top + 8;
// the chart, full width and nearly full height; the bars come up from the bottom bleed
const bars = L.bars, B = { x0: 0, x1: W, y0: y0 + 112, y1: SAFE.bottom - 34 };
const max = Math.max(...bars.map((b) => b.v)), bw = (B.x1 - B.x0) / bars.length;
const ys = scale(0, max, B.y1, B.y0);
glow(W - bw / 2, B.y0 + 60, 120, 260, 0.25);
bars.forEach((b, i) => {
  const last = i === bars.length - 1, x = B.x0 + i * bw + 1.2, top = ys(b.v);
  mk("rect", { x, y: top, width: bw - 2.4, height: B.y1 - top + 4, rx: 1.5,
    style: last ? `fill:${FILL};stroke:none` : `fill:${TONE.hi};fill-opacity:${0.07 + 0.1 * (b.v / max)};stroke:none` }, svg);
});
// a soft floor so the bottom UI (reply field) sits on dark
const fl = mk("linearGradient", { id: "floorfade", x1: 0, y1: 0, x2: 0, y2: 1 }, mk("defs", {}, svg));
mk("stop", { offset: 0, "stop-color": TONE.ground, "stop-opacity": 0 }, fl);
mk("stop", { offset: 1, "stop-color": TONE.ground, "stop-opacity": 0.95 }, fl);
mk("rect", { x: 0, y: B.y1 - 20, width: W, height: H - B.y1 + 20, style: "fill:url(#floorfade);stroke:none" }, svg);
mk("line", { x1: 0, y1: B.y1, x2: W, y2: B.y1, class: "lo thin" }, svg);

// the normal day, a dashed line low across the bars
const my = ys(L.median);
mk("line", { x1: 0, y1: my, x2: W, y2: my, style: `stroke:${TONE.hi};stroke-width:.8px;stroke-dasharray:2 3;opacity:.75` }, svg);
type(svg, M, my - 5, `normal day · ${L.medianTxt} shares`, "label", { fill: TONE.hi, size: 7.4 });

// the multiple, sitting on top of the spike bar
// set beside the spike bar (to its left), level with its upper half
const sx = W - bw - 8, sy = ys(L.volume) + 120;
typeRun(svg, sx, sy, [[L.ratioTxt, 120, 500, INK], ["×", 52, 400, INK]], { anchor: "end" });
type(svg, sx, sy + 20, `${L.volumeTxt} shares today`, "label", { fill: TONE.hi, size: 9, weight: 650, anchor: "end" });

// top: kicker, then the company large
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "VOLUME SPIKE", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, D.company, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });
logoChip(svg, M + 20, y0 + 42, 20, L.logo, L.sym);
type(svg, M + 50, y0 + 47, L.sym, "hero", { size: 34, weight: 650 });
type(svg, M + 50, y0 + 61, L.name, "label", { fill: TONE.muted, size: 8.5 });

type(svg, M, SAFE.bottom - 14, `Price ${L.chgTxt} that day · busiest in ${L.rareHead}`, "label", { fill: TONE.hi, size: 9, weight: 600 });
type(svg, W - M, SAFE.bottom - 14, "sectors.app", "label", { fill: TONE.muted, size: 7.4, anchor: "end", weight: 650 });
grain(0.09);
