// C2 · UNITS.field — the whole company as 20 copies of one sector object, 5% each (docs/automated-posts.md).
// The stake that moved is the accent (dashed ghosts for a sale, solid accent for a buy), what the holder kept
// is bright, the rest of the company is dim. One drawing per sector, made once, reused by every post.
//
//   drawUnits(parent, { sector, S, cx, cy, moved, kept, mode }) → g with g.K and g.anchor = { moved, kept, load }
//     moved  units that changed hands      kept  units the holder still has (0 for an exit or a new holder)
//     mode   "ghost" (sell) | "add" (buy)
//
// Each kind lays out 20 units in the cart's model box (OBJECTS.md §2) and ranks them: the lowest ranks are the
// moved block (near right), then the kept block next to it, then everyone else, so every group is one block.

const UNIT_N = 20;
const UNIT_GHOST = "stroke:var(--acc);stroke-dasharray:2 2.4;stroke-width:1px;opacity:.8";
const UNIT_BOX = [[-50, -26, 0], [50, 26, 0], [-32, -20, 46], [32, 20, 46]];
// role → [silhouette class, crease class]
const UNIT_CLS = { add: ["acc", "nf acc"], kept: ["sil hi", "nf lo"], other: ["lo", "nf lo"] };

/** One unit's body: the hull of two rings, and a crease ring on top. */
function unitHull(g, K, lower, upper, z0, z1, role, crease = true) {
  const d = poly(hull(ringAt(K.P, lower, z0).concat(ringAt(K.P, upper, z1))));
  if (role === "ghost") return mk("path", { d, style: `fill:${TONE.ground};${UNIT_GHOST}` }, g);
  mk("path", { d, class: UNIT_CLS[role][0] }, g);
  if (crease) mk("path", { d: poly(ringAt(K.P, upper, z1)), class: UNIT_CLS[role][1] }, g);
}

/** A grid of cols × rows (× layers high), ranked right column first, near row first, top layer first. */
function unitGrid(cols, rows, layers, dx, dy, dz) {
  const out = [];
  for (let i = 0; i < cols; i++) for (let j = 0; j < rows; j++) for (let k = 0; k < layers; k++) {
    out.push({ x: (i - (cols - 1) / 2) * dx, y: (j - (rows - 1) / 2) * dy, z: k * dz, rank: ((cols - 1 - i) * rows + (rows - 1 - j)) * layers + (layers - 1 - k) });
  }
  return out;
}

const UNIT_KINDS = {
  // Consumer Cyclicals: shopping bags, 5 × 4
  bag: {
    h: 13,
    layout: () => unitGrid(5, 4, 1, 20, 13, 0),
    draw(g, K, u, role) {
      const P = K.P, BX = 7.6, BY = 3.6, RIM = 13;
      const handle = (yy) => {
        const a = [], b = [];
        for (let k = 0; k <= 20; k++) {
          const t = Math.PI * (k / 20);
          a.push(P(u.x + Math.cos(t) * BX * 0.5, u.y + yy, RIM - 1 + Math.sin(t) * BX * 0.72));
          b.push(P(u.x + Math.cos(t) * BX * 0.38, u.y + yy, RIM - 1 + Math.sin(t) * BX * 0.6));
        }
        return poly(a.concat(b.reverse()));
      };
      const foot = rrect(u.x - BX * 0.9, u.y - BY * 0.88, u.x + BX * 0.9, u.y + BY * 0.88, 0.6, 3);
      const mouth = rrect(u.x - BX, u.y - BY, u.x + BX, u.y + BY, 0.6, 3);
      if (role === "ghost") {
        unitHull(g, K, foot, mouth, 0, RIM, role);
        return mk("path", { d: handle(BY - 0.3), class: "nf", style: UNIT_GHOST }, g);
      }
      const [cls, crease] = UNIT_CLS[role];
      mk("path", { d: handle(-BY + 0.3), class: role === "kept" ? "lo" : cls }, g);
      unitHull(g, K, foot, mouth, 0, RIM, role, false);
      mk("path", { d: poly(ringAt(P, rrect(u.x - BX + 0.5, u.y - BY + 0.5, u.x + BX - 0.5, u.y + BY - 0.5, 0.4, 3), RIM)), class: crease }, g);
      mk("path", { d: handle(BY - 0.3), class: role === "kept" ? "hi" : cls }, g);
    },
  },

  // Basic Materials: ingots, 5 × 2 on the floor, two high
  ingot: {
    h: 7.4,
    layout: () => unitGrid(5, 2, 2, 20, 15, 7.8),
    draw(g, K, u, role) {
      const HX = 8.6, HY = 5, IN = 1.6;
      unitHull(g, K, rrect(u.x - HX, u.y - HY, u.x + HX, u.y + HY, 1.1, 4),
        rrect(u.x - HX + IN, u.y - HY + IN * 0.6, u.x + HX - IN, u.y + HY - IN * 0.6, 0.9, 4), u.z, u.z + 7.4, role);
    },
  },

  // Consumer Non-Cyclicals: a wall of slatted crates, 5 columns × 4 high
  crate: {
    h: 10,
    layout: () => unitGrid(5, 1, 4, 19.5, 0, 10),
    draw(g, K, u, role) {
      const P = K.P, x0 = u.x - 9.5, x1 = u.x + 9.5, Y0 = -9, Y1 = 9, z0 = u.z, z1 = u.z + 10;
      const pts = [];
      for (const x of [x0, x1]) for (const y of [Y0, Y1]) for (const z of [z0, z1]) pts.push(P(x, y, z));
      if (role === "ghost") return mk("path", { d: poly(hull(pts)), style: `fill:${TONE.ground};${UNIT_GHOST}` }, g);
      const [cls, det] = UNIT_CLS[role];
      mk("path", { d: poly(hull(pts)), class: cls }, g);
      const line = (a, b) => mk("path", { d: `M${P(...a).join(" ")}L${P(...b).join(" ")}`, class: det }, g);
      line([x0, Y1, z1], [x1, Y1, z1]); line([x1, Y1, z1], [x1, Y1, z0]); line([x1, Y1, z1], [x1, Y0, z1]);
      for (const f of [0.36, 0.68]) { const z = z0 + 10 * f; line([x0 + 1, Y1, z], [x1 - 1, Y1, z]); line([x1, Y0 + 1, z], [x1, Y1 - 1, z]); }
      line([x1, -2.6, z0 + 8.4], [x1, 2.6, z0 + 8.4]); // hand slot
    },
  },

  // Every sector without its own object: stacks of coins, 5 × 4
  coin: {
    h: 12,
    layout: () => unitGrid(5, 4, 1, 20, 13, 0),
    draw(g, K, u, role) {
      const [ring, inner] = disc(u.x, u.y, 5.6, 1, 36);
      if (role === "ghost") return unitHull(g, K, ring, ring, 0, 12, role);
      for (let k = 0; k < 4; k++) slab(g, K, ring, inner, k * 3, k * 3 + 2.5, UNIT_CLS[role][0]);
    },
  },
};

/** Which object stands for a sector. Sectors without one get coins. */
const SECTOR_UNITS = {
  "Consumer Cyclicals": "bag",
  "Basic Materials": "ingot",
  "Consumer Non-Cyclicals": "crate",
};

function drawUnits(parent, { sector, kind, S = 2.2, cx = 182, cy = 266, moved = 0, kept = 0, mode = "ghost", floorOn = true } = {}) {
  const U = UNIT_KINDS[kind ?? SECTOR_UNITS[sector] ?? "coin"];
  const g = mk("g", {}, parent);
  const K = camera(S, UNIT_BOX, cx, cy);
  if (floorOn) floor(g, K, -80, -50, 80, 50, 8);
  const units = U.layout();
  const nMoved = Math.max(0, Math.min(UNIT_N, moved)), nKept = Math.max(0, Math.min(UNIT_N - nMoved, kept));
  units.slice().sort((a, b) => a.rank - b.rank).forEach((u, i) => { u.role = i < nMoved ? mode : i < nMoved + nKept ? "kept" : "other"; });
  // painter's order: far to near, bottom to top
  units.sort((a, b) => a.x + a.y - (b.x + b.y) || a.z - b.z);
  for (const u of units) U.draw(g, K, u, u.role);
  const top = (arr) => {
    if (!arr.length) return null;
    const z = Math.max(...arr.map((u) => u.z)), row = arr.filter((u) => u.z === z);
    return [row.reduce((s, u) => s + u.x, 0) / row.length, row.reduce((s, u) => s + u.y, 0) / row.length, z + U.h];
  };
  g.K = K;
  g.anchor = { moved: top(units.filter((u) => u.role === mode)), kept: top(units.filter((u) => u.role === "kept")), load: [0, 0, U.h] };
  return g;
}
