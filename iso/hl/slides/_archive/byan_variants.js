// Five hook variants for one insider move (BYAN), each combining two of: the company's hairline mark,
// a chart, a sector object. DATA.slide.variant picks 1–5. Every number comes from DATA.slide.
const D = DATA, S = D.slide;
setAccent(D.direction);
const num = (v) => Number(v).toLocaleString("en-US");

/** A weekly-close line chart in `box`; returns helpers. fromZero puts Rp 0 on the baseline. */
function priceChart(parent, box, { fromZero = false, extra = [], fill = true } = {}) {
  const g = mk("g", {}, parent);
  const px = weekly(S.prices.map((p) => [dayOf(p.date), p.close]));
  const t0 = px[0][0], t1 = px.at(-1)[0], vals = px.map((p) => p[1]).concat(extra);
  const lo = fromZero ? 0 : Math.min(...vals), hi = Math.max(...vals), pad = (hi - lo) * 0.14;
  const xs = scale(t0, t1, box.x0, box.x1), ys = scale(fromZero ? 0 : lo - pad, hi + pad, box.y1, box.y0);
  const pts = px.map(([t, v]) => [xs(t), ys(v)]), line = smoothPath(pts);
  if (fill) {
    const id = `pf${Math.random().toString(36).slice(2, 7)}`, lg = mk("linearGradient", { id, x1: 0, y1: 0, x2: 0, y2: 1 }, mk("defs", {}, g));
    mk("stop", { offset: 0, "stop-color": TONE.hi, "stop-opacity": 0.1 }, lg);
    mk("stop", { offset: 1, "stop-color": TONE.hi, "stop-opacity": 0 }, lg);
    mk("path", { d: `${line}L${pts.at(-1)[0]} ${box.y1}L${pts[0][0]} ${box.y1}Z`, style: `fill:url(#${id});stroke:none` }, g);
  }
  mk("line", { x1: box.x0, y1: box.y1, x2: box.x1, y2: box.y1, class: "lo thin" }, g);
  mk("path", { d: line, class: "nf", style: `stroke:${TONE.hi};stroke-width:1.7px` }, g);
  const at = (t) => {
    const i = px.findIndex(([tt]) => tt >= t);
    if (i <= 0) return pts[0][1];
    const [ta] = px[i - 1], [tb] = px[i];
    return pts[i - 1][1] + ((t - ta) / (tb - ta)) * (pts[i][1] - pts[i - 1][1]);
  };
  return { g, px, pts, xs, ys, at, saleX: xs(dayOf(S.saleDate)), saleY: at(dayOf(S.saleDate)) };
}
const saleDot = (g, x, y) => {
  mk("circle", { cx: x, cy: y, r: 9, style: "fill:var(--acc);fill-opacity:.18;stroke:none" }, g);
  mk("circle", { cx: x, cy: y, r: 3.6, style: `fill:var(--acc);stroke:${TONE.ground};stroke-width:1.5px` }, g);
};
const stat = (g, x, yy, k, v, accent = false) => {
  type(g, x, yy, k, "caps", { fill: TONE.faint, size: 5.6 });
  type(g, x, yy + 18, v, "num", { size: 19, weight: 280, fill: accent ? "var(--acc)" : TONE.hi });
};

const VARIANTS = {
  // 1 · The question: a question as the headline, the object big, three facts as a strip
  1() {
    frame(D);
    para(svg, M, 74, `Why would ${S.holder} sell 30% of Bayan in a single day?`, "title", { accent: ["30%"], maxW: W - 2 * M });
    const cart = drawMineCart(svg, { S: 2.15, cx: 182, cy: 262 });
    leader(svg, cart.K.P(10, 6, 44), [W - M - 52, 150], [[`${S.sold.pct.toFixed(1)}%`, "label", { fill: "var(--acc)", weight: 700, size: 12 }], ["sold", "label", { fill: TONE.muted, size: 7 }]], { cls: "dash nf acc" });
    const g = mk("g", {}, svg), Y = H - 76;
    mk("line", { x1: M, y1: Y - 12, x2: W - M, y2: Y - 12, class: "lo thin" }, g);
    stat(g, M, Y, "STAKE BEFORE", `${S.before.toFixed(2)}%`);
    stat(g, M + 108, Y, "STAKE AFTER", `${S.after.toFixed(2)}%`);
    stat(g, M + 214, Y, `VALUE · ${S.day.toUpperCase()}`, S.value, true);
  },

  // 2 · The chart: the price chart is the picture, the mark behind it; the number sits below like a caption
  2() {
    drawFlameMark(mk("g", { opacity: 0.1 }, svg), { S: 2.6, cx: 200, cy: 190, dropCls: "sil", floorOn: false });
    frame(D);
    type(svg, M, 62, "BYAN · WEEKLY CLOSE SINCE APRIL", "caps", { fill: TONE.faint, size: 5.6 });
    const c = priceChart(svg, { x0: M, x1: W - M, y0: 84, y1: 262 });
    mk("line", { x1: c.saleX, y1: 80, x2: c.saleX, y2: 262, style: "stroke:var(--acc);stroke-dasharray:2 3;stroke-width:1px" }, c.g);
    saleDot(c.g, c.saleX, c.saleY);
    type(c.g, c.saleX - 7, 92, `sold ${S.day}`, "label", { fill: "var(--acc)", size: 8, weight: 700, anchor: "end" });
    typeRun(svg, M - 3, 350, [[S.hero.num, 84, 220, "var(--acc)"], [S.hero.unit, 34, 250, TONE.muted]]);
    // how long after the peak the sale came, from the same weekly series
    const pkI = c.px.reduce((b, p, i) => (p[1] > c.px[b][1] ? i : b), 0);
    const wks = Math.round((dayOf(S.saleDate) - c.px[pkI][0]) / (7 * 864e5));
    para(svg, M, 378, `of Bayan sold by ${S.holder}, ${wks} weeks after the stock's peak`, "body", { maxW: W - 2 * M, fill: TONE.hi, lh: 1.3 });
  },

  // 3 · The cut: hero number, the object, and one bar that is the whole company with the slice cut out
  3() {
    frame(D);
    typeRun(svg, M - 3, 110, [[S.hero.num, 74, 220], [S.hero.unit, 30, 250, TONE.muted]]);
    para(svg, M, 136, `of Bayan, sold by ${S.holder} in one filing`, "title", { accent: [] });
    drawMineCart(svg, { S: 1.5, cx: 180, cy: 254 });
    const g = mk("g", {}, svg), Y = 352, X0 = M, X1 = W - M, xo = (p) => X0 + (p / 100) * (X1 - X0);
    type(g, X1, Y - 6, "100% OF BAYAN'S SHARES", "caps", { fill: TONE.faint, size: 5.6, anchor: "end" });
    mk("rect", { x: X0, y: Y, width: X1 - X0, height: 12, rx: 6, style: `fill:${TONE.lo};stroke:none` }, g);
    mk("rect", { x: X0, y: Y, width: xo(S.after) - X0, height: 12, rx: 6, style: `fill:${TONE.hi};stroke:none` }, g);
    mk("rect", { x: xo(S.after) + 1.5, y: Y, width: xo(S.before) - xo(S.after) - 3, height: 12, rx: 3, style: "fill:var(--acc);fill-opacity:.25;stroke:var(--acc);stroke-width:1.2px;stroke-dasharray:3 2" }, g);
    type(g, X0, Y + 28, `${S.after.toFixed(2)}% kept`, "label", { size: 9, weight: 650 });
    type(g, xo(S.before), Y - 6, `${S.sold.pct.toFixed(1)}% sold · ${S.day}`, "label", { size: 9, weight: 700, fill: "var(--acc)", anchor: "end" });
    type(g, X1, Y + 28, "everyone else", "label", { size: 7.4, fill: TONE.faint, anchor: "end" });
  },

  // 4 · The money: the rupiah figure is the hook, the company's mark is the object
  4() {
    frame(D);
    typeRun(svg, M - 4, 124, [["Rp", 30, 260, TONE.muted], [` ${S.valueNum}`, 76, 220], [" T", 30, 260, TONE.muted]]);
    const y4 = para(svg, M, 154, `of Bayan sold by ${S.holder} in one day`, "title", { accent: [] });
    type(svg, M, y4 + 17, `${S.shares} · ${S.sold.pct.toFixed(1)}% of the company · ${S.day}`, "body", { fill: TONE.muted });
    drawFlameMark(svg, { S: 1.7, cx: 186, cy: 316, dropCls: "acc" });
  },

  // 5 · The price gap: the sale price drawn on the same scale as the market, far below the line
  5() {
    drawFlameMark(mk("g", { opacity: 0.09 }, svg), { S: 2.4, cx: 250, cy: 250, dropCls: "sil", floorOn: false });
    frame(D);
    para(svg, M, 74, `Sold at Rp ${num(S.salePrice)}. The market closed at Rp ${num(S.close)}.`, "title", { accent: ["Rp", num(S.salePrice) + "."].slice(1), maxW: W - 2 * M });
    type(svg, M, 132, `${S.holder} · ${S.sold.pct.toFixed(1)}% of Bayan · ${S.day}`, "body", { fill: TONE.muted });
    const c = priceChart(svg, { x0: M, x1: W - M - 6, y0: 160, y1: 384 }, { fromZero: true, extra: [S.salePrice] });
    const ys = c.ys(S.salePrice), yc = c.ys(S.close);
    mk("line", { x1: M, y1: ys, x2: W - M, y2: ys, style: "stroke:var(--acc);stroke-dasharray:4 3;stroke-width:1.3px" }, c.g);
    mk("line", { x1: c.saleX, y1: yc, x2: c.saleX, y2: ys, style: "stroke:var(--acc);stroke-width:1px;opacity:.6" }, c.g);
    saleDot(c.g, c.saleX, ys);
    mk("circle", { cx: c.saleX, cy: yc, r: 3, style: `fill:${TONE.hi};stroke:${TONE.ground};stroke-width:1.5px` }, c.g);
    const gap = Math.round((1 - S.salePrice / S.close) * 100);
    typeRun(svg, M, ys - 10, [[`−${gap}%`, 40, 240, "var(--acc)"]]);
    type(svg, M + 2, ys + 14, `sale price Rp ${num(S.salePrice)}`, "label", { fill: "var(--acc)", size: 8, weight: 650 });
    type(svg, c.saleX - 8, yc + 16, `close Rp ${num(S.close)}`, "label", { size: 8, weight: 650, anchor: "end" }); // below the line
    type(svg, W - M, 396, "Rp 0", "label", { fill: TONE.faint, size: 6.4, anchor: "end" });
  },
};
// 6 · The question + a stat object: the company as 100 coal cubes (1% each). The holder's sold stake lifts
//     off in the accent and fades as it rises; what they kept stays as bright outlines; the rest is dim.
VARIANTS[6] = function () {
  frame(D);
  para(svg, M, 74, `Why would ${S.holder} sell 30% of Bayan in a single day?`, "title", { accent: ["30%"], maxW: W - 2 * M });

  const N = 10, C = 9, GAP = 1.6, SIDE = C - GAP, HT = 6;   // grid, cell, cube size
  const sold = Math.round(S.sold.pct), kept = Math.round(S.after);
  const K = camera(1.55, [[0, 0, 0], [N * C, N * C, 0], [0, 0, 70], [N * C, N * C, HT]], 186, 252);
  const g = mk("g", {}, svg);
  floor(g, K, -20, -20, N * C + 20, N * C + 20, 8);
  { const [r, i] = rings(-4, -4, N * C + 4 - GAP, N * C + 4 - GAP, 3, 1.2); slab(g, K, r, i, 0, 3, "sil"); } // the pallet

  // which cells: the holder's stake is the far rows (sold first, then kept), everyone else nearer to us
  const cells = [];
  for (let k = 0; k < N * N; k++) {
    const i = Math.floor(k / N), j = k % N;
    cells.push({ i, j, kind: k < sold ? "sold" : k < sold + kept ? "kept" : "other" });
  }
  const hash = (k) => { const s = Math.sin(k * 12.9898) * 43758.5453; return s - Math.floor(s); };
  const cube = (c, z0, cls, op = 1) => {
    const x0 = c.j * C, y0 = c.i * C, [r, i] = rings(x0, y0, x0 + SIDE, y0 + SIDE, 1.2, 0.5);
    const el = slab(mk("g", { opacity: op }, g), K, r, i, z0, z0 + HT, cls);
    return el;
  };
  // grounded cubes, far to near; the sold cells leave an empty dashed slot
  const order = (a, b) => a.i + a.j - (b.i + b.j);
  for (const c of cells.slice().sort(order)) {
    if (c.kind === "sold") {
      const x0 = c.j * C, y0 = c.i * C;
      mk("path", { d: poly([[x0, y0], [x0 + SIDE, y0], [x0 + SIDE, y0 + SIDE], [x0, y0 + SIDE]].map(([x, y]) => K.P(x, y, 3))), class: "dash nf" }, g);
    } else cube(c, 3, c.kind === "kept" ? "hi" : "lo");
  }
  // the sold cubes, risen and fading: higher means fainter
  const risen = cells.filter((c) => c.kind === "sold").map((c, k) => ({ ...c, z: 14 + hash(k + 1) * 48 }));
  risen.sort((a, b) => order(a, b) || a.z - b.z); // depth first: footprints never overlap, so this is exact
  for (const c of risen) cube(c, c.z, "acc", Math.max(0.18, 1 - (c.z - 14) / 60));

  // labels, one per group
  leader(svg, K.P(4.5 * C, 1.5 * C, 52), [W - M - 56, 140], [[`${S.sold.pct.toFixed(1)}% sold`, "label", { fill: "var(--acc)", weight: 700, size: 11 }], [S.day, "label", { fill: TONE.muted, size: 7 }]], { cls: "dash nf acc" });
  leader(svg, K.P(0, 3.5 * C, 9), [M + 52, 236], [[`${S.after.toFixed(2)}% kept`, "label", { fill: TONE.hi, weight: 650, size: 10 }], [S.holder, "label", { fill: TONE.muted, size: 6.6 }]], { anchor: "end" });
  leader(svg, K.P(N * C - GAP, 8 * C, 9), [W - M - 62, 316], [[`${(100 - S.before).toFixed(1)}%`, "label", { fill: TONE.muted, weight: 650, size: 10 }], ["everyone else", "label", { fill: TONE.faint, size: 6.6 }]]);

  const s = mk("g", {}, svg), Y = H - 66;
  mk("line", { x1: M, y1: Y - 12, x2: W - M, y2: Y - 12, class: "lo thin" }, s);
  stat(s, M, Y, "STAKE BEFORE", `${S.before.toFixed(2)}%`);
  stat(s, M + 108, Y, "STAKE AFTER", `${S.after.toFixed(2)}%`);
  stat(s, M + 214, Y, `VALUE · ${S.day.toUpperCase()}`, S.value, true);
};
// 7 · The question + the holder's stake only: blocks of ~10% each. The kept block stays bright on the ground;
//     the sold blocks lift away to the right, each higher and fainter. Count it at a glance.
VARIANTS[7] = function () {
  frame(D);
  para(svg, M, 74, `Why would ${S.holder} sell 30% of Bayan in a single day?`, "title", { accent: ["30%"], maxW: W - 2 * M });
  type(svg, M, 132, `Each block ≈ 10% of the company`, "body", { fill: TONE.muted });

  const nSold = Math.round(S.sold.pct / 10), nKept = Math.max(1, Math.round(S.after / 10));
  const B = 20, GAP = 20, H0 = 20; // block size, gap (wide enough that no two blocks touch on screen), height
  const blocks = [...Array(nKept)].map(() => ({ kind: "kept" })).concat([...Array(nSold)].map(() => ({ kind: "sold" })));
  blocks.forEach((b, i) => { b.x = i * (B + GAP); b.z = b.kind === "sold" ? 18 + (i - nKept) * 22 : 0; });
  const span = blocks.length * (B + GAP);
  const K = camera(1.75, [[0, 0, 0], [span, B, 0], [span, 0, blocks.at(-1).z + H0]], 176, 282);
  const g = mk("g", {}, svg);
  floor(g, K, -30, -30, span + 20, B + 30, 9);
  // the ground row: where every block used to sit (dashed slots for the sold ones)
  blocks.forEach((b) => { if (b.kind === "sold") mk("path", { d: poly([[b.x, 0], [b.x + B, 0], [b.x + B, B], [b.x, B]].map(([x, y]) => K.P(x, y, 0))), class: "dash nf" }, g); });
  blocks.forEach((b, i) => {
    const [r, inr] = rings(b.x, 0, b.x + B, B, 2.5, 1);
    const op = b.kind === "sold" ? 1 - (i - nKept) * 0.25 : 1;
    slab(mk("g", { opacity: op }, g), K, r, inr, b.z, b.z + H0, b.kind === "sold" ? "acc" : "hi");
    if (b.kind === "sold") mk("line", { x1: K.P(b.x + B / 2, B / 2, 0)[0], y1: K.P(b.x + B / 2, B / 2, 0)[1], x2: K.P(b.x + B / 2, B / 2, b.z)[0], y2: K.P(b.x + B / 2, B / 2, b.z)[1], class: "dash nf", opacity: op }, g);
  });
  const top = blocks.at(-1);
  leader(svg, K.P(top.x + B, 0, top.z + H0 / 2), [W - M - 56, 168], [[`${S.sold.pct.toFixed(1)}% sold`, "label", { fill: "var(--acc)", weight: 700, size: 12 }], [S.day, "label", { fill: TONE.muted, size: 7 }]], { cls: "dash nf acc" });
  leader(svg, K.P(0, B, H0 / 2), [M + 50, 300], [[`${S.after.toFixed(2)}% kept`, "label", { fill: TONE.hi, weight: 650, size: 11 }], [S.holder, "label", { fill: TONE.muted, size: 6.6 }]], { anchor: "end" });

  const s = mk("g", {}, svg), Y = H - 66;
  mk("line", { x1: M, y1: Y - 12, x2: W - M, y2: Y - 12, class: "lo thin" }, s);
  stat(s, M, Y, "STAKE BEFORE", `${S.before.toFixed(2)}%`);
  stat(s, M + 108, Y, "STAKE AFTER", `${S.after.toFixed(2)}%`);
  stat(s, M + 214, Y, `VALUE · ${S.day.toUpperCase()}`, S.value, true);
};
// 8 · The question + one cart that IS the stake: the dashed heap is what the holder had (before), the white
//     coal left in the tub is what they kept (after), the red coal lifted out is what they sold.
VARIANTS[8] = function () {
  frame(D);
  para(svg, M, 74, `Why would ${S.holder} sell 30% of Bayan in a single day?`, "title", { accent: ["30%"], maxW: W - 2 * M });
  type(svg, M, 132, `This cart is ${S.holder}'s stake in Bayan`, "body", { fill: TONE.muted });

  const cart = drawMineCart(svg, { S: 2.25, cx: 178, cy: 290, keep: S.after / S.before, lift: 30 });
  const P = cart.K.P;
  leader(svg, P(...cart.soldAt), [W - M - 70, 168], [[`${S.sold.pct.toFixed(1)}% sold`, "label", { fill: "var(--acc)", weight: 700, size: 13 }], [`${S.value} · ${S.day}`, "label", { fill: TONE.muted, size: 7.4 }]], { cls: "dash nf acc" });
  leader(svg, P(...cart.heapAt), [W - M - 74, 268], [[`Before: ${S.before.toFixed(2)}%`, "label", { fill: TONE.muted, weight: 650, size: 10 }], ["the full load", "label", { fill: TONE.faint, size: 6.8 }]]);
  leader(svg, P(...cart.keptAt), [M + 76, 312], [[`After: ${S.after.toFixed(2)}%`, "label", { fill: TONE.hi, weight: 700, size: 12 }], ["what's left", "label", { fill: TONE.muted, size: 6.8 }]], { anchor: "end" });
};
// 9 · The question + two carts: before (full load) and after (what's left). Nothing else.
VARIANTS[9] = function () {
  frame(D);
  para(svg, M, 74, `Why would ${S.holder} sell 30% of Bayan in a single day?`, "title", { accent: ["30%"], maxW: W - 2 * M });
  type(svg, M, 132, `${S.holder}'s stake in Bayan, as a cart of coal`, "body", { fill: TONE.muted });

  const L = 96, R = 264, Y = 278;
  drawMineCart(svg, { S: 1.25, cx: L, cy: Y, keep: 1, lift: 0 });
  drawMineCart(svg, { S: 1.25, cx: R, cy: Y, keep: S.after / S.before, lift: 0 });
  const label = (x, k, v, fill) => {
    type(svg, x, 348, k, "caps", { fill: TONE.faint, size: 6.4, anchor: "middle" });
    type(svg, x, 374, v, "num", { size: 26, weight: 300, fill, anchor: "middle" });
  };
  label(L, "BEFORE", `${S.before.toFixed(2)}%`, TONE.muted);
  label(R, "AFTER", `${S.after.toFixed(2)}%`, TONE.hi);
  // the change, between them
  mk("path", { d: `M${L + 52} ${Y - 6}H${R - 52}`, class: "nf", style: "stroke:var(--acc);stroke-width:1.4px" }, svg);
  mk("path", { d: `M${R - 58} ${Y - 10}L${R - 52} ${Y - 6}L${R - 58} ${Y - 2}`, class: "nf", style: "stroke:var(--acc);stroke-width:1.4px" }, svg);
  type(svg, (L + R) / 2, Y - 14, `−${S.sold.pct.toFixed(1)}%`, "label", { fill: "var(--acc)", size: 14, weight: 700, anchor: "middle" });
  type(svg, (L + R) / 2, Y + 10, `${S.value} · ${S.day}`, "label", { fill: TONE.muted, size: 7, anchor: "middle" });
};
// 10 · Hook 1 + a ghost: one cart; the coal that was sold stays in place as a dashed outline.
VARIANTS[10] = function () {
  frame(D);
  para(svg, M, 74, `Why would ${S.holder} sell 30% of Bayan in a single day?`, "title", { accent: ["30%"], maxW: W - 2 * M });
  const cart = drawMineCart(svg, { S: 2.2, cx: 182, cy: 266, keep: S.after / S.before, lift: "ghost" });
  const P = cart.K.P;
  leader(svg, P(...cart.soldAt), [W - M - 64, 160], [[`${S.sold.pct.toFixed(1)}% sold`, "label", { fill: "var(--acc)", weight: 700, size: 12 }], [S.day, "label", { fill: TONE.muted, size: 7 }]], { cls: "dash nf acc" });
  leader(svg, P(...cart.keptAt), [M + 64, 196], [[`${S.after.toFixed(2)}% kept`, "label", { fill: TONE.hi, weight: 650, size: 11 }], ["what's left", "label", { fill: TONE.muted, size: 6.8 }]], { anchor: "end" });
  const s = mk("g", {}, svg), Y = H - 66;
  mk("line", { x1: M, y1: Y - 12, x2: W - M, y2: Y - 12, class: "lo thin" }, s);
  stat(s, M, Y, "STAKE BEFORE", `${S.before.toFixed(2)}%`);
  stat(s, M + 108, Y, "STAKE AFTER", `${S.after.toFixed(2)}%`);
  stat(s, M + 214, Y, `VALUE · ${S.day.toUpperCase()}`, S.value, true);
};
VARIANTS[S.variant]();
