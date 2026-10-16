// Top broker story, direction C: tug of war. The week's biggest net buyer (top half, green) against its
// biggest net seller (bottom half, terracotta): each with its code, the net huge, and the stocks it leaned on.
const D = DATA, Bu = D.buyer, Se = D.seller;
setAccent("buy");
const G = "#81a789", T = "#c07159", GI = "#b2d2b9", TI = "#dc8d74";

const y0 = SAFE.top + 8, mid = (y0 + SAFE.bottom) / 2 + 6;
glow(W * 0.8, y0 + 120, 200, 140, 0.18);
const tg = mk("radialGradient", { id: "tglow" }, mk("defs", {}, svg));
mk("stop", { offset: 0, "stop-color": T, "stop-opacity": 0.18 }, tg);
mk("stop", { offset: 1, "stop-color": T, "stop-opacity": 0 }, tg);
mk("ellipse", { cx: W * 0.8, cy: mid + 130, rx: 200, ry: 140, style: "fill:url(#tglow);stroke:none" }, svg);

mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "BROKER TUG OF WAR", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, D.company, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });

function half(S, top, fill, ink, label) {
  type(svg, M, top, label, "caps", { fill: ink, size: 6, weight: 750 });
  logoChip(svg, M + 21, top + 32, 21, S.logo, S.code);
  type(svg, M + 52, top + 30, S.name, "label", { fill: TONE.hi, size: 15, weight: 650 });
  type(svg, M + 52, top + 45, `${S.code} · ${S.foreign ? "foreign" : "local"} · ${S.gross_s} traded`, "label", { fill: TONE.muted, size: 8 });
  type(svg, M - 2, top + 110, S.net_s, "num", { size: 52, weight: 500, fill: ink });
  let x = M;
  for (const s of S.stocks) {
    logoChip(svg, x + 11, top + 140, 11, s.logo, s.sym);
    type(svg, x + 27, top + 138, s.sym, "label", { fill: TONE.hi, size: 9.5, weight: 700 });
    type(svg, x + 27, top + 149, s.s, "label", { fill: ink, size: 7, weight: 600 });
    x += 100;
  }
}
half(Bu, y0 + 32, G, GI, "BIGGEST NET BUYER");
// the rope: a divider with "vs"
mk("line", { x1: M, y1: mid, x2: W - M, y2: mid, style: `stroke:${TONE.mid};stroke-width:1px` }, svg);
mk("circle", { cx: W / 2, cy: mid, r: 13, style: `fill:${TONE.ground};stroke:${TONE.mid};stroke-width:1px` }, svg);
type(svg, W / 2, mid + 3.5, "vs", "label", { fill: TONE.hi, size: 10, weight: 650, anchor: "middle" });
half(Se, mid + 26, T, TI, "BIGGEST NET SELLER");

type(svg, M, SAFE.bottom - 4, "Which side are you on?", "label", { fill: TONE.hi, size: 9, weight: 600 });
type(svg, W - M, SAFE.bottom - 4, "sectors.app", "label", { fill: TONE.muted, size: 7.4, anchor: "end", weight: 650 });
grain(0.09);
