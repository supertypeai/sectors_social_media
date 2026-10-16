// Object test · Basic Materials → an ingot pallet (style A · faithful). Hook layout = byan_variants VARIANTS[10].
const D = DATA, S = D.slide;
setAccent(D.direction);

// ---------------------------------------------------------------- an ingot pallet
/**
 * A block pallet (nine feet, three stringers, five deck boards) carrying 20 trapezoid ingots in four
 * cross-stacked layers of five. keep splits top-to-bottom: the top units go first. lift "ghost" = gone units
 * as dashed accent outlines; lift "add" (a buy) = the new units drawn solid in the accent.
 */
function drawIngotPallet_A(parent, { S, cx, cy, floorOn = true, keep = null, lift = "ghost" } = {}) {
  const g = mk("g", {}, parent);
  const K = camera(S, [[-50, -26, 0], [50, 26, 0], [-32, -20, 46], [32, 20, 46]], cx, cy);
  const P = K.P, front = K.front;
  const block = (x0, y0, x1, y1, z0, z1, cls = "sil", r = 0.8, b = 0.4) => { const [ring, inner] = rings(x0, y0, x1, y1, r, b); slab(g, K, ring, inner, z0, z1, cls); };
  const dot = (p, r = 0.6, fill = TONE.edge) => { const [x, y] = P(...p); mk("circle", { cx: x, cy: y, r, fill }, g); };

  if (floorOn) floor(g, K, -80, -50, 80, 50, 8);

  // 1 · feet (3 × 3), far to near, then 2 · stringers, then 3 · deck boards (with nail heads at the ends)
  const PX = 34, PY = 22;
  const feet = [];
  for (const x of [-PX + 4, 0, PX - 4]) for (const y of [-PY + 4, 0, PY - 4]) feet.push([x, y]);
  feet.sort((a, b) => a[0] + a[1] - (b[0] + b[1]));
  for (const [x, y] of feet) block(x - 4, y - 4, x + 4, y + 4, 0, 4.5);
  for (const y of [-PY + 4, 0, PY - 4]) block(-PX, y - 4.5, PX, y + 4.5, 4.5, 6.5);
  const BW = 8.4, BG = (2 * PY - 5 * BW) / 4;
  for (let i = 0; i < 5; i++) { const x0 = -PX, y0 = -PY + i * (BW + BG); block(x0, y0, PX, y0 + BW, 6.5, 8.5, "sil", 0.6, 0.3); }
  for (let i = 0; i < 5; i++) { const y = -PY + i * (BW + BG) + BW / 2; for (const x of [PX - 3.5]) { dot([x, y - 2, 8.55], 0.55); dot([x, y + 2, 8.55], 0.55); } }

  // 4 · the ingots: trapezoid bars (foot wider than top), layers alternate direction, 5 per layer
  const Z0 = 8.5, LH = 7.5, units = [];
  for (let L = 0; L < 5; L++) for (let i = 0; i < 4; i++) {
    const z0 = Z0 + L * LH, z1 = z0 + LH - 0.6;
    if (L % 2 === 0) { const w = 13, x = -21.75 + i * 14.5; units.push({ L, x, y: 0, hx: w / 2, hy: 18, z0, z1 }); }
    else { const w = 8.6, y = -14.4 + i * 9.6; units.push({ L, x: 0, y, hx: 28.5, hy: w / 2, z0, z1 }); }
  }
  const ztop = Z0 + 5 * LH - 0.6;
  const ingot = (u, cls, style) => {
    const foot = rrect(u.x - u.hx, u.y - u.hy, u.x + u.hx, u.y + u.hy, 0.8, 4);
    const t = 1.6, top = rrect(u.x - u.hx + t, u.y - u.hy + t, u.x + u.hx - t, u.y + u.hy - t, 0.8, 4);
    const sh = hull(ringAt(P, foot, u.z0).concat(ringAt(P, top, u.z1)));
    if (style) { mk("path", { d: poly(sh), class: "nf", style }, g); return; }
    mk("path", { d: poly(sh), class: cls }, g);
    mk("path", { d: poly(ringAt(P, top, u.z1)), class: "nf lo" }, g); // the cast top face
  };
  // top-to-bottom, front-to-back within a layer: rank 0 leaves first
  const order = units.slice().sort((a, b) => b.L - a.L || (b.x + b.y) - (a.x + a.y));
  const nGone = keep == null ? 0 : Math.min(units.length - 1, Math.max(0, units.length - Math.round(units.length * keep)));
  order.forEach((u, i) => { u.gone = i < nGone; });
  const paint = (a, b) => a.L - b.L || (a.x + a.y) - (b.x + b.y);
  const kept = units.filter((u) => !u.gone).sort(paint), gone = units.filter((u) => u.gone).sort(paint);
  for (const u of kept) ingot(u, keep == null ? "acc" : "hi");
  // 6 · the gone part, last
  for (const u of gone) {
    if (lift === "add") ingot(u, "acc");
    else ingot(u, null, `fill:${TONE.ground};stroke:var(--acc);stroke-dasharray:2 2.5;stroke-width:1.1px;opacity:.75`);
  }

  // kept leader lands on the near face of the front-left bottom ingot: always visible, never under a ghost
  const fk = kept.filter((u) => u.L === 0).reduce((a, b) => (b.x < a.x ? b : a));
  g.keptAt = [fk.x, fk.y + fk.hy, (fk.z0 + fk.z1) / 2];
  if (gone.length) { const t = gone.reduce((a, b) => (b.z1 > a.z1 ? b : a)); g.goneAt = [t.x, t.y, t.z1]; }
  g.K = K;
  g.anchor = { load: [0, 0, ztop], base: [PX, PY, 0] };
  return g;
}

// ---------------------------------------------------------------- hook (VARIANTS[10] layout)
const stat = (g, x, yy, k, v, accent = false) => {
  type(g, x, yy, k, "caps", { fill: TONE.faint, size: 5.6 });
  type(g, x, yy + 18, v, "num", { size: 19, weight: 280, fill: accent ? "var(--acc)" : TONE.hi });
};
frame(D);
para(svg, M, 74, `Why would ${S.holder} sell 30% of Bayan in a single day?`, "title", { accent: ["30%"], maxW: W - 2 * M });
const keep = S.keepOverride ?? S.after / S.before;
const obj = drawIngotPallet_A(svg, { S: 2.2, cx: 182, cy: 266, keep, lift: D.direction === "buy" ? "add" : "ghost" });
const P = obj.K.P;
leader(svg, P(...(obj.goneAt ?? obj.anchor.load)), [W - M - 64, 160], [[`${S.sold.pct.toFixed(1)}% sold`, "label", { fill: "var(--acc)", weight: 700, size: 12 }], [S.day, "label", { fill: TONE.muted, size: 7 }]], { cls: "dash nf acc" });
leader(svg, P(...(obj.keptAt ?? obj.anchor.base)), [M + 64, 196], [[`${S.after.toFixed(2)}% kept`, "label", { fill: TONE.hi, weight: 650, size: 11 }], ["what's left", "label", { fill: TONE.muted, size: 6.8 }]], { anchor: "end" });
const s = mk("g", {}, svg), Y = H - 66;
mk("line", { x1: M, y1: Y - 12, x2: W - M, y2: Y - 12, class: "lo thin" }, s);
stat(s, M, Y, "STAKE BEFORE", `${S.before.toFixed(2)}%`);
stat(s, M + 108, Y, "STAKE AFTER", `${S.after.toFixed(2)}%`);
stat(s, M + 214, Y, `VALUE · ${S.day.toUpperCase()}`, S.value, true);
