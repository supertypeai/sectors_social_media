// Insider "people" cover: the holder's name set big like a magazine cover line, one sentence on the deal, and
// the company drawn as 100 seats (1 seat = 1% of the shares) so the size of the move is seen, not read.
// DATA.slide: { holder{name,sym,logo,initials}, other?, headline, accent[], sym, before, after, sell,
//               otherBefore?, otherAfter?, value, span, year }
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);
grain(0.05);

function badge(cx, cy, r, b, { ring = "var(--acc)" } = {}) {
  if (b.logo) { logoChip(svg, cx, cy, r, b.logo, b.sym); return; }
  mk("circle", { cx, cy, r, style: `fill:${TONE.card};stroke:${ring};stroke-width:1.1px` }, svg);
  type(svg, cx, cy + r * 0.34, b.initials, "label", { size: r * 0.9, weight: 600, anchor: "middle", fill: TONE.hi });
}

// ---------------------------------------------------------------- the person
const role = S.other ? "THE BUYER" : S.sell ? "THE SELLER" : "THE BUYER";
badge(M + 13, 66, 13, S.holder);
type(svg, M + 34, 63, role, "caps", { fill: "var(--acc)", weight: 750 });
type(svg, M + 34, 74, S.holder.sym ? `Listed as ${S.holder.sym}` : "Insider of " + S.sym, "label", { fill: TONE.muted, size: 7 });

// the name: as big as fits in two lines
let size = 50, lines;
for (; size > 26; size -= 2) {
  lines = wrapText(S.holder.name, size, W - 2 * M, 0.5);
  if (lines.length <= 2 && Math.max(...lines.map((l) => l.length)) * size * 0.5 <= W - 2 * M) break;
}
let y = 96 + size * 0.85;
for (const l of lines) { type(svg, M - 2, y, l, "hero", { size, weight: 330 }); y += size * 0.98; }
// the sub-line under the name: one sentence, smaller than the name, the stake in the accent
{
  const hs = 17, hl = wrapText(S.headline, hs, W - 2 * M, 0.47);
  y += 6;
  for (const l of hl) {
    const t = type(svg, M, y, "", "title", { size: hs, weight: 500 });
    t.innerHTML = l.split(" ").map((w) => S.accent.includes(w) ? `<tspan style="fill:var(--acc)">${esc(w)}</tspan>` : esc(w)).join(" ");
    y += hs * 1.18;
  }
}
y += 10;

// ---------------------------------------------------------------- 100 seats
const nNow = Math.round(S.after), nWas = Math.round(S.before);
const nGone = S.sell ? Math.max(0, nWas - nNow) : 0;
const nOld = !S.sell ? Math.min(nWas, nNow) : 0; // a buyer's seats from before the deal
const nOther = S.other ? Math.round(S.otherAfter) : 0;
const seats = [];
for (let i = 0; i < nNow; i++) seats.push(i < nOld ? "old" : "now");
for (let i = 0; i < nGone; i++) seats.push("gone");
for (let i = 0; i < nOther; i++) seats.push("other");
while (seats.length < 100) seats.push("rest");

const step = Math.min(15, (418 - 30 - y) / 10), r = step * 0.34, gx = M + r + 1, gy = y + r;
const g = mk("g", {}, svg);
seats.slice(0, 100).forEach((k, i) => {
  const cx = gx + (i % 10) * step, cy = gy + Math.floor(i / 10) * step;
  const st = k === "now" ? "fill:var(--acc);stroke:none"
    : k === "old" ? "fill:var(--acc);fill-opacity:.45;stroke:none"
    : k === "gone" ? "fill:none;stroke:var(--acc);stroke-width:.9px;stroke-dasharray:1.6 1.4"
    : k === "other" ? `fill:${TONE.edge};stroke:none`
    : `fill:${TONE.lo};stroke:none`;
  mk("circle", { cx, cy, r, style: st }, g);
});

// ---------------------------------------------------------------- the legend, beside the seats
const lx = gx + 10 * step + 8;
let ly = gy + 2;
type(svg, lx, ly, `1 seat = 1% of ${S.sym}`, "caps", { fill: TONE.faint, size: 6 });
ly += 22;
const pct = (v) => `${v.toFixed(2)}%`;
const items = [];
if (S.sell) {
  items.push([nNow, nNow ? "seats kept" : "seats left", `${pct(S.after)} now`, "fill:var(--acc);stroke:none"]);
  items.push([nGone, "seats sold", `was ${pct(S.before)}`, "fill:none;stroke:var(--acc);stroke-dasharray:1.6 1.4"]);
} else {
  const src = S.other ? `from ${S.other.name.split(" ").slice(0, 2).join(" ")}` : S.before > 0.005 ? `was ${pct(S.before)}` : "from 0%";
  items.push([nNow, S.before > 0.005 ? "seats now" : "new seats", src, "fill:var(--acc);stroke:none"]);
}
if (S.other) {
  const short = S.other.name.split(" ").slice(0, 2).join(" ");
  items.push([nOther, `still with ${short}`, `was ${pct(S.otherBefore)}`, `fill:${TONE.edge};stroke:none`]);
}
for (const [n, a, b, st] of items) {
  mk("circle", { cx: lx + 3.5, cy: ly - 8, r: 3.2, style: st }, svg);
  typeRun(svg, lx + 12, ly, [[String(n), 24, 300, TONE.hi]]);
  type(svg, lx + 12 + String(n).length * 13 + 4, ly - 9, a, "label", { size: 7.4, weight: 600 });
  type(svg, lx + 12 + String(n).length * 13 + 4, ly + 0.5, b, "label", { size: 6.8, fill: TONE.muted });
  ly += 30;
}

// the money and the date, set as a byline under the legend
const by = gy + 9 * step + r;
mk("line", { x1: lx, y1: by - 20, x2: W - M, y2: by - 20, class: "lo thin" }, svg);
typeRun(svg, lx, by - 2, [[S.value, 15, 400, "var(--acc)"]]);
type(svg, W - M, by - 2, `${S.span} ${S.year}`, "label", { size: 7, fill: TONE.muted, anchor: "end" });
