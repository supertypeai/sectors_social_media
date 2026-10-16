// Consumer Cyclicals · a paper shopping bag, filled with boxed goods. Style A (faithful): same camera,
// keep/ghost logic and painter's order as drawMineCart. Hook slide = VARIANTS[10]'s layout with the bag.
const D = DATA, S = D.slide;
setAccent(D.direction);

/**
 * A paper shopping bag (x ±30, y ±16, body z 0–38) with two rope handles (to z 54) and boxes standing in
 * its mouth (z 37–52). keep splits the boxes back (kept) to front (gone, dashed accent ghost).
 */
function drawShoppingBag_A(parent, { S = 2.2, cx = 182, cy = 266, floorOn = true, keep = null, lift = "ghost" } = {}) {
  const g = mk("g", {}, parent);
  const K = camera(S, [[-50, -26, 0], [50, 26, 0], [-32, -20, 46], [32, 20, 46]], cx, cy);
  const P = K.P;
  const line = (a, b, cls = "nf lo") => mk("path", { d: `M${P(...a).join(" ")}L${P(...b).join(" ")}`, class: cls }, g);
  const block = (x0, y0, x1, y1, z0, z1, cls = "sil", r = 0.8, b = 0.4) => { const [ring, inner] = rings(x0, y0, x1, y1, r, b); slab(g, K, ring, inner, z0, z1, cls); };
  const dot = (p, r = 0.8, fill = TONE.edge) => { const [x, y] = P(...p); mk("circle", { cx: x, cy: y, r, fill }, g); };
  const BX = 26, BY = 13, Z1 = 39, ZB = 28; // body half-sizes, rim height, box floor (hidden inside)
  const handle = (y, cls) => { // a rope loop standing on the long wall at y
    const pts = [];
    for (let k = 0; k <= 24; k++) { const t = (k / 24) * Math.PI; pts.push(P(Math.cos(t) * 10, y, 34 + Math.sin(t) * 21.5)); }
    mk("path", { d: "M" + pts.map((p) => p.join(" ")).join("L"), class: `nf ${cls}` }, g);
  };
  const face = (pts, cls = "sil") => mk("path", { d: poly(pts.map((p) => P(...p))), class: cls }, g);

  // 1 floor
  if (floorOn) floor(g, K, -80, -50, 80, 50, 8);
  // 2 behind the body: the far handle
  handle(-BY + 0.6, "sil");
  // 3 the body: one prism; its top ring is the open mouth
  block(-BX, -BY, BX, BY, 0, Z1, "sil", 0.6, 0.6);

  // the load: one box per grid cell standing in the mouth, never intersecting
  const boxes = [];
  for (const x of [-18, -6, 6, 18]) for (const y of [-7, 0, 7]) {
    const n = Math.sin(x * 12.9898 + y * 78.233) * 43758.5453, j = n - Math.floor(n);
    const h = 1 - (x / 30) ** 2 - (y / 20) ** 2;
    boxes.push({ x, y, sx: 3.8 + 1.2 * j, sy: 3 + 0.4 * j, z0: ZB, z1: Z1 + 3 + h * 8 + j * 2.5 });
  }
  // the two near walls, re-laid over the box feet so the boxes stand IN the bag, then their creases:
  // folded cuff, the gusset's centre fold and V on the short side, a base crease on the long side
  const nearWalls = () => {
    face([[-BX, BY, 0], [BX, BY, 0], [BX, BY, Z1], [-BX, BY, Z1]]);
    face([[BX, -BY, 0], [BX, BY, 0], [BX, BY, Z1], [BX, -BY, Z1]]);
    line([-BX + 0.6, BY + 0.05, 34], [BX - 0.3, BY + 0.05, 34]); line([BX + 0.05, -BY + 0.6, 34], [BX + 0.05, BY - 0.3, 34]);
    line([BX + 0.05, 0, 34], [BX + 0.05, 0, 9]);
    line([BX + 0.05, 0, 9], [BX + 0.05, -BY + 0.8, 0.6]); line([BX + 0.05, 0, 9], [BX + 0.05, BY - 0.8, 0.6]);
    line([-BX + 1, BY + 0.05, 5], [BX - 1, BY + 0.05, 5]);
  };
  const draw = (b, cls) => {
    block(b.x - b.sx, b.y - b.sy, b.x + b.sx, b.y + b.sy, b.z0, b.z1, cls);
    if (cls === "hi") line([b.x - b.sx + 0.8, b.y, b.z1 + 0.05], [b.x + b.sx - 0.8, b.y, b.z1 + 0.05]); // lid seam
  };
  const order = (a, b) => a.x + a.y - (b.x + b.y) || a.z1 - b.z1;
  const anchor = { load: [0, 0, 53], base: [BX, BY, 0] };
  if (keep == null) { boxes.slice().sort(order).forEach((b) => draw(b, "acc")); nearWalls(); }
  else {
    const byX = boxes.slice().sort((a, b) => a.x - b.x || a.y - b.y), nKeep = Math.max(1, Math.round(boxes.length * keep));
    byX.forEach((b, i) => { b.gone = i >= nKeep; });
    const kept = boxes.filter((b) => !b.gone).sort(order), gone = boxes.filter((b) => b.gone).sort(order);
    for (const b of kept) draw(b, "hi");
    nearWalls();
    // 6 the ghost: gone boxes stay in place (the part above the rim) as dashed accent outlines, on top
    for (const b of gone) {
      const [r] = rings(b.x - b.sx, b.y - b.sy, b.x + b.sx, b.y + b.sy, 0.8, 0.4);
      mk("path", { d: poly(hull(ringAt(P, r, Z1).concat(ringAt(P, r, b.z1)))), class: "nf", style: "stroke:var(--acc);stroke-dasharray:2 2.5;stroke-width:1.1px;opacity:.75" }, g);
    }
    const k0 = kept.reduce((a, b) => (b.z1 > a.z1 ? b : a));
    anchor.kept = [k0.x, k0.y, k0.z1];
    if (gone.length) { const t = gone.reduce((a, b) => (b.x > a.x || (b.x === a.x && b.z1 > a.z1) ? b : a)); anchor.gone = [t.x, t.y, t.z1]; }
  }
  // 7 near parts: the near handle and its rivets
  handle(BY + 0.3, "sil");
  for (const x of [-10, 10]) dot([x, BY + 0.3, 34], 1.1, TONE.hi);
  g.K = K; g.anchor = anchor;
  return g;
}

// ---------------------------------------------------------------- the hook (VARIANTS[10] layout)
const stat = (g, x, yy, k, v, accent = false) => {
  type(g, x, yy, k, "caps", { fill: TONE.faint, size: 5.6 });
  type(g, x, yy + 18, v, "num", { size: 19, weight: 280, fill: accent ? "var(--acc)" : TONE.hi });
};
frame(D);
para(svg, M, 74, `Why would ${S.holder} sell 30% of Bayan in a single day?`, "title", { accent: ["30%"], maxW: W - 2 * M });
const bag = drawShoppingBag_A(svg, { S: 2.2, cx: 182, cy: 266, keep: S.keepOverride ?? S.after / S.before, lift: "ghost" });
const P = bag.K.P;
if (bag.anchor.gone) leader(svg, P(...bag.anchor.gone), [W - M - 64, 160], [[`${S.sold.pct.toFixed(1)}% sold`, "label", { fill: "var(--acc)", weight: 700, size: 12 }], [S.day, "label", { fill: TONE.muted, size: 7 }]], { cls: "dash nf acc" });
leader(svg, P(...(bag.anchor.kept ?? bag.anchor.load)), [M + 64, 196], [[`${S.after.toFixed(2)}% kept`, "label", { fill: TONE.hi, weight: 650, size: 11 }], ["what's left", "label", { fill: TONE.muted, size: 6.8 }]], { anchor: "end" });
const st = mk("g", {}, svg), Y = H - 66;
mk("line", { x1: M, y1: Y - 12, x2: W - M, y2: Y - 12, class: "lo thin" }, st);
stat(st, M, Y, "STAKE BEFORE", `${S.before.toFixed(2)}%`);
stat(st, M + 108, Y, "STAKE AFTER", `${S.after.toFixed(2)}%`);
stat(st, M + 214, Y, `VALUE · ${S.day.toUpperCase()}`, S.value, true);
