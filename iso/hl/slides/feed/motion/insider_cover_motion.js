// Insider cover, animated (slide 1 as a video). PROG 0 → 1:
//   0.00–0.25  the holder's name and sentence slide in
//   0.20–0.50  the 100 seats appear row by row; the holder's old stake fills in (sell) / is empty (new buyer)
//   0.50–0.85  the move happens: sold seats fade to dashed rings one by one (sell) or new seats light up (buy),
//              while the stake counter ticks from before to after
//   0.85–1.00  the legend and the money settle; the finished frame is the still cover
// DATA.slide: same as vp_cover { holder{name,sym,logo,initials}, other?, headline, accent[], sym, before, after,
//              sell, otherBefore?, otherAfter?, value, span, year }
const D = DATA, S = D.slide;
setAccent(D.direction);
const P = typeof PROG === "number" ? PROG : 1;
const win = (a, b) => Math.max(0, Math.min(1, (P - a) / (b - a)));
const ease = (t) => 1 - Math.pow(1 - t, 3);
frame(D);
grain(0.05);

const badge = (g, cx, cy, r, b) => {
  if (b.logo) return logoChip(g, cx, cy, r, b.logo, b.sym);
  mk("circle", { cx, cy, r, style: `fill:${TONE.card};stroke:var(--acc);stroke-width:1.1px` }, g);
  type(g, cx, cy + r * 0.34, b.initials, "label", { size: r * 0.9, weight: 600, anchor: "middle", fill: TONE.hi });
};
const h = ease(win(0, 0.25)), hg = mk("g", { opacity: h, transform: `translate(${(1 - h) * -14} 0)` }, svg);
const role = S.other ? "THE BUYER" : S.sell ? "THE SELLER" : "THE BUYER";
badge(hg, M + 13, 66, 13, S.holder);
type(hg, M + 34, 63, role, "caps", { fill: "var(--acc)", weight: 750 });
type(hg, M + 34, 74, S.holder.sym ? `Listed as ${S.holder.sym}` : "Insider of " + S.sym, "label", { fill: TONE.muted, size: 7 });
let size = 50, lines;
for (; size > 26; size -= 2) {
  lines = wrapText(S.holder.name, size, W - 2 * M, 0.5);
  if (lines.length <= 2 && Math.max(...lines.map((l) => l.length)) * size * 0.5 <= W - 2 * M) break;
}
let y = 96 + size * 0.85;
for (const l of lines) { type(hg, M - 2, y, l, "hero", { size, weight: 330 }); y += size * 0.98; }
y += 6;
for (const l of wrapText(S.headline, 17, W - 2 * M, 0.47)) {
  const t = type(hg, M, y, "", "title", { size: 17, weight: 500 });
  t.innerHTML = l.split(" ").map((w) => S.accent.includes(w) ? `<tspan style="fill:var(--acc)">${esc(w)}</tspan>` : esc(w)).join(" ");
  y += 17 * 1.18;
}
y += 10;

// seats: final role of each, plus whether it is part of the move
const nNow = Math.round(S.after), nWas = Math.round(S.before);
const nGone = S.sell ? Math.max(0, nWas - nNow) : 0, nOld = !S.sell ? Math.min(nWas, nNow) : 0;
const nOther = S.other ? Math.round(S.otherAfter) : 0, nOtherWas = S.other ? Math.round(S.otherBefore) : 0;
const seats = [];
for (let i = 0; i < nNow; i++) seats.push(i < nOld ? "old" : S.sell ? "now" : "new");
for (let i = 0; i < nGone; i++) seats.push("gone");
for (let i = 0; i < nOther; i++) seats.push("other");
while (seats.length < 100) seats.push("rest");
const moved = seats.map((k, i) => (k === "gone" || k === "new" ? i : -1)).filter((i) => i >= 0);
const mt = win(0.5, 0.85);
const step = Math.min(15, (418 - 30 - y) / 10), r = step * 0.34, gx = M + r + 1, gy = y + r;
const appear = win(0.2, 0.5);
seats.slice(0, 100).forEach((k, i) => {
  const row = Math.floor(i / 10), a = ease(Math.max(0, Math.min(1, appear * 12 - row)));
  if (a <= 0) return;
  // has this seat's part of the move happened yet? (the moved seats go one after another)
  const mi = moved.indexOf(i), done = mi >= 0 && mt * moved.length > mi;
  let st;
  if (k === "gone") st = done ? "fill:none;stroke:var(--acc);stroke-width:.9px;stroke-dasharray:1.6 1.4" : "fill:var(--acc);stroke:none";
  else if (k === "new") st = done ? "fill:var(--acc);stroke:none" : `fill:${TONE.lo};stroke:none`;
  else if (k === "now") st = "fill:var(--acc);stroke:none";
  else if (k === "old") st = "fill:var(--acc);fill-opacity:.45;stroke:none";
  else if (k === "other") st = `fill:${TONE.edge};stroke:none`;
  else st = `fill:${TONE.lo};stroke:none`;
  const cx = gx + (i % 10) * step, cy = gy + row * step;
  mk("circle", { cx, cy, r: r * (0.6 + 0.4 * a), style: st, opacity: a }, svg);
});

// the stake counter beside the seats, ticking during the move
const lx = gx + 10 * step + 8, cur = S.before + (S.after - S.before) * ease(mt);
const cg = mk("g", { opacity: ease(win(0.25, 0.45)) }, svg);
type(cg, lx, gy + 2, `1 seat = 1% of ${S.sym}`, "caps", { fill: TONE.faint, size: 6 });
type(cg, lx, gy + 26, S.sell ? "STAKE" : "STAKE NOW", "caps", { fill: TONE.muted, size: 6, weight: 750 });
typeRun(cg, lx, gy + 58, [[cur.toFixed(2), 30, 400, "var(--acc)"], ["%", 14, 400, TONE.muted]]);
type(cg, lx, gy + 72, `from ${S.before.toFixed(2)}%`, "label", { fill: TONE.muted, size: 7.4 });
// the money and date settle in last
const fg = mk("g", { opacity: ease(win(0.85, 1)) }, svg), by = gy + 9 * step + r;
mk("line", { x1: lx, y1: by - 20, x2: W - M, y2: by - 20, class: "lo thin" }, fg);
typeRun(fg, lx, by - 2, [[S.value, 15, 400, "var(--acc)"]]);
type(fg, W - M, by - 2, `${S.span} ${S.year}`, "label", { size: 7, fill: TONE.muted, anchor: "end" });
