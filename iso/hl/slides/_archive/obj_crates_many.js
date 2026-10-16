// Consumer Non-Cyclicals, "many crates": the stake is the stock itself — a wall of 12 grocery crates
// (4 columns × 3 high). Sold columns come off the far end (dashed ghosts); what's kept stands near and bright.
// DATA.slide.keepOverride forces keep (for the 4-up review renders).
const D = DATA, S = D.slide;
setAccent(D.direction);

/**
 * A tidy wall of slatted crates. Each crate: one box, two slat gaps on the long face, a hand slot on the end,
 * an inner rim where the top is open. Removal runs column by column from the far (−x) end, top crate first,
 * so kept = round(keep × N) exactly and the kept part is always a solid stack nearest the eye.
 */
function drawCrateField(parent, { S = 2.2, cx = 182, cy = 266, floorOn = true, keep = null, lift = "ghost" } = {}) {
  const g = mk("g", {}, parent);
  // the cart's model box, turned a quarter so the wall runs far-right → near-left (sold end under the sold label)
  const K = camera(S, [[-26, -50, 0], [26, 50, 0], [-20, -32, 46], [20, 32, 46]], cx, cy);
  // local frame: x runs along the wall (world +y), y is crate depth (world +x)
  const P = (x, y, z) => K.P(y, x, z), W2 = (p) => p && [p[1], p[0], p[2]];
  const COLS = 4, LAYERS = 3, CW = 24, CD = 20, CH = 12.5, X0 = -COLS * CW / 2, Y0 = -CD / 2, Y1 = CD / 2;
  const quad = (pts, cls, style) => mk("path", { d: poly(pts.map((p) => P(...p))), class: cls, ...(style ? { style } : {}) }, g);
  const line = (a, b, cls) => mk("path", { d: `M${P(...a).join(" ")}L${P(...b).join(" ")}`, class: cls }, g);

  if (floorOn) floor(g, K, -80, -50, 80, 50, 8);

  const crates = [];
  for (let i = 0; i < COLS; i++) for (let k = 0; k < LAYERS; k++) crates.push({ i, k, x0: X0 + i * CW, x1: X0 + (i + 1) * CW, z0: k * CH, z1: (k + 1) * CH });
  const N = crates.length, nKeep = keep == null ? N : Math.max(0, Math.min(N, Math.round(N * keep)));
  // removal order: far column first, top crate first within a column
  crates.slice().sort((a, b) => a.i - b.i || b.k - a.k).forEach((c, r) => { c.gone = r < N - nKeep; });

  const crate = (c, cls, det) => {
    const { x0, x1, z0, z1 } = c, I = 1.2;
    quad([[x0, Y1, z1], [x1, Y1, z1], [x1, Y0, z1], [x0, Y0, z1]], cls);                    // top
    quad([[x0, Y1, z0], [x1, Y1, z0], [x1, Y1, z1], [x0, Y1, z1]], cls);                    // long face
    quad([[x1, Y0, z0], [x1, Y1, z0], [x1, Y1, z1], [x1, Y0, z1]], cls);                    // end face
    for (const f of [0.36, 0.68]) {                                                          // slat gaps
      const z = z0 + (z1 - z0) * f;
      line([x0 + I, Y1 + 0.05, z], [x1 - I, Y1 + 0.05, z], det);
      line([x1 + 0.05, Y0 + I, z], [x1 + 0.05, -4.5, z], det);
    }
    // the end hand slot sits in the top slat
    const hz = z0 + (z1 - z0) * 0.84;
    line([x1 + 0.05, -3, hz], [x1 + 0.05, 3, hz], cls);
    // open top: inner rim, only where nothing stands on it
    if (c.open) {
      quad([[x0 + I, Y1 - I, z1], [x1 - I, Y1 - I, z1], [x1 - I, Y0 + I, z1], [x0 + I, Y0 + I, z1]], `nf ${det}`);
      // a hint of produce: a 3 × 2 grid of round tops just clearing the rim
      for (const v of [-4.5, 4.5]) for (const u of [-7, 0, 7]) {
        const [r, inn] = disc(v, (x0 + x1) / 2 + u, 3.1, 0.9, 28);   // world frame: x = depth, y = along wall
        slab(g, K, r, inn, z1 - 1.5, z1 + 1.6, cls);
      }
    }
  };
  const ghostCrate = (c) => {
    const pts = [];
    for (const x of [c.x0, c.x1]) for (const y of [Y0, Y1]) for (const z of [c.z0, c.z1]) pts.push(P(x, y, z));
    mk("path", { d: poly(hull(pts)), style: "stroke:var(--acc);stroke-dasharray:2 2.5;stroke-width:1.1px;opacity:.7" }, g);
  };

  // painter's order: far → near, bottom → top
  crates.sort((a, b) => a.i + a.k - (b.i + b.k) || a.k - b.k);
  for (const c of crates) {
    const above = crates.find((d) => d.i === c.i && d.k === c.k + 1);
    c.open = !above || (above.gone && lift === "ghost");
    if (!c.gone) crate(c, keep == null ? "sil" : "hi", "sil");
    else if (lift === "add") { c.open = !above; crate(c, "acc", "acc"); }
    else if (lift === "ghost") ghostCrate(c);
  }

  const kept = crates.filter((c) => !c.gone), gone = crates.filter((c) => c.gone);
  const topOf = (c) => [(c.x0 + c.x1) / 2, 0, c.z1];
  g.K = K;
  g.anchor = {
    load: W2([0, 0, LAYERS * CH]),
    base: W2([-X0, Y1, 0]),
    kept: W2(kept.length ? topOf(kept.reduce((a, b) => (b.z1 > a.z1 || (b.z1 === a.z1 && b.i > a.i) ? b : a))) : null),
    sold: W2(gone.length ? topOf(gone.reduce((a, b) => (b.z1 > a.z1 || (b.z1 === a.z1 && b.i > a.i) ? b : a))) : null),
  };
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
const obj = drawCrateField(svg, { S: 2.2, cx: 182, cy: 266, keep, lift: D.direction === "buy" ? "add" : "ghost" });
const P = obj.K.P;
leader(svg, P(...(obj.anchor.sold ?? obj.anchor.load)), [W - M - 64, 160], [[`${S.sold.pct.toFixed(1)}% sold`, "label", { fill: "var(--acc)", weight: 700, size: 12 }], [S.day, "label", { fill: TONE.muted, size: 7 }]], { cls: "dash nf acc" });
leader(svg, P(...(obj.anchor.kept ?? obj.anchor.base)), [M + 64, 196], [[`${S.after.toFixed(2)}% kept`, "label", { fill: TONE.hi, weight: 650, size: 11 }], ["what's left", "label", { fill: TONE.muted, size: 6.8 }]], { anchor: "end" });
const s = mk("g", {}, svg), Y = H - 66;
mk("line", { x1: M, y1: Y - 12, x2: W - M, y2: Y - 12, class: "lo thin" }, s);
stat(s, M, Y, "STAKE BEFORE", `${S.before.toFixed(2)}%`);
stat(s, M + 108, Y, "STAKE AFTER", `${S.after.toFixed(2)}%`);
stat(s, M + 214, Y, `VALUE · ${S.day.toUpperCase()}`, S.value, true);
