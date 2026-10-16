// Consumer Non-Cyclicals · a slatted grocery crate of cans, style C (technical): registration corners round the
// stage and one dimension line under the crate that splits its length into kept vs gone. Hook = VARIANTS[10].
const D = DATA, S = D.slide;
setAccent(D.direction);

/**
 * A slatted produce crate holding 18 cans (6 × 3). OBJECTS.md §1 contract. keep splits the cans back-to-front
 * along x (rear stays solid, front goes dashed accent). With `dim` (default on), a dimension line on the floor
 * in front of the crate measures the full fill and marks where the kept part ends.
 */
function drawGroceryCrate_C(parent, { S: sc, cx, cy, floorOn = true, keep = null, lift = "ghost", dim = true }) {
  const g = mk("g", {}, parent);
  const K = camera(sc, [[-50, -26, 0], [50, 26, 0], [-32, -20, 46], [32, 20, 46]], cx, cy);
  const P = K.P;
  const X = 40, Y = 20, Z = 34; // crate half-length, half-depth, rim height
  const line = (a, b, cls = "nf lo", style) => mk("path", { d: `M${P(...a).join(" ")}L${P(...b).join(" ")}`, class: cls, ...(style ? { style } : {}) }, g);

  // 1 floor
  if (floorOn) floor(g, K, -80, -50, 80, 50, 8);
  // 3 body: one rounded box, then the dark opening on top (inner rim) so the cans read as sitting inside
  const [outer, inner] = rings(-X, -Y, X, Y, 2, 1);
  slab(g, K, outer, inner, 0, Z, "sil");
  mk("path", { d: poly(ringAt(P, rrect(-X + 2.6, -Y + 2.6, X - 2.6, Y - 2.6, 1.2, 4), Z)), class: "lo" }, g);
  // 4 slats: two gaps on each visible face (+y long side, +x short end), corner posts, a hand slot on the end
  for (const z of [11.5, 22.5]) {
    for (const dz of [0, 1.6]) {
      line([-X + 4, Y + 0.05, z + dz], [X - 4, Y + 0.05, z + dz]);
      line([X + 0.05, -Y + 4, z + dz], [X + 0.05, Y - 4, z + dz]);
    }
  }
  for (const x of [-X + 4, X - 4]) line([x, Y + 0.05, 1.5], [x, Y + 0.05, Z - 1.5]);
  line([X + 0.05, -Y + 4, 1.5], [X + 0.05, -Y + 4, Z - 1.5]);
  line([X + 0.05, Y - 4, 1.5], [X + 0.05, Y - 4, Z - 1.5]);
  const slot = rrect(-7, 26.5, 7, 30.5, 2, 4).map((q) => P(X + 0.05, q.u, q.v));
  mk("path", { d: poly(slot), class: "nf lo" }, g);

  // 5 load: cans standing in the crate, tops above the rim
  const R = 5.2, Z0 = Z - 1, Z1 = Z + 9, cans = [];
  for (let i = 0; i < 6; i++) for (let j = 0; j < 3; j++) cans.push({ x: -32.5 + i * 13, y: -13 + j * 13 });
  const can = (c, mode) => {
    const [r] = disc(c.x, c.y, R, 1, 40), [ri] = disc(c.x, c.y, R - 1.3, 1, 40);
    if (mode === "ghost") {
      const st = "stroke:var(--acc);stroke-dasharray:2 2.5;stroke-width:1.1px;opacity:.8";
      mk("path", { d: poly(hull(ringAt(P, r, Z0).concat(ringAt(P, r, Z1)))), class: "nf", style: st }, g);
      mk("path", { d: poly(ringAt(P, r, Z1)), class: "nf", style: st }, g);
      return;
    }
    const cls = mode === "acc" ? "acc" : keep == null ? "sil" : "hi";
    mk("path", { d: poly(hull(ringAt(P, r, Z0).concat(ringAt(P, r, Z1)))), class: cls }, g);
    mk("path", { d: poly(ringAt(P, r, Z1)), class: cls }, g);
    mk("path", { d: poly(ringAt(P, ri, Z1)), class: "nf lo" }, g);
    mk("path", { d: seam(K, r, Z1 - 3), class: "nf lo" }, g);
  };
  const order = (a, b) => a.x + a.y - (b.x + b.y);
  const nKeep = keep == null ? cans.length : Math.max(1, Math.round(cans.length * keep));
  cans.slice().sort((a, b) => a.x - b.x || a.y - b.y).forEach((c, i) => { c.gone = i >= nKeep; });
  for (const c of cans.filter((c) => !c.gone).sort(order)) can(c, keep == null ? "acc" : "kept");
  // 6 the ghost, last
  if (lift === "ghost") for (const c of cans.filter((c) => c.gone).sort(order)) can(c, "ghost");

  // the one technical extra: a dimension line on the floor in front, full fill length, split at the kept edge
  const kept = cans.filter((c) => !c.gone), gone = cans.filter((c) => c.gone);
  const xs = -32.5 - R, xe = 32.5 + R, xk = gone.length ? (Math.max(...kept.map((c) => c.x)) + Math.min(...gone.map((c) => c.x))) / 2 : xe;
  if (dim) {
    const yd = Y + 9, tk = (x, h, style) => line([x, Y + 3, 0], [x, yd + h, 0], "nf", style ?? `stroke:${TONE.edge};stroke-width:1px`);
    tk(xs, 2.5); tk(xe, 2.5);
    line([xs, yd, 0], [xk, yd, 0], "nf", `stroke:${TONE.hi};stroke-width:1px`);
    if (xk < xe) {
      line([xk, yd, 0], [xe, yd, 0], "nf", "stroke:var(--acc);stroke-width:1px;stroke-dasharray:2 2.5");
      tk(xk, 4, `stroke:${TONE.hi};stroke-width:1px`);
    }
    for (let x = xs + 6.5; x < xe - 1; x += 13) line([x, yd - 1, 0], [x, yd + 1, 0], "nf", `stroke:${TONE.faint};stroke-width:1px`); // one tick per can column
  }

  g.K = K;
  g.anchor = { load: [0, 0, Z1], base: [X, Y, 0] };
  g.keptAt = kept.length ? [kept[0].x, kept[0].y, Z1] : null;
  g.soldAt = gone.length ? [gone.at(-1).x, gone.at(-1).y, Z1] : null;
  return g;
}

// ---------------------------------------------------------------- hook (VARIANTS[10] layout)
const stat = (g, x, yy, k, v, accent = false) => {
  type(g, x, yy, k, "caps", { fill: TONE.faint, size: 5.6 });
  type(g, x, yy + 18, v, "num", { size: 19, weight: 280, fill: accent ? "var(--acc)" : TONE.hi });
};
frame(D);
para(svg, M, 74, `Why would ${S.holder} sell 30% of Bayan in a single day?`, "title", { accent: ["30%"], maxW: W - 2 * M });
// registration corners round the stage (24,170 → 336,360)
const A = { x0: 24, y0: 170, x1: 336, y1: 360 };
for (const [x, yy, dx, dy] of [[A.x0, A.y0, 1, 1], [A.x1, A.y0, -1, 1], [A.x0, A.y1, 1, -1], [A.x1, A.y1, -1, -1]]) {
  mk("path", { d: `M${x} ${yy + dy * 7}V${yy}H${x + dx * 7}`, class: "nf", style: `stroke:${TONE.edge};stroke-width:1px` }, svg);
}
const keep = S.keepOverride ?? S.after / S.before;
const crate = drawGroceryCrate_C(svg, { S: 2.2, cx: 182, cy: 266, keep, lift: "ghost" });
const P = crate.K.P;
leader(svg, P(...(crate.soldAt ?? crate.anchor.load)), [W - M - 64, 160], [[`${S.sold.pct.toFixed(1)}% sold`, "label", { fill: "var(--acc)", weight: 700, size: 12 }], [S.day, "label", { fill: TONE.muted, size: 7 }]], { cls: "dash nf acc" });
leader(svg, P(...(crate.keptAt ?? crate.anchor.base)), [M + 64, 196], [[`${S.after.toFixed(2)}% kept`, "label", { fill: TONE.hi, weight: 650, size: 11 }], ["what's left", "label", { fill: TONE.muted, size: 6.8 }]], { anchor: "end" });
const st = mk("g", {}, svg), Y = H - 66;
mk("line", { x1: M, y1: Y - 12, x2: W - M, y2: Y - 12, class: "lo thin" }, st);
stat(st, M, Y, "STAKE BEFORE", `${S.before.toFixed(2)}%`);
stat(st, M + 108, Y, "STAKE AFTER", `${S.after.toFixed(2)}%`);
stat(st, M + 214, Y, `VALUE · ${S.day.toUpperCase()}`, S.value, true);
