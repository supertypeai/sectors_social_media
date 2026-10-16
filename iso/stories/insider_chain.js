// Insider chain, "the ledger" object: one banknote stack per filing, in date order on a ledger
// plate, each as tall as its rupiah value. A streak reads as a row; one outsized buy towers over it.
// DATA is pasted above this file by post.mjs (see image_generator/iso_render.py for its shape).
//
//  t        what moves
//  0–1.8    the stacks rise one by one, left to right (date order)
//  1.8–2.4  the biggest stack lands last; pins appear
//  2.4–3.0  held: the still for the carousel is taken at the end

const PTS = DATA.points, NP = PTS.length;
const MAXV = Math.max(...PTS.map((p) => p.value));
const BIG = PTS.findIndex((p) => p.value === MAXV);
const SELL = DATA.direction === "sell";
const ACCENT = SELL ? SECTORS.rose : SECTORS.teal; // colour is earned: buying teal, selling rose
const STEP = Math.min(15, 220 / NP), BW = Math.min(12, STEP * 0.78), BD = 16;
const TALL = 72; // the biggest stack, in world units
const hOf = (v) => Math.max(1.4, (v / MAXV) * TALL);
const xOf = (i) => (i - (NP - 1) / 2) * STEP;
const SPAN = (NP - 1) * STEP + BW;
const appearAt = (i) => 0.15 + (i === BIG ? 1.75 : (1.5 * i) / Math.max(1, NP - 1));

const plate = body("ledger", () => ({
  x: 0, y: 0, z: 0, w: SPAN + 18, d: BD + 14, h: 3, r: 2, b: 1, layer: 0, color: "#231f1c", side: "#171412", tone: "hi",
  // a date ruler along the front edge: one tick per filing, a long tick at each month change
  marks: (top, P, p) => {
    let d = "";
    PTS.forEach((q, i) => {
      const newMonth = i === 0 || q.date.slice(0, 7) !== PTS[i - 1].date.slice(0, 7);
      d += seg(top(xOf(i), p.d / 2 - 1.2), top(xOf(i), p.d / 2 - (newMonth ? 5 : 2.8)));
    });
    return d + seg(top(-p.w / 2 + 3, p.d / 2 - 1.2), top(p.w / 2 - 3, p.d / 2 - 1.2));
  },
}));

const stacks = PTS.map((q, i) =>
  body(`stack-${i}`, (t) => {
    const t0 = appearAt(i), p = prog(t, t0, t0 + 0.5, ease.lift);
    const h = hOf(q.value), big = i === BIG;
    return {
      x: xOf(i), y: -1, z: 3 + 18 * (1 - p), w: BW, d: BD, h, r: 0.8, b: 0.6, layer: 2,
      color: big ? NOTE : "#7f9e7c", side: big ? NOTE_S : "#5b7558", tone: big ? "accent" : "base",
      marks: bundleMarks(big ? 6 : Math.max(h, 1.4), true), opacity: prog(t, t0, t0 + 0.2),
    };
  }),
);

const bigH = hOf(MAXV);
const smallIdx = PTS.map((_, i) => i).filter((i) => i !== BIG);
const midSmall = smallIdx[Math.floor(smallIdx.length / 2)] ?? 0;

// Every world point that bounds the finished scene: plate corners and stack tops (+ room for the big pin).
const BOUNDS = [
  ...[-1, 1].flatMap((sx) => [-1, 1].map((sy) => [sx * (SPAN + 18) / 2, sy * (BD + 14) / 2, 0])),
  ...PTS.flatMap((q, i) => [[xOf(i) - BW / 2, -1 - BD / 2, 3 + hOf(q.value)], [xOf(i) + BW / 2, -1 + BD / 2, 3 + hOf(q.value)]]),
  [xOf(BIG), -1, 3 + bigH + 14],
];
const camFit = sceneFit(BOUNDS);

export default ISO.story({
  name: "insider-chain",
  duration: 3,
  aspect: "4:5",
  backdrop: "grid",
  theme: { ...SECTORS_THEME, accent: ACCENT },
  brand: { name: "Sectors", accent: ACCENT, font: "\"Inter Tight\", Inter, ui-sans-serif, system-ui, sans-serif", watermark: true },
  bodies: [plate, ...stacks],
  camera: (t, { view }) => camFit(view),
  pins: (t) => [
    { id: "p-big", at: [xOf(BIG), -1, 3 + bigH + 2], text: DATA.copy.pinBig, tone: "accent", show: win(t, 2.1, 9, 0.2) },
    { id: "p-small", at: [xOf(midSmall), -1, 3 + hOf(PTS[midSmall].value) + 3], text: DATA.copy.pinSmall, show: DATA.copy.pinSmall && NP >= 8 ? win(t, 2.2, 9, 0.2) : 0 }, // short rows: the pins would touch
  ],
  texts: [
    { t0: 0, text: DATA.copy.kicker, style: "kicker", at: "top", group: "head", anim: "none" },
    { t0: 0, text: DATA.copy.headline, style: "big", group: "head", anim: "none", emphasis: DATA.copy.emphasis },
    { t0: 0, text: DATA.copy.sub, style: "title", group: "head", anim: "none" },
    { t0: 0, text: DATA.copy.stat, style: "title", at: [50, 87], group: "foot", anim: "none", emphasis: DATA.copy.statEmphasis },
    { t0: 0, text: DATA.copy.source, style: "caption", group: "foot", anim: "none" },
  ],
  poster: 2.9,
});
