// Object B, before → after: two identical columns of the company, side by side. In each, the holder's
// stake is the bright band at the top; you see it shrink (or appear) without reading. Same DATA.slide.
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

typeRun(svg, M - 3, 128, [[S.hero.num, 92, 220], [S.hero.unit, 40, 250, TONE.muted]]);
const sentence = S.deal ? `of ${S.name} changed owner in one deal` : `of ${S.name} was ${S.verb} by ${S.holder}`;
let y = para(svg, M, 162, sentence, "title", { accent: S.deal ? [] : S.holder.split() });
type(svg, M, y + 18, S.deal ? `${S.seller} → ${S.holder}` : `in one filing, on ${S.day}`, "body", { fill: TONE.muted });

// two columns along the camera's x axis, so they sit side by side on screen
const R = 27, TALL = 110, GAP = 92, zOf = (p) => (p / 100) * TALL;
const cols = [{ x: -GAP / 2, pct: S.before, label: "Before" }, { x: GAP / 2, pct: S.after, label: "After" }];
const at = (x) => [x * 0.7071, -x * 0.7071]; // a ground point that moves only sideways on screen
const K = camera(1.12, cols.flatMap((c) => { const [cx, cy] = at(c.x); return [[cx - R, cy - R, 0], [cx + R, cy + R, 0], [cx, cy, TALL]]; }), 180, 296);
const g = mk("g", {}, svg);
for (const c of cols) {
  // shift the column sideways on screen: +x and −y together keep it on the same ground row
  const [cx, cy] = at(c.x);
  const [ring, inner] = disc(cx, cy, R);
  mirror(g, K, ring, 0, 18);
  const z1 = TALL - zOf(c.pct);
  slab(g, K, ring, inner, 0, z1, "sil");
  if (c.pct > 0.01) slab(g, K, ring, inner, z1, TALL, "acc");
  else mk("path", { d: poly(ringAt(K.P, ring, TALL)), class: "dash nf" }, g);
  // the numbers under each column, flat and large
  const [bx, by] = K.P(cx + R * 0.707, cy + R * 0.707, 0);
  type(g, bx - 2, by + 26, `${c.pct.toFixed(2)}%`, "num", { size: 22, weight: 300, anchor: "middle", fill: c.label === "After" ? "var(--acc)" : TONE.hi });
  type(g, bx - 2, by + 38, c.label.toUpperCase(), "caps", { fill: TONE.muted, anchor: "middle" });
}
