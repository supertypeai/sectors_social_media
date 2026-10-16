// Insider "people", slide 3: everyone who filed on this stock in six months, on one timeline ribbon.
// Buys rise above the line, sells hang below; the length is the stake moved. Answers "one person, or a pattern?"
// DATA.slide: { sym, events[{date, name, type, pp, value, mover}], moveDate, today, holder }
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

const ev = S.events;
const people = new Map();
for (const e of ev) {
  const k = e.name.toLowerCase();
  const p = people.get(k) ?? { name: e.name, buys: 0, sells: 0, pp: 0, mover: e.mover };
  p[e.type === "buy" ? "buys" : "sells"]++;
  p.pp += e.type === "buy" ? e.pp : -e.pp;
  p.mover = p.mover || e.mover;
  people.set(k, p);
}
const nP = people.size;
para(svg, M, 74, `${nP} insiders, ${ev.length} filings`, "title", { accent: [String(nP)] });
type(svg, M, 90, `Every insider buy and sell on ${S.sym} in six months. Longer line = bigger stake.`, "body", { fill: TONE.muted });

// ---------------------------------------------------------------- the ribbon
const t1 = dayOf(S.today), t0 = t1 - 182 * 864e5;
const xs = scale(t0, t1, M + 4, W - M - 4), base = 205;
const maxPP = Math.max(...ev.map((e) => e.pp), 1);
const len = (pp) => 8 + 62 * Math.sqrt(pp / maxPP);
const g = mk("g", {}, svg);
mk("line", { x1: M, y1: base, x2: W - M, y2: base, style: `stroke:${TONE.edge};stroke-width:1px` }, g);
type(g, M, base - 74, "BUYS ↑", "caps", { size: 5.6, fill: TONE.faint });
type(g, M, base + 82, "SELLS ↓", "caps", { size: 5.6, fill: TONE.faint });
// month ticks
{
  const d = new Date(t0); d.setUTCDate(1); d.setUTCMonth(d.getUTCMonth() + 1);
  for (; d.getTime() <= t1; d.setUTCMonth(d.getUTCMonth() + 1)) {
    const x = xs(d.getTime());
    mk("line", { x1: x, y1: base - 2, x2: x, y2: base + 2, style: `stroke:${TONE.edge};stroke-width:.8px` }, g);
    type(g, x + 2, base + 9, fmtMonth(d.getTime()), "label", { size: 5.8, fill: TONE.faint });
  }
}
// draw the others first, the mover last (on top)
const sorted = [...ev].sort((a, b) => a.mover - b.mover);
for (const e of sorted) {
  const x = xs(Math.max(dayOf(e.date), t0)), up = e.type === "buy", l = len(e.pp), y2 = up ? base - l : base + l;
  const c = e.mover ? "var(--acc)" : TONE.muted;
  mk("line", { x1: x, y1: base, x2: x, y2, style: `stroke:${c};stroke-width:${e.mover ? 1.8 : 1}px;opacity:${e.mover ? 1 : 0.75}` }, g);
  mk("circle", { cx: x, cy: y2, r: e.mover ? 3.4 : 2.2, style: e.mover ? "fill:var(--acc);stroke:none" : `fill:${TONE.ground};stroke:${TONE.muted};stroke-width:1px` }, g);
}
// the mover's label at their line's end
{
  const m = ev.filter((e) => e.mover).sort((a, b) => b.pp - a.pp)[0];
  if (m) {
    const x = xs(dayOf(m.date)), up = m.type === "buy", y2 = up ? base - len(m.pp) : base + len(m.pp);
    const right = x < W / 2, tx = right ? x + 7 : x - 7, anchor = right ? "start" : "end";
    type(svg, tx, y2 + (up ? 3 : 3), `${m.name.length > 24 ? m.name.slice(0, 23) + "…" : m.name}`, "label", { size: 7.6, weight: 650, anchor, fill: "var(--acc)" });
    type(svg, tx, y2 + 12, `${m.type === "buy" ? "+" : "−"}${m.pp.toFixed(m.pp >= 10 ? 1 : 2)}% · ${fmtDay(dayOf(m.date))}`, "label", { size: 6.6, anchor, fill: TONE.muted });
  }
}

// ---------------------------------------------------------------- who, in short
let y = 316;
mk("line", { x1: M, y1: y - 12, x2: W - M, y2: y - 12, class: "lo thin" }, svg);
const list = [...people.values()].sort((a, b) => b.mover - a.mover || Math.abs(b.pp) - Math.abs(a.pp)).slice(0, 5);
for (const p of list) {
  const what = [p.buys ? `${p.buys} buy${p.buys > 1 ? "s" : ""}` : "", p.sells ? `${p.sells} sell${p.sells > 1 ? "s" : ""}` : ""].filter(Boolean).join(" · ");
  type(svg, M, y, p.name.length > 30 ? p.name.slice(0, 29) + "…" : p.name, "label", { size: 8, weight: p.mover ? 650 : 500, fill: p.mover ? TONE.hi : TONE.muted });
  type(svg, W - M - 62, y, what, "label", { size: 7, fill: TONE.faint, anchor: "end" });
  const net = p.pp;
  type(svg, W - M, y, `${net >= 0 ? "+" : "−"}${Math.abs(net).toFixed(Math.abs(net) >= 10 ? 1 : 2)}%`, "label", { size: 8, weight: 650, anchor: "end", fill: p.mover ? "var(--acc)" : TONE.hi });
  y += 15;
}
if (people.size > list.length) type(svg, M, y, `+ ${people.size - list.length} more`, "label", { size: 7, fill: TONE.faint });
