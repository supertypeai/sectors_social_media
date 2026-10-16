// Consumer Cyclicals · a shopping bag, style B (minimal): one box body, two strap handles, 12 boxed goods.
// The object lives here (not objects.js) while it is a candidate; the hook reuses byan_variants VARIANTS[10].

/**
 * An open retail bag with rope handles, boxed goods standing out of its mouth. Painted far to near.
 * keep: fraction of the boxes that stay (rear first); the rest are dashed accent ghosts in place.
 */
function drawShoppingBag_B(parent, { S, cx, cy, floorOn = true, keep = null, lift = "ghost" } = {}) {
  const g = mk("g", {}, parent);
  const K = camera(S, [[-50, -26, 0], [50, 26, 0], [-32, -20, 46], [32, 20, 46]], cx, cy);
  const P = K.P;
  const BX = 31, BY = 14, FX = 28, FY = 12.5, RIM = 40; // mouth x ±31 y ±14, foot a little smaller
  const block = (x0, y0, x1, y1, z0, z1, cls = "sil", r = 1, b = 0.5) => { const [ring, inner] = rings(x0, y0, x1, y1, r, b); slab(g, K, ring, inner, z0, z1, cls); };
  // a handle: a slim ribbon arch standing on one long face (y = yy), rooted just under the rim
  const handle = (yy, cls) => {
    const N = 32, out = [], inn = [];
    for (let k = 0; k <= N; k++) {
      const a = Math.PI * (k / N);
      out.push(P(Math.cos(a) * 13, yy, RIM - 4 + Math.sin(a) * 20));
      inn.push(P(Math.cos(a) * 10.6, yy, RIM - 4 + Math.sin(a) * 17.6));
    }
    mk("path", { d: poly(out.concat(inn.reverse())), class: cls }, g);
  };

  // 1 · floor
  if (floorOn) floor(g, K, -80, -50, 80, 50, 8);
  // 2 · behind the body: the far handle
  handle(-BY + 0.5, "lo");
  // 3 · the body: a gently flared solid (hull of foot and mouth), one crease at the mouth
  const foot = rrect(-FX, -FY, FX, FY, 1.2, 4), mouth = rrect(-BX, -BY, BX, BY, 1.2, 4), lip = rrect(-BX + 1, -BY + 1, BX - 1, BY - 1, 0.8, 4);
  mk("path", { d: poly(hull(ringAt(P, foot, 0).concat(ringAt(P, mouth, RIM)))), class: "sil" }, g);
  mk("path", { d: poly(ringAt(P, lip, RIM)), class: "nf lo" }, g);
  // 4 · one detail: the gusset fold, a V down the short (+x) face
  const onX = (y, z) => { const t = z / RIM; return [FX + (BX - FX) * t + 0.05, y, z]; };
  mk("path", { d: `M${P(...onX(-BY * 0.9, RIM)).join(" ")}L${P(...onX(0, RIM * 0.62)).join(" ")}L${P(...onX(BY * 0.9, RIM)).join(" ")}M${P(...onX(0, RIM * 0.62)).join(" ")}L${P(...onX(0, 1)).join(" ")}`, class: "nf lo" }, g);

  // 5 · the load: 12 boxes on a 4 × 3 grid, heights varied, never intersecting
  const boxes = [], CX = 14.6, CY = 8.8;
  for (let i = 0; i < 4; i++) for (let j = 0; j < 3; j++) {
    const x = -BX + 2 + CX * (i + 0.5), y = -BY + 1 + CY * (j + 0.5);
    const n = Math.sin(i * 12.9898 + j * 78.233) * 43758.5453, t = n - Math.floor(n);
    boxes.push({ x, y, hx: CX * (0.36 + 0.07 * t), hy: CY * 0.4, z0: RIM - 1, z1: RIM + 5 + t * 7 });
  }
  const draw = (b, cls) => block(b.x - b.hx, b.y - b.hy, b.x + b.hx, b.y + b.hy, b.z0, b.z1, cls, 0.8, 0.5);
  const order = (a, b) => a.x + a.y - (b.x + b.y) || a.z1 - b.z1;
  if (keep == null) {
    boxes.sort(order).forEach((b) => draw(b, "hi"));
  } else {
    const nKeep = Math.max(1, Math.round(boxes.length * keep));
    boxes.slice().sort((a, b) => a.x - b.x || a.y - b.y).forEach((b, i) => { b.sold = i >= nKeep; });
    boxes.filter((b) => !b.sold).sort(order).forEach((b) => draw(b, "hi"));
    // 6 · the ghost: sold boxes stay where they stood, as dashed accent outlines, on top
    if (lift === "ghost") for (const b of boxes.filter((q) => q.sold).sort(order)) {
      const [r] = rings(b.x - b.hx, b.y - b.hy, b.x + b.hx, b.y + b.hy, 0.8, 0.5);
      mk("path", { d: poly(hull(ringAt(P, r, b.z0).concat(ringAt(P, r, b.z1)))), class: "nf", style: "stroke:var(--acc);stroke-dasharray:2 2.5;stroke-width:1.1px;opacity:.8" }, g);
    }
  }
  // 7 · near: the front handle over everything
  handle(BY - 0.5, "sil");

  g.K = K;
  g.anchor = { load: [0, 0, RIM + 12], base: [FX, FY, 0] };
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
const bag = drawShoppingBag_B(svg, { S: 2.2, cx: 182, cy: 266, keep: S.keepOverride ?? S.after / S.before, lift: "ghost" });
const P = bag.K.P;
leader(svg, P(...bag.anchor.load), [W - M - 64, 160], [[`${S.sold.pct.toFixed(1)}% sold`, "label", { fill: "var(--acc)", weight: 700, size: 12 }], [S.day, "label", { fill: TONE.muted, size: 7 }]], { cls: "dash nf acc" });
leader(svg, P(...bag.anchor.base), [M + 64, 352], [[`${S.after.toFixed(2)}% kept`, "label", { fill: TONE.hi, weight: 650, size: 11 }], ["what's left", "label", { fill: TONE.muted, size: 6.8 }]], { anchor: "end" });
const st = mk("g", {}, svg), Y = H - 66;
mk("line", { x1: M, y1: Y - 12, x2: W - M, y2: Y - 12, class: "lo thin" }, st);
stat(st, M, Y, "STAKE BEFORE", `${S.before.toFixed(2)}%`);
stat(st, M + 108, Y, "STAKE AFTER", `${S.after.toFixed(2)}%`);
stat(st, M + 214, Y, `VALUE · ${S.day.toUpperCase()}`, S.value, true);
