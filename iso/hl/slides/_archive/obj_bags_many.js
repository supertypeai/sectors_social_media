// Consumer Cyclicals · the stake as a formation of many identical shopping bags (style B, minimal, no contents).
// Kept bags solid and bright; sold bags stay in place as dashed accent ghosts (background-filled). Hook = VARIANTS[10].

/**
 * A neat iso grid of NC × NR small bags standing on the floor. Split along x: the kept bags fill the
 * left (far-x) columns, the sold ghosts the right ones, so each group reads as one block. Painted far to near.
 */
function drawBagField(parent, { S, cx, cy, floorOn = true, keep = null, lift = "ghost" } = {}) {
  const g = mk("g", {}, parent);
  const K = camera(S, [[-50, -26, 0], [50, 26, 0], [-32, -20, 46], [32, 20, 46]], cx, cy);
  const P = K.P;
  const NC = DATA.slide.gridC ?? 4, NR = DATA.slide.gridR ?? 3; // 12 bags, columns along x, rows along y
  const DX = 100 / NC, DY = 52 / NR;
  const BX = DX * 0.4, BY = Math.min(4.6, DY * 0.3), FX = BX * 0.9, FY = BY * 0.88, RIM = BX * 1.6;
  const bags = [];
  for (let i = 0; i < NC; i++) for (let j = 0; j < NR; j++) bags.push({ i, j, x: (i - (NC - 1) / 2) * DX, y: (j - (NR - 1) / 2) * DY });
  const nKeep = keep == null ? bags.length : Math.round(bags.length * keep);
  bags.forEach((b) => { b.sold = b.i * NR + b.j >= nKeep; });

  const handlePts = (x, y, yy) => {
    const N = 20, out = [], inn = [];
    for (let k = 0; k <= N; k++) {
      const a = Math.PI * (k / N);
      out.push(P(x + Math.cos(a) * BX * 0.5, y + yy, RIM - 1.2 + Math.sin(a) * BX * 0.72));
      inn.push(P(x + Math.cos(a) * BX * 0.39, y + yy, RIM - 1.2 + Math.sin(a) * BX * 0.61));
    }
    return out.concat(inn.reverse());
  };
  const solid = (b) => {
    mk("path", { d: poly(handlePts(b.x, b.y, -BY + 0.3)), class: "lo" }, g);
    const foot = rrect(b.x - FX, b.y - FY, b.x + FX, b.y + FY, 0.6, 3), mouth = rrect(b.x - BX, b.y - BY, b.x + BX, b.y + BY, 0.6, 3);
    mk("path", { d: poly(hull(ringAt(P, foot, 0).concat(ringAt(P, mouth, RIM)))), class: "sil hi" }, g);
    mk("path", { d: poly(ringAt(P, rrect(b.x - BX + 0.6, b.y - BY + 0.6, b.x + BX - 0.6, b.y + BY - 0.6, 0.4, 3), RIM)), class: "nf lo" }, g);
    mk("path", { d: poly(handlePts(b.x, b.y, BY - 0.3)), class: "hi" }, g);
  };
  const ghost = (b) => {
    const st = "stroke:var(--acc);stroke-dasharray:2 2.2;stroke-width:1px;opacity:.75";
    const foot = rrect(b.x - FX, b.y - FY, b.x + FX, b.y + FY, 0.6, 3), mouth = rrect(b.x - BX, b.y - BY, b.x + BX, b.y + BY, 0.6, 3);
    mk("path", { d: poly(hull(ringAt(P, foot, 0).concat(ringAt(P, mouth, RIM)))), class: "sil", style: st }, g);
    mk("path", { d: poly(handlePts(b.x, b.y, BY - 0.3)), class: "nf", style: st }, g);
  };

  if (floorOn) floor(g, K, -80, -50, 80, 50, 8);
  // painter: far (small x+y) to near
  bags.slice().sort((a, b) => a.x + a.y - (b.x + b.y) || a.x - b.x).forEach((b) => (b.sold && lift === "ghost" ? ghost : solid)(b));

  const cen = (arr) => arr.length ? [arr.reduce((s, b) => s + b.x, 0) / arr.length, arr.reduce((s, b) => s + b.y, 0) / arr.length] : [0, 0];
  const kept = bags.filter((b) => !b.sold), sold = bags.filter((b) => b.sold);
  const kc = cen(kept), sc = cen(sold.length ? sold : kept);
  g.K = K;
  g.N = bags.length;
  g.anchor = { load: [0, 0, RIM + 6], base: [0, (NR - 1) / 2 * DY + FY, 0], kept: [kc[0], kc[1], RIM + 2], sold: [sc[0], sc[1], RIM + 2] };
  return g;
}

// ---------------------------------------------------------------- the hook (VARIANTS[10] layout)
const D = DATA, S = D.slide;
setAccent(D.direction);
const stat = (g, x, yy, k, v, accent = false) => {
  type(g, x, yy, k, "caps", { fill: TONE.faint, size: 5.6 });
  type(g, x, yy + 18, v, "num", { size: 19, weight: 280, fill: accent ? "var(--acc)" : TONE.hi });
};
frame(D);
para(svg, M, 74, `Why would ${S.holder} sell 30% of Bayan in a single day?`, "title", { accent: ["30%"], maxW: W - 2 * M });
const field = drawBagField(svg, { S: 2.2, cx: 182, cy: 266, keep: S.keepOverride ?? S.after / S.before, lift: "ghost" });
const P = field.K.P;
leader(svg, P(...field.anchor.sold), [W - M - 64, 160], [[`${S.sold.pct.toFixed(1)}% sold`, "label", { fill: "var(--acc)", weight: 700, size: 12 }], [S.day, "label", { fill: TONE.muted, size: 7 }]], { cls: "dash nf acc" });
leader(svg, P(...field.anchor.kept), [M + 64, 352], [[`${S.after.toFixed(2)}% kept`, "label", { fill: TONE.hi, weight: 650, size: 11 }], ["what's left", "label", { fill: TONE.muted, size: 6.8 }]], { anchor: "end" });
const st = mk("g", {}, svg), Y = H - 66;
mk("line", { x1: M, y1: Y - 12, x2: W - M, y2: Y - 12, class: "lo thin" }, st);
stat(st, M, Y, "STAKE BEFORE", `${S.before.toFixed(2)}%`);
stat(st, M + 108, Y, "STAKE AFTER", `${S.after.toFixed(2)}%`);
stat(st, M + 214, Y, `VALUE · ${S.day.toUpperCase()}`, S.value, true);
