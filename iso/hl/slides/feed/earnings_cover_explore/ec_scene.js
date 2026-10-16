// Earnings cover, approach 4: one calm hairline scene of the industry (a mine cart for coal and mining names;
// the flame mark otherwise). The load is the profit: last year's share stays in the tub, the change lifts off.
// DATA.slide: eo_cover data + sector
const D = DATA, S = D.slide;
setAccent(D.direction);
const up = S.up, INK = up ? "#b2d2b9" : "#dc8d74";
dotField(0, 0, W, H, { fx: W * 0.5, fy: 320, reach: 240, op: 0.22 });
frame(D);

logoChip(svg, M + 15, 66, 15, S.logo, S.sym);
type(svg, M + 37, 70, S.sym, "label", { fill: TONE.hi, size: 14, weight: 800 });
type(svg, M + 37, 80, S.name, "label", { fill: TONE.muted, size: 7.4 });

type(svg, M - 3, 150, S.hero, "hero", { size: 66, weight: 650, fill: INK });
type(svg, M, 172, S.line, "title", { size: 15, fill: TONE.hi });

const qs = S.quarters, vNow = qs[qs.length - 1].v;
const vPrev = (qs.find((q) => q.label.slice(0, 2) === qs[qs.length - 1].label.slice(0, 2) && +q.label.slice(-4) === +qs[qs.length - 1].label.slice(-4) - 1) || qs[0]).v;
const mining = /coal|mining|metal|mineral|energy|oil|heavy/i.test(S.sector || "");
glow(190, 300, 130, 70, up ? 0.12 : 0.07);
const industrial = /industrial|machin|equipment/i.test(S.sector || "");
if (mining) drawMineCart(svg, { S: 2.05, cx: 186, cy: 322, keep: up ? vPrev / vNow : vNow / vPrev, lift: up ? 34 : 22 });
else if (industrial) drawHaulTruck(svg, { frame: "full", S: 1.5, cx: 184, cy: 318 });
else drawFlameMark(svg, { S: 1.4, cx: 186, cy: 330 });

// the reading of the scene
type(svg, M, 398, `${S.prev.label}  ${S.prev.s}`, "label", { fill: TONE.muted, size: 7.6, weight: 600 });
type(svg, W - M, 398, `${S.now.label}  ${S.now.s}`, "label", { fill: INK, size: 8.4, weight: 750, anchor: "end" });
if (mining) type(svg, W / 2, 410, up ? "bright load = last year · lifted = the new profit" : "bright load = what is left · lifted = what is gone", "label", { fill: TONE.faint, size: 6.4, anchor: "middle" });
grain(0.07);
