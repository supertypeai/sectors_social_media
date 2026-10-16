// Shared isometric parts for Sectors feed posts. Lifted from the foreign-outflow video
// (supertype/video/foreign-outflow/sectors-outflow.js) so every post type draws money,
// towers and people the same way. post.mjs pastes this file above each story, so it has no
// imports or exports: ISO is a global by the time it runs.
const { body, prog, mix, ease, settle, arc, jitter, window: win } = ISO;
const { seg, poly, circ } = ISO.HL;

// ---------------------------------------------------------------- Sectors palette (warm stone + Spectral meaning)
const SECTORS = {
  bg: ["#14110f", "#0c0a09"], ink: "#fafaf9", muted: "#a8a29e",
  amber: "#fdae61", rose: "#d53e4f", green: "#abdda4", teal: "#66c2a5",
};
const SECTORS_THEME = {
  bg: SECTORS.bg, ink: SECTORS.ink, edge: "#e7e5e4", line: "#57534e", lo: "#292524",
  shadow: "rgba(0,0,0,0.45)", caption: SECTORS.ink, muted: SECTORS.muted, accent: SECTORS.rose,
  palette: { ground: "#1c1917", plate: "#1a1715", paper: "#8a817a", card: "#3a3431", tray: "#4a3a2c", lane: "#29241f",
    blue: "#2f6f99", green: "#5fb59a", amber: "#e39a52", rose: "#c63c4e", violet: "#4e4488", ink: "#fafaf9" },
};
const WOOD = "#7a5a3c", WOOD_S = "#563e29", STEEL = "#a8a29e", SKIN = "#d9b38c";
const NOTE = "#9fcf9a", NOTE_S = "#6f9e6b"; // banknotes: rupiah green-grey
const GOLD = "#f1c94b", GOLD_S = "#c49c2a";

// ---------------------------------------------------------------- drawing on faces
// The camera looks from +x +y, so a solid shows its top, its +x face and its +y face.
const fx = (P, p) => (a, z) => P(p.x + p.w / 2 + 0.05, p.y + a, p.z + z); // +x face: a along y
const fy = (P, p) => (a, z) => P(p.x + a, p.y + p.d / 2 + 0.05, p.z + z); // +y face: a along x
const L2 = (f, a0, z0, a1, z1) => seg(f(a0, z0), f(a1, z1));
const R2 = (f, a0, z0, a1, z1) => poly([f(a0, z0), f(a1, z0), f(a1, z1), f(a0, z1)]);
const ring = (top, cu, cv, r) => poly(circ(r, 20).map((q) => top(cu + q.u, cv + q.v)));
/** The half of a horizontal circle that faces the camera: a coin's rim, a cylinder's ridge. */
const rimFront = (P, cx, cy, r, z) => {
  const pts = [];
  for (let k = 0; k <= 12; k++) {
    const a = (-45 + (180 * k) / 12) * (Math.PI / 180);
    pts.push(P(cx + Math.cos(a) * r, cy + Math.sin(a) * r, z));
  }
  return "M" + pts.map((q) => `${q[0].toFixed(2)} ${q[1].toFixed(2)}`).join("L");
};

/** A banknote bundle (or a stack of them, `layerH` units each): sheet lines, a strap, a portrait on top. */
const bundleMarks = (layerH = 7, top = true) => (topF, P, p) => {
  const X = fx(P, p), Y = fy(P, p), W = p.w / 2, Dd = p.d / 2;
  let d = "";
  for (let z = 0; z < p.h - 0.5; z += layerH) {
    const hh = Math.min(layerH, p.h - z);
    if (z > 0) d += L2(X, -Dd + 0.6, z, Dd - 0.6, z) + L2(Y, -W + 0.6, z, W - 0.6, z);
    if (hh > 2.4) for (const f of [0.35, 0.68]) d += L2(Y, -W + 1.2, z + hh * f, -3.6, z + hh * f) + L2(Y, 3.6, z + hh * f, W - 1.2, z + hh * f) + L2(X, -Dd + 1.2, z + hh * f, Dd - 1.2, z + hh * f);
    d += R2(Y, -3, z + 0.3, 3, z + hh - 0.3); // the paper strap
  }
  if (top) d += L2((u, v) => topF(u, v), -3, -Dd + 0.6, -3, Dd - 0.6) + L2((u, v) => topF(u, v), 3, -Dd + 0.6, 3, Dd - 0.6) + ring(topF, -W + Math.min(7, W * 0.45), 0, Math.min(3, Dd * 0.4));
  return d;
};
/** An office tower: a window grid on both faces, a lobby band at the foot. */
const towerMarks = (topF, P, p) => {
  const X = fx(P, p), Y = fy(P, p), W = p.w / 2, Dd = p.d / 2;
  let d = L2(Y, -W + 1, 6, W - 1, 6) + L2(X, -Dd + 1, 6, Dd - 1, 6);
  for (let z = 9; z < p.h - 4; z += 6) {
    for (let a = -W + 3; a < W - 4; a += 5) d += R2(Y, a, z, a + 3, z + 3.2);
    for (let a = -Dd + 3; a < Dd - 4; a += 5) d += R2(X, a, z, a + 3, z + 3.2);
  }
  return d + R2(Y, -3, 0, 3, 4.5); // the door
};
/** A stack of coins: a face ring on top, one rim line per coin down the front. */
const coinMarks = (top, P, p) => { let d = ring(top, 0, 0, p.w / 2 - 2); for (let z = 1.6; z < p.h; z += 1.6) d += rimFront(P, p.x, p.y, p.w / 2, p.z + z); return d; };
/** Planks on a wooden plate. */
const plankMarks = (top, P, p) => { const X = fx(P, p), Y = fy(P, p); let d = ""; for (let a = -p.w / 2 + 6; a < p.w / 2 - 2; a += 6) d += L2(Y, a, 0.6, a, p.h - 0.6); for (let a = -p.d / 2 + 6; a < p.d / 2 - 2; a += 6) d += L2(X, a, 0.6, a, p.h - 0.6); return d; };

/** A person from parts. poseFn returns { x, y, z, k, suit, color, tone, opacity }. Suits carry a briefcase and wear a tie. */
function person(id, poseFn) {
  const part = (name, f) => body(`${id}-${name}`, (t, c) => f(poseFn(t, c)));
  return [
    part("legs", (q) => ({ x: q.x, y: q.y, z: q.z, w: 5.4 * q.k, d: 3.6 * q.k, h: 7 * q.k, r: 1.6 * q.k, b: 0.6, layer: 1, color: "#2e2926", opacity: q.opacity })),
    part("torso", (q) => ({ x: q.x, y: q.y, z: q.z + 7 * q.k, w: 8 * q.k, d: 5 * q.k, h: 8.5 * q.k, r: 2.4 * q.k, b: 0.6, layer: 1, color: q.color, tone: q.tone,
      marks: q.suit ? (top, P, p) => { const Y = fy(P, p); return L2(Y, 0, p.h - 0.5, 0, p.h * 0.25) + L2(Y, -1.6, p.h - 0.4, 0, p.h - 2.6) + L2(Y, 1.6, p.h - 0.4, 0, p.h - 2.6); } : undefined,
      opacity: q.opacity })),
    part("head", (q) => ({ x: q.x, y: q.y, z: q.z + 16 * q.k, w: 5.6 * q.k, d: 5.6 * q.k, h: 5.4 * q.k, r: 2.8 * q.k, b: 0.6, layer: 1, color: SKIN, opacity: q.opacity })),
    part("case", (q) => ({ x: q.x + 1.5 * q.k, y: q.y - 4.4 * q.k, z: q.z + 2.2 * q.k, w: 6 * q.k, d: 1.8 * q.k, h: 4.6 * q.k, r: 0.8, b: 0.4, layer: 1,
      color: "#4a3324", tone: "hi", opacity: q.suit ? q.opacity : 0 })),
  ];
}

// ---------------------------------------------------------------- feed typography (4:5 carousel, read on a phone)
// Static CSS added to the page; `html body` outranks the engine's selectors.
if (typeof document !== "undefined" && !document.getElementById("sectors-type")) {
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = "https://fonts.googleapis.com/css2?family=Inter+Tight:wght@500..800&family=Inter:wght@400..700&display=swap";
  document.head.appendChild(link);
  const css = document.createElement("style");
  css.id = "sectors-type";
  css.textContent = `
html body .iso[data-tall] .iso-text[data-style=stat]{font-family:"Inter Tight",Inter,sans-serif;font-weight:800;font-size:15cqw;line-height:1;letter-spacing:-.035em}
html body .iso[data-tall] .iso-text[data-style=big]{font-family:"Inter Tight",Inter,sans-serif;font-weight:800;font-size:8.2cqw;line-height:1.02;letter-spacing:-.03em}
html body .iso[data-tall] .iso-text[data-style=title]{font-family:"Inter Tight",Inter,sans-serif;font-weight:600;font-size:4.5cqw;line-height:1.18;letter-spacing:-.015em;color:#e7e5e4}
html body .iso[data-tall] .iso-text[data-style=caption]{font-family:Inter,sans-serif;font-weight:450;font-size:3cqw;line-height:1.35;color:#8a827b;padding-top:.4em}
html body .iso[data-tall] .iso-text[data-style=kicker]{font-family:Inter,sans-serif;font-weight:650;font-size:3cqw;line-height:1.2;letter-spacing:.09em;color:#fdae61;padding-bottom:.5em}
html body .iso .iso-pin{font-family:Inter,sans-serif;font-size:2.9cqw;font-weight:600;padding:.35em .8em}`;
  document.head.appendChild(css);
}

// ---------------------------------------------------------------- framing
/**
 * A camera that fits a finished scene into the band of a feed slide between the headline and
 * the footer, whatever the data made it: few stacks or many, the tallest one first or last.
 * `pts` are world points bounding the scene. The band is in fractions of the view height.
 * Uses the kernel's default view (azimuth 45°, k 0.5), so it matches what the engine draws.
 */
const sceneFit = (pts, { top = 0.43, bottom = 0.8, width = 0.9, maxS = 2.2, cx = 0.5 } = {}) => (view) => {
  const c = Math.SQRT1_2, zf = Math.sqrt(0.75);
  let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
  for (const [x, y, z] of pts) {
    const sx = (x - y) * c, sy = (x + y) * c * 0.5 - z * zf;
    x0 = Math.min(x0, sx); x1 = Math.max(x1, sx); y0 = Math.min(y0, sy); y1 = Math.max(y1, sy);
  }
  const C0 = Math.min(view.w, view.h) / 360; // the engine scales S, dx and dy by this
  const bandH = (bottom - top) * view.h, bandMid = ((top + bottom) / 2) * view.h;
  const S = Math.min(maxS * C0, bandH / (y1 - y0), (width * view.w) / (x1 - x0));
  return { S: S / C0, focus: [0, 0, 0], dx: ((cx - 0.5) * view.w - (S * (x0 + x1)) / 2) / C0, dy: (bandMid - view.h / 2 - (S * (y0 + y1)) / 2) / C0 };
};

/** The screen point (view units) of a world point under a sceneFit camera: the same maths as the kernel's proj + fit. */
const projector = (cam, view) => {
  const C0 = Math.min(view.w, view.h) / 360, S = cam.S * C0, c = Math.SQRT1_2, zf = Math.sqrt(0.75);
  const ox = view.w / 2 + (cam.dx ?? 0) * C0, oy = view.h / 2 + (cam.dy ?? 0) * C0;
  return (x, y, z) => [ox + S * (x - y) * c, oy + S * ((x + y) * c * 0.5 - z * zf)];
};
/**
 * An SVG transform that lays flat content onto a face of the scene: local u runs along world `along`,
 * local v runs down the face (world −z), both in world units. Used for signs, labels and charts on boards.
 */
const faceMatrix = (P, o, along = [1, 0, 0], down = [0, 0, -1]) => {
  const O = P(...o), A = P(o[0] + along[0], o[1] + along[1], o[2] + along[2]), D = P(o[0] + down[0], o[1] + down[1], o[2] + down[2]);
  return `matrix(${A[0] - O[0]} ${A[1] - O[1]} ${D[0] - O[0]} ${D[1] - O[1]} ${O[0]} ${O[1]})`;
};

// ---------------------------------------------------------------- flat overlay (stats stay flat and readable)
// A story sets OVERLAY((view) => svg body); post.mjs lays it over the stage in view units before each shot.
const OVERLAY = (fn) => { globalThis.__OVERLAY__ = (view) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${view.w} ${view.h}" style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none;overflow:visible">${fn(view)}</svg>`; };
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;");
const FONT_H = `font-family="Inter Tight, Inter, sans-serif"`, FONT_B = `font-family="Inter, sans-serif"`;
const txt = (x, y, s, { size = 10, weight = 500, fill = SECTORS.ink, anchor = "start", head = false, ls = 0, extra = "" } = {}) =>
  `<text x="${x}" y="${y}" ${head ? FONT_H : FONT_B} font-size="${size}" font-weight="${weight}" fill="${fill}" text-anchor="${anchor}" letter-spacing="${ls}" ${extra}>${esc(s)}</text>`;
const rect = (x, y, w, h, { fill = "none", stroke = "none", r = 0, sw = 0.6, op = 1 } = {}) =>
  `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}" opacity="${op}"/>`;
const MUTED_BAR = "#57534e", CARD = "#1c1917", CARD_LINE = "#2f2a27", SUBTLE = "#8a827b";

/** A timeline of vertical bars (one per filing). items: [{ value, date, hi }]. Labels the highlighted bar and the date ends. */
function barsV(items, x, y, w, h, accent, { valueLabel = rp } = {}) {
  const n = items.length, gap = Math.min(3, (w / n) * 0.3), bw = (w - gap * (n - 1)) / n;
  const max = Math.max(...items.map((i) => i.value));
  let s = `<line x1="${x}" y1="${y + h}" x2="${x + w}" y2="${y + h}" stroke="${CARD_LINE}" stroke-width="0.8"/>`;
  items.forEach((it, i) => {
    const bh = Math.max(1.2, (it.value / max) * (h - 14)), bx = x + i * (bw + gap);
    s += rect(bx, y + h - bh, bw, bh, { fill: it.hi ? accent : MUTED_BAR, r: Math.min(1.5, bw / 3) });
    if (it.hi) s += txt(bx + bw / 2, y + h - bh - 4, valueLabel(it.value), { size: 8.5, weight: 700, fill: accent, anchor: i > n * 0.7 ? "end" : i < n * 0.3 ? "start" : "middle" });
  });
  const d = (i) => items[i].date ? new Date(items[i].date + "T00:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "short" }) : "";
  s += txt(x, y + h + 9, d(0), { size: 7, fill: SUBTLE }) + txt(x + w, y + h + 9, d(n - 1), { size: 7, fill: SUBTLE, anchor: "end" });
  return s;
}
/** Ranked horizontal bars (one per person). items: [{ label, value, hi }]. Value printed at the end of every bar. */
function barsH(items, x, y, w, h, accent, { valueLabel = rp, labelW = 92 } = {}) {
  const n = items.length, rowH = h / n, max = Math.max(...items.map((i) => i.value)), bw = w - labelW - 46;
  let s = "";
  items.forEach((it, i) => {
    const cy = y + rowH * i + rowH / 2, len = Math.max(1.5, (it.value / max) * bw);
    s += txt(x, cy + 3, it.label.length > 20 ? it.label.slice(0, 19) + "…" : it.label, { size: 8, weight: it.hi ? 650 : 500, fill: it.hi ? SECTORS.ink : SECTORS.muted });
    s += rect(x + labelW, cy - Math.min(5, rowH * 0.3), len, Math.min(10, rowH * 0.6), { fill: it.hi ? accent : MUTED_BAR, r: 1.5 });
    s += txt(x + labelW + len + 4, cy + 3, valueLabel(it.value), { size: 8, weight: 650, fill: it.hi ? accent : SECTORS.muted });
  });
  return s;
}
/** The chart for DATA.chart, whatever its kind. */
const chartOf = (chart, x, y, w, h, accent) => chart.kind === "roster" ? barsH(chart.items, x, y, w, h, accent) : barsV(chart.items, x, y, w, h, accent);
/** A row of stat tiles: [{ value, label, tone }]; tone "accent" colours the value. */
function tiles(items, x, y, w, h, accent, { boxed = true } = {}) {
  const n = items.length, gap = 6, tw = (w - gap * (n - 1)) / n;
  return items.map((it, i) => {
    const tx = x + i * (tw + gap);
    return (boxed ? rect(tx, y, tw, h, { fill: "#231f1c", stroke: CARD_LINE, r: 5 }) : "") +
      txt(tx + 8, y + h * 0.52, it.value, { size: Math.min(17, (tw - 12) / Math.max(4, it.value.length) * 1.9), weight: 800, head: true, ls: -0.4, fill: it.tone === "accent" ? accent : SECTORS.ink }) +
      txt(tx + 8, y + h * 0.82, it.label, { size: 6.8, weight: 550, fill: SUBTLE, ls: 0.3 });
  }).join("");
}

/** Compact rupiah: 61750000000 → "Rp 61.8 B". */
const rp = (v) => {
  const a = Math.abs(v);
  const [d, u] = a >= 1e12 ? [1e12, "T"] : a >= 1e9 ? [1e9, "B"] : a >= 1e6 ? [1e6, "M"] : [1, ""];
  const n = a / d;
  return `Rp ${n >= 100 ? n.toFixed(0) : n.toFixed(1).replace(/\.0$/, "")}${u ? " " + u : ""}`;
};
