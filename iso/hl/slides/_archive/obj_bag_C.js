// Consumer Cyclicals · a shopping bag of boxed goods, style C (technical): registration corners round the
// stage and one dimension line under the bag that measures the load's kept vs original depth.
// The object lives here (render.mjs pastes kernel + style + charts + objects + DATA + slide).

/**
 * An open retail bag on the floor, boxed goods standing proud of the rim, two strap handles.
 * Split is back-to-front along x (kept = rear boxes). Painted far to near per OBJECTS.md §4.
 */
function drawShoppingBag_C(parent, { S, cx, cy, floorOn = true, keep = null, lift = "ghost" }) {
  const g = mk("g", {}, parent);
  const K = camera(S, [[-50, -26, 0], [50, 26, 0], [-32, -20, 46], [32, 20, 46]], cx, cy);
  const P = K.P;
  const line = (a, b, cls = "nf lo") => mk("path", { d: `M${P(...a).join(" ")}L${P(...b).join(" ")}`, class: cls }, g);
  const block = (x0, y0, x1, y1, z0, z1, cls = "sil", r = 0.8, b = 0.4) => { const [ring, inner] = rings(x0, y0, x1, y1, r, b); slab(g, K, ring, inner, z0, z1, cls); };
  const BX = 29, BY = 16, RIM = 32;

  // a strap handle: a flat arch standing in the x–z plane at depth y
  const handle = (y, cls) => {
    const arc = (R, h) => { const pts = []; for (let k = 0; k <= 24; k++) { const a = Math.PI * (k / 24); pts.push([Math.cos(a) * R, y, RIM - 4 + Math.sin(a) * h]); } return pts; };
    const outer = arc(11, 19), inner = arc(9, 17).reverse();
    mk("path", { d: poly(outer.concat(inner).map((p) => P(...p))), class: cls }, g);
  };

  // 1 floor
  if (floorOn) floor(g, K, -80, -50, 80, 50, 8);
  // 2 behind the body: the far handle
  handle(-BY - 0.3, "sil");
  // 3 body: one straight prism
  block(-BX, -BY, BX, BY, 0, RIM, "sil", 1.2, 1);
  // 4 face details: the folded hem, the side gusset crease, the base fold
  line([-BX, BY + 0.05, RIM - 5], [BX, BY + 0.05, RIM - 5]);
  line([BX + 0.05, -BY, RIM - 5], [BX + 0.05, BY, RIM - 5]);
  line([BX + 0.05, 0, 3], [BX + 0.05, 0, RIM - 5]);
  line([BX + 0.05, -BY + 1, RIM - 5], [BX + 0.05, 0, RIM - 11]); line([BX + 0.05, BY - 1, RIM - 5], [BX + 0.05, 0, RIM - 11]);

  // 5 load: boxes on a 6 × 3 grid (never intersecting), a soft mound, far to near
  const boxes = [];
  for (const x of [-22, -11, 0, 11, 22]) for (const y of [-9.6, 0, 9.6]) {
    const n = Math.sin(x * 12.9898 + y * 78.233) * 43758.5453, j = n - Math.floor(n);
    const h = 5 + 6 * (1 - (x / 34) ** 2 - (y / 26) ** 2) + j * 3;
    boxes.push({ x, y, hx: 4.5 + j * 0.6, hy: 4 + (1 - j) * 0.4, z: RIM + h });
  }
  const order = (a, b) => a.x + a.y - (b.x + b.y) || a.z - b.z;
  const solidBox = (b, cls) => {
    block(b.x - b.hx, b.y - b.hy, b.x + b.hx, b.y + b.hy, RIM, b.z, cls);
    line([b.x - b.hx + 0.6, b.y, b.z], [b.x + b.hx - 0.6, b.y, b.z]); // the tape seam across the lid
  };
  const byX = boxes.slice().sort((a, b) => a.x - b.x || a.y - b.y);
  const nKeep = keep == null ? boxes.length : Math.max(1, Math.round(boxes.length * keep));
  byX.forEach((b, i) => { b.sold = i >= nKeep; });
  const kept = boxes.filter((b) => !b.sold).sort(order), sold = boxes.filter((b) => b.sold).sort(order);
  for (const b of kept) solidBox(b, keep == null ? "sil" : "hi");
  // 6 the ghost: sold boxes stay in place as dashed accent outlines
  if (lift === "ghost") for (const b of sold) {
    const [r] = rings(b.x - b.hx, b.y - b.hy, b.x + b.hx, b.y + b.hy, 0.8, 0.4);
    mk("path", { d: poly(hull(ringAt(P, r, RIM).concat(ringAt(P, r, b.z)))), class: "nf", style: "stroke:var(--acc);stroke-dasharray:2 2.5;stroke-width:1.1px;opacity:.8" }, g);
  }
  // 7 near part: the front handle
  handle(BY + 0.3, "sil");

  const top = Math.max(...boxes.map((b) => b.z));
  const lastKept = byX[nKeep - 1], firstSold = byX[nKeep];
  g.K = K;
  g.anchor = { load: [0, 0, top], base: [BX, BY, 0] };
  g.fill = { x0: byX[0].x - byX[0].hx, x1: byX.at(-1).x + byX.at(-1).hx, xk: firstSold ? (lastKept.x === firstSold.x ? lastKept.x : (lastKept.x + lastKept.hx + firstSold.x - firstSold.hx) / 2) : null };
  g.keptAt = kept.length ? [kept[0].x, kept[0].y, kept[0].z] : null;
  g.soldAt = sold.length ? (({ x, y, z }) => [x, y, z])(sold.reduce((a, b) => (b.x > a.x ? b : a))) : null;
  return g;
}

// ---------------------------------------------------------------- hook (VARIANTS[10] layout)
const D = DATA, S = D.slide;
setAccent(D.direction);
const stat = (g, x, yy, k, v, accent = false) => {
  type(g, x, yy, k, "caps", { fill: TONE.faint, size: 5.6 });
  type(g, x, yy + 18, v, "num", { size: 19, weight: 280, fill: accent ? "var(--acc)" : TONE.hi });
};
frame(D);
para(svg, M, 74, `Why would ${S.holder} sell 30% of Bayan in a single day?`, "title", { accent: ["30%"], maxW: W - 2 * M });

// registration corners round the stage
const A = { x0: 24, y0: 170, x1: 336, y1: 360 };
for (const [x, yy, dx, dy] of [[A.x0, A.y0, 1, 1], [A.x1, A.y0, -1, 1], [A.x0, A.y1, 1, -1], [A.x1, A.y1, -1, -1]]) {
  mk("path", { d: `M${x} ${yy + dy * 8}V${yy}H${x + dx * 8}`, class: "nf", style: `stroke:${TONE.edge};stroke-width:1px` }, svg);
}

const keep = S.keepOverride ?? S.after / S.before;
const bag = drawShoppingBag_C(svg, { S: 2.2, cx: 182, cy: 266, keep, lift: "ghost" });
const P = bag.K.P;

// one dimension line on the floor in front of the bag: the load's original depth, ticked where the kept part ends
{
  const { x0, x1, xk } = bag.fill, Y = 22, seg = (a, b, style) => mk("path", { d: `M${P(a, Y, 0).join(" ")}L${P(b, Y, 0).join(" ")}`, class: "nf", style }, svg);
  const tick = (x, len, style) => mk("path", { d: `M${P(x, Y - len, 0).join(" ")}L${P(x, Y + len, 0).join(" ")}`, class: "nf", style }, svg);
  const solidS = `stroke:${TONE.hi};stroke-width:1px`, goneS = "stroke:var(--acc);stroke-width:1px;stroke-dasharray:2 2.5;opacity:.8", tickS = `stroke:${TONE.edge};stroke-width:1px`;
  for (const x of [x0, x1]) mk("path", { d: `M${P(x, 17, 0).join(" ")}L${P(x, Y + 3, 0).join(" ")}`, class: "nf", style: `stroke:${TONE.faint};stroke-width:1px` }, svg); // extension lines
  if (xk == null) seg(x0, x1, solidS); else { seg(x0, xk, solidS); seg(xk, x1, goneS); }
  for (let x = Math.ceil(x0 / 6) * 6; x < x1; x += 6) tick(x, 0.9, `stroke:${TONE.faint};stroke-width:1px`);
  tick(x0, 2.4, tickS); tick(x1, 2.4, tickS);
  if (xk != null) tick(xk, 2.4, `stroke:${TONE.hi};stroke-width:1px`);
}

leader(svg, P(...bag.anchor.load), [W - M - 64, 160], [[`${S.sold.pct.toFixed(1)}% sold`, "label", { fill: "var(--acc)", weight: 700, size: 12 }], [S.day, "label", { fill: TONE.muted, size: 7 }]], { cls: "dash nf acc" });
leader(svg, P(...(bag.keptAt ?? bag.anchor.base)), [M + 64, 196], [[`${S.after.toFixed(2)}% kept`, "label", { fill: TONE.hi, weight: 650, size: 11 }], ["what's left", "label", { fill: TONE.muted, size: 6.8 }]], { anchor: "end" });

const s = mk("g", {}, svg), Y = H - 66;
mk("line", { x1: M, y1: Y - 12, x2: W - M, y2: Y - 12, class: "lo thin" }, s);
stat(s, M, Y, "STAKE BEFORE", `${S.before.toFixed(2)}%`);
stat(s, M + 108, Y, "STAKE AFTER", `${S.after.toFixed(2)}%`);
stat(s, M + 214, Y, `VALUE · ${S.day.toUpperCase()}`, S.value, true);
