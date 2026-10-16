// Hook: a company drawn as a column of its shares, 100% tall, cut into who owns what. The stake that was
// sold is lifted off the top and set aside, bright in the accent; the slot it left is a dashed ghost.
// DATA.slide: { hero, title, accent[], line, segments: [{ pct, label, sub, kind: "other"|"kept" }] (bottom
// up), sold: { pct, label, sub } }.
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

// ---------------------------------------------------------------- the column
const R = 30, TALL = 128, zOf = (pct) => (pct / 100) * TALL; // 100% of the company is 150 units tall
const segs = [];
let z = 0;
for (const s of S.segments) { segs.push({ ...s, z0: z, z1: z + zOf(s.pct) }); z += zOf(s.pct); }
const SOLD0 = z, SOLD1 = z + zOf(S.sold.pct); // where the sold stake sat
const LIFT = { x: 10, y: -52, z: 22 }; // set aside: up and back, so the column stays in front of it
const K = camera(0.98, [[-R, -R, 0], [R, R, 0], [0, 0, SOLD1], [LIFT.x + R, LIFT.y - R, SOLD1 + LIFT.z], [LIFT.x - R, LIFT.y + R, SOLD0 + LIFT.z]], 214, 330);
const [ring, inner] = disc(0, 0, R), [ringL, innerL] = disc(LIFT.x, LIFT.y, R);

const scene = mk("g", {}, svg);
floor(scene, K, -110, -130, 90, 80, 9);
mirror(scene, K, ring, 0, 26);
// the lifted stake: farther from us than the column, so it is painted first
slab(scene, K, ringL, innerL, SOLD0 + LIFT.z, SOLD1 + LIFT.z, "acc");
// the column, bottom up; each owner's band is its own slab, so every boundary is a seam
for (const s of segs) slab(scene, K, ring, inner, s.z0, s.z1, s.kind === "kept" ? "hi" : "sil");
// the empty slot: a dashed ghost of the stake that left, and the drops that say where it went
const ghostG = mk("g", {}, scene);
mk("path", { d: poly(hull(ringAt(K.P, ring, SOLD0).concat(ringAt(K.P, ring, SOLD1)))), class: "dash nf" }, ghostG);
mk("path", { d: poly(ringAt(K.P, ring, SOLD1)), class: "dash nf" }, ghostG);
for (const a of [Math.PI * 0.75, -Math.PI * 0.25]) {
  const px = Math.cos(a) * R, py = Math.sin(a) * R;
  mk("path", { d: `M${K.P(px, py, SOLD1).join(" ")}L${K.P(px + LIFT.x, py + LIFT.y, SOLD1 + LIFT.z).join(" ")}`, class: "dash nf" }, ghostG);
}

// ---------------------------------------------------------------- leaders: what each band is
const leftAt = (zz) => K.P(-R * 0.707, R * 0.707, zz);
let ly = 0;
segs.slice().reverse().forEach((s, i) => {
  const from = leftAt((s.z0 + s.z1) / 2);
  const to = [M + 96, Math.max(from[1], ly + 30)]; // room for a trimmed 26-character label inside the margin
  ly = to[1];
  leader(scene, from, to, [[`${s.pct.toFixed(2)}%`, "label", { fill: s.kind === "kept" ? TONE.hi : TONE.muted, weight: 650, size: 10 }], [s.label, "label", { fill: TONE.faint, size: 7 }]], { anchor: "end" });
});
const soldAt = K.P(LIFT.x + R * 0.707, LIFT.y - R * 0.707, (SOLD0 + SOLD1) / 2 + LIFT.z);
leader(scene, soldAt, [W - M - 50, soldAt[1] - 26], [[`${S.sold.pct.toFixed(2)}%`, "label", { fill: "var(--acc)", weight: 700, size: 10 }], [S.sold.label, "label", { fill: TONE.muted, size: 7 }]], { cls: "dash nf acc" });

// ---------------------------------------------------------------- type: the hook
const hero = typeRun(svg, M - 3, 128, [[S.hero.num, 92, 220], [S.hero.unit, 40, 250, TONE.muted]]);
let y = para(svg, M, 160, S.title, "title", { accent: S.accent, maxW: W - 2 * M });
type(svg, M, y + 17, S.line, "body", { fill: TONE.muted });
