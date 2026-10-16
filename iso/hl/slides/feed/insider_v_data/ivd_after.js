// Insider "story of the deal", slide 5: what changed. The owner table before and after as two 100% bars
// (the mover in the accent), each holder's before → after, the filings around this one, then the question.
// DATA.slide: { title, accent[], rows: [{name, before, after, mover}], related: [{date, name, buy, pp, price}],
//               question, cta, buyerUnknown }
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

const y = para(svg, M, 74, S.title, "title", { accent: S.accent, maxW: W - 2 * M });

// ---------------------------------------------------------------- two bars, 100% each
const x0 = M + 40, x1 = W - M, xs = scale(0, 100, x0, x1);
const greys = [TONE.edge, TONE.mid, "#5c554f", TONE.lo];
const order = [...S.rows].sort((a, b) => b.mover - a.mover); // the mover first, at the left
function bar(by, key, label) {
  type(svg, M, by + 9, label, "label", { fill: TONE.muted, size: 7.5, weight: 600 });
  let x = x0, gi = 0;
  for (const r of order) {
    const w = xs(r[key]) - x0;
    if (w <= 0) { if (!r.mover) gi++; continue; }
    const fill = r.mover ? "var(--acc)" : greys[gi++ % greys.length];
    mk("rect", { x, y: by, width: Math.max(0.8, w - 1.2), height: 13, style: `fill:${fill};stroke:none` }, svg);
    if (w > 26) type(svg, x + 4, by + 9.3, `${r[key].toFixed(r[key] >= 10 ? 0 : 1)}%`, "label", { size: 7, weight: 700, fill: r.mover ? TONE.ground : TONE.ground });
    x += w;
  }
  mk("rect", { x, y: by, width: Math.max(0, x1 - x), height: 13, style: `fill:none;stroke:${TONE.mid};stroke-width:.8px;stroke-dasharray:2 2` }, svg);
}
const BY = y + 30;
bar(BY, "before", "Before");
bar(BY + 22, "after", "After");

// ---------------------------------------------------------------- each holder, before → after
let ly = BY + 60;
let gi = 0;
for (const r of order) {
  const fill = r.mover ? "var(--acc)" : greys[gi++ % greys.length];
  mk("rect", { x: M, y: ly - 6.5, width: 7, height: 7, rx: 1.5, style: `fill:${fill};stroke:none` }, svg);
  const nm = r.name.length > 30 ? r.name.slice(0, 29) + "…" : r.name;
  type(svg, M + 12, ly, nm, "label", { size: 8.4, weight: r.mover ? 650 : 500, fill: r.mover ? TONE.hi : TONE.muted });
  const f = (v) => `${+v.toFixed(2)}%`, same = f(r.before) === f(r.after);
  type(svg, W - M, ly, `${f(r.before)} → ${f(r.after)}`, "label", { size: 8.4, weight: 650, anchor: "end", fill: same ? TONE.faint : r.mover ? "var(--acc)" : TONE.hi });
  ly += 15;
}
const rest = 100 - S.rows.reduce((s, r) => s + r.after, 0);
mk("rect", { x: M + 0.5, y: ly - 6, width: 6, height: 6, rx: 1.5, style: `fill:none;stroke:${TONE.mid};stroke-width:.8px;stroke-dasharray:2 1.5` }, svg);
type(svg, M + 12, ly, S.buyerUnknown ? "Everyone else, incl. buyers not yet filed" : "Everyone else (public and small holders)", "label", { size: 8.4, fill: TONE.faint });
type(svg, W - M, ly, `${rest.toFixed(1)}%`, "label", { size: 8.4, weight: 600, anchor: "end", fill: TONE.faint });
ly += 12;

// ---------------------------------------------------------------- the filings around it
if (S.related.length) {
  ly += 14;
  mk("line", { x1: M, y1: ly - 12, x2: W - M, y2: ly - 12, class: "lo thin" }, svg);
  // one name throughout (a seller letting go in steps): the name goes in the heading, once
  const one = S.related.every((r) => r.name === S.related[0].name) && S.related.length > 1;
  const head = one ? `How ${S.related[0].name.length > 30 ? S.related[0].name.split(" ").slice(0, 2).join(" ") : S.related[0].name} sold` : "Around the same days";
  type(svg, M, ly + 2, head, "caps", { fill: TONE.muted });
  ly += 17;
  for (const r of S.related) {
    type(svg, M, ly, r.date, "label", { size: 7.6, fill: TONE.faint });
    const nm = one ? "" : r.name.length > 26 ? r.name.slice(0, 25) + "…" : r.name;
    type(svg, M + 34, ly, nm, "label", { size: 7.8, fill: TONE.hi });
    type(svg, W - M, ly, `${r.buy ? "bought" : "sold"} ${r.pp >= 1 ? r.pp.toFixed(1) : r.pp.toFixed(2)}% at ${rp(r.price)}`, "label", { size: 7.6, fill: TONE.muted, anchor: "end" });
    ly += 13;
  }
}

// ---------------------------------------------------------------- the question
const QY = Math.max(ly + 26, 352);
mk("line", { x1: M, y1: QY - 20, x2: W - M, y2: QY - 20, class: "lo thin" }, svg);
wrapText(S.question, 14, W - 2 * M).forEach((l, i) => type(svg, M, QY + i * 17, l, "title", { size: 14, weight: 540 }));
type(svg, M, H - 44, S.cta, "label", { fill: "var(--acc)", size: 8.2, weight: 650 });
type(svg, W - M, H - 44, "Not financial advice.", "label", { fill: TONE.faint, size: 6.6, anchor: "end" });
grain(0.05);
