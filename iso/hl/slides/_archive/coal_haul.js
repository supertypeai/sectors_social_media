// Hook object for a coal company: the company is a terraced coal stockpile; the stake that changed hands
// is the load on a haul truck driving away from it, in the accent. You read "a big piece of this company
// was carted off" before you read a word. Same DATA.slide as stake_split (hero, title/sentence fields,
// sold, before/after, holder, name, verb, deal, seller, day).
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

const moved = S.sold.pct;
typeRun(svg, M - 3, 124, [[S.hero.num, 88, 220], [S.hero.unit, 36, 250, TONE.muted]]);
const sentence = S.deal ? `of ${S.name} changed owner in one deal` : `of ${S.name} was ${S.verb} by ${S.holder}`;
let y = para(svg, M, 156, sentence, "title", { accent: S.deal ? [] : S.holder.split() });
type(svg, M, y + 17, S.deal ? `${S.seller} → ${S.holder}` : `Stake ${S.before.toFixed(2)}% → ${S.after.toFixed(2)}%`, "body", { fill: TONE.muted });

// ---------------------------------------------------------------- geometry (world units, z up)
const TER = [[50, 0, 8], [41, 8, 16], [32, 16, 24], [23, 24, 31], [14, 31, 37]]; // stockpile benches: radius, z0, z1
const T = { x: 96, y: 30 }; // the truck, front-right of the pile and nearer to us
const box = (x0, y0, x1, y1, r = 2, b = 1.2) => rings(x0, y0, x1, y1, r, b);
const K = camera(1.38, [[-50, -50, 0], [50, 50, 0], [0, 0, 37], [T.x - 34, T.y - 16, 0], [T.x + 34, T.y + 16, 0], [T.x, T.y, 46]], 186, 318);
const g = mk("g", {}, svg);
floor(g, K, -70, -70, 130, 70, 9);

// the pile, bottom bench first; the top bench carries a scatter of lumps
mirror(g, K, disc(0, 0, 50)[0], 0, 16);
for (const [R, z0, z1] of TER) { const [ring, inner] = disc(0, 0, R, 1.6, 56); slab(g, K, ring, inner, z0, z1, "sil"); }
for (const [lx, ly, lr] of [[-4, 3, 3], [5, -2, 2.4], [1, 7, 2], [-7, -5, 2.2]]) {
  const [ring, inner] = disc(lx, ly, lr, 0.6, 16);
  slab(g, K, ring, inner, 37, 39.2, "sil");
}
// the haul road: two dashed ruts from the pile to the truck
for (const dy of [-8, 8]) mk("path", { d: `M${K.P(40, 26 + dy, 0).join(" ")}L${K.P(T.x - 34, T.y + dy, 0).join(" ")}`, class: "dash nf" }, g);

// ---------------------------------------------------------------- the truck (painted far to near)
const wheel = (cx, cy, r, cls = "sil") => {
  // a wheel stands in the x–z plane: project its rim ourselves, the kernel only extrudes along z
  const rim = [], hub = [];
  for (let k = 0; k < 28; k++) {
    const a = (k / 28) * Math.PI * 2;
    rim.push(K.P(cx + Math.cos(a) * r, cy, r + Math.sin(a) * r));
    hub.push(K.P(cx + Math.cos(a) * r * 0.45, cy + 0.2, r + Math.sin(a) * r * 0.45));
  }
  mk("path", { d: poly(rim), class: cls }, g);
  mk("path", { d: poly(hub), class: "nf lo" }, g);
};
// a mining haul truck: big wheels, a low chassis, a cab at the front, and a long, tall dump body
// whose canopy reaches forward over the cab
for (const wx of [T.x - 22, T.x + 20]) wheel(wx, T.y - 15, 10, "lo");  // far wheels, mostly hidden
const [chR, chI] = box(T.x - 34, T.y - 13, T.x + 32, T.y + 13, 2);
slab(g, K, chR, chI, 10, 15, "sil");                                    // chassis
const [cbR, cbI] = box(T.x + 18, T.y - 12, T.x + 32, T.y + 2, 3);
slab(g, K, cbR, cbI, 15, 29, "sil");                                    // cab, on the near-left corner
mk("path", { d: poly([K.P(T.x + 32.05, T.y - 9, 27), K.P(T.x + 32.05, T.y - 1, 27), K.P(T.x + 32.05, T.y - 1, 21), K.P(T.x + 32.05, T.y - 9, 21)]), class: "nf lo" }, g); // windscreen
const [bdR, bdI] = box(T.x - 34, T.y - 15, T.x + 14, T.y + 15, 4, 1.6);
slab(g, K, bdR, bdI, 15, 34, "acc");                                    // dump body
const [cnR, cnI] = box(T.x + 14, T.y - 15, T.x + 32, T.y + 15, 2, 1);
slab(g, K, cnR, cnI, 32, 34, "acc");                                    // canopy over the cab
for (const [R, z0, z1, ox] of [[15, 34, 38, -10], [10, 38, 41, -9], [5, 41, 43, -8]]) { // the load
  const [lr, li] = disc(T.x + ox, T.y, R, 1, 36);
  slab(g, K, lr, li, z0, z1, "acc");
}
for (const wx of [T.x - 22, T.x + 20]) wheel(wx, T.y + 15, 10);        // near wheels

// ---------------------------------------------------------------- two labels
const loadAt = K.P(T.x - 10, T.y - 15, 40);
leader(g, loadAt, [W - M - 70, loadAt[1] - 30], [[`${moved.toFixed(1)}% ${S.verb}`, "label", { fill: "var(--acc)", weight: 700, size: 11 }], [S.day, "label", { fill: TONE.muted, size: 7.4 }]], { cls: "dash nf acc" });
const pileAt = K.P(-35, 35, 6);
leader(g, pileAt, [M + 60, pileAt[1] + 6], [[`${(100 - moved).toFixed(1)}%`, "label", { fill: TONE.muted, weight: 650, size: 11 }], ["the rest", "label", { fill: TONE.faint, size: 7.4 }]], { anchor: "end" });
