// Object A, simple: the company is one column; only two things on it, the stake that moved (bright, lifted
// off) and the rest. One label each. The sentence says it plainly. Same DATA.slide as stake_split.
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

const moved = S.sold.pct;
// type: number, one plain sentence, one quiet line
typeRun(svg, M - 3, 128, [[S.hero.num, 92, 220], [S.hero.unit, 40, 250, TONE.muted]]);
const sentence = S.deal ? `of ${S.name} changed owner in one deal` : `of ${S.name} was ${S.verb} by ${S.holder}`;
let y = para(svg, M, 162, sentence, "title", { accent: S.deal ? [] : S.holder.split() });
const line = S.deal ? `${S.seller} → ${S.holder}` : `Stake ${S.before.toFixed(2)}% → ${S.after.toFixed(2)}%`;
type(svg, M, y + 18, line, "body", { fill: TONE.muted });

// the object: one column, 100% tall; the moved slab lifted straight up and a little back
const R = 36, TALL = 120, zOf = (p) => (p / 100) * TALL;
const REST = zOf(100 - moved), LIFT = { x: 0, y: -26, z: 30 };
const K = camera(0.95, [[-R, -R, 0], [R, R, 0], [LIFT.x - R, LIFT.y - R, TALL + LIFT.z], [R, R, TALL + LIFT.z]], 180, 318);
const [ring, inner] = disc(0, 0, R), [ringL, innerL] = disc(LIFT.x, LIFT.y, R);
const g = mk("g", {}, svg);
mirror(g, K, ring, 0, 22);
slab(g, K, ringL, innerL, REST + LIFT.z, TALL + LIFT.z, "acc");
slab(g, K, ring, inner, 0, REST, "sil");
mk("path", { d: poly(ringAt(K.P, ring, TALL)), class: "dash nf" }, g); // where the stake used to sit

// two labels, set well clear of the column
const top = K.P(R * 0.707, -R * 0.707 + LIFT.y, (REST + TALL) / 2 + LIFT.z);
leader(g, top, [W - M - 64, top[1] - 6], [[`${moved.toFixed(1)}% ${S.verb}`, "label", { fill: "var(--acc)", weight: 700, size: 11 }], [S.day, "label", { fill: TONE.muted, size: 7.4 }]], { cls: "dash nf acc" });
const rest = K.P(-R * 0.707, R * 0.707, REST / 2);
leader(g, rest, [M + 70, rest[1]], [[`${(100 - moved).toFixed(1)}%`, "label", { fill: TONE.muted, weight: 650, size: 11 }], ["the rest", "label", { fill: TONE.faint, size: 7.4 }]], { anchor: "end" });
