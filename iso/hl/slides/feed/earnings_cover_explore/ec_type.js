// Earnings cover, approach 1: typography is the illustration. Last year's profit and this year's are set at
// type sizes whose AREA is true to the money, so the size jump is the chart; the multiple sits between them.
// DATA.slide: eo_cover data (sym, name, logo, up, hero, line, prev {label, s}, now {label, s}, quarters)
const D = DATA, S = D.slide;
setAccent(D.direction);
const up = S.up, INK = up ? "#b2d2b9" : "#dc8d74";
frame(D);

logoChip(svg, M + 15, 66, 15, S.logo, S.sym);
type(svg, M + 37, 70, S.sym, "label", { fill: TONE.hi, size: 14, weight: 800 });
type(svg, M + 37, 80, S.name, "label", { fill: TONE.muted, size: 7.4 });

const qs = S.quarters, vNow = qs[qs.length - 1].v;
const vPrev = (qs.find((q) => q.label.slice(0, 2) === qs[qs.length - 1].label.slice(0, 2) && +q.label.slice(-4) === +qs[qs.length - 1].label.slice(-4) - 1) || qs[0]).v;
const BIG = 78, k = Math.sqrt(Math.min(vNow, vPrev) / Math.max(vNow, vPrev));
const sPrev = up ? BIG * k : BIG, sNow = up ? BIG : BIG * k;

// split "Rp 1.8 T" so the unit is lighter than the figure
const parts = (s, size, fill, w) => {
  const [rp, n, u] = s.split(" ");
  return [[`${rp} `, size * 0.42, 400, TONE.muted], [n, size, w, fill], [` ${u ?? ""}`, size * 0.5, 450, fill]];
};

// the hook: the multiple, then the plain sentence
type(svg, M - 3, 150, S.hero, "hero", { size: 66, weight: 650, fill: INK });
type(svg, M, 172, S.line, "title", { size: 15, fill: TONE.hi });

// the two numbers on a shared left edge, a year apart
const y1 = 236 + sPrev * 0.72, y2 = y1 + 26 + sNow * 0.72;
type(svg, M, y1 - sPrev * 0.72 - 6, S.prev.label.toUpperCase(), "caps", { fill: TONE.muted, size: 6.6, weight: 750 });
typeRun(svg, M - 1, y1, parts(S.prev.s, sPrev, up ? TONE.edge : TONE.hi, up ? 400 : 500));
mk("line", { x1: M, y1: y1 + 9, x2: W - M, y2: y1 + 9, class: "lo thin" }, svg);
type(svg, M, y1 + 22, S.now.label.toUpperCase(), "caps", { fill: INK, size: 6.6, weight: 750 });
typeRun(svg, M - 1, y2 + 6, parts(S.now.s, sNow, INK, 650));
type(svg, W - M, H - 44, "type area = net profit", "label", { fill: TONE.faint, size: 6.4, anchor: "end" });
grain(0.07);
