// Story frame 1: the week's busiest brokers, bars true to scale. One accent: the leader's bar.
// DATA: { title, market, top8, rows: [{ code, name, cohort, gross, gross_s, share, wow }] }
setAccent(DATA.direction);
const { top, bottom } = storyFrame(DATA);
dotField(0, 0, W, H, { fx: W * 0.85, fy: H * 0.25, reach: 300, op: 0.22 });
glow(W * 0.3, top + 120, 180, 120, 0.08);

/** A broker's code in a hairline rounded box, fixed width so rows align. */
function codeBadge(g, x, yc, code, { w = 24, h = 15, lit = false } = {}) {
  mk("rect", { x, y: yc - h / 2, width: w, height: h, rx: 3.5, style: `fill:${TONE.ground};stroke:${lit ? "var(--acc)" : TONE.edge};stroke-width:.8px` }, g);
  type(g, x + w / 2, yc + 2.9, code, "label", { fill: lit ? "var(--acc)" : TONE.hi, size: 8, weight: 700, anchor: "middle" });
}

const g = mk("g", {}, svg);
let y = para(g, M, top + 16, DATA.title, "title", { size: 21, maxW: W - 2 * M - 10 });
y += 18;
typeRun(g, M, y, [[`${DATA.market} `, 11, 600, TONE.hi], ["traded on IDX · top 8 brokers took ", 8.4, 450, TONE.muted],
  [`${Math.round(DATA.top8)}%`, 8.4, 650, TONE.hi]]);

const rows = DATA.rows, y0 = y + 22, rh = (bottom - y0) / rows.length;
const bx0 = M + 32, bx1 = W - M - 66, xs = scale(0, rows[0].gross, 0, bx1 - bx0);
rows.forEach((r, i) => {
  const yc = y0 + i * rh + 8, lead = i === 0;
  codeBadge(g, M, yc, r.code, { lit: lead });
  const nm = type(g, bx0, yc + 2.6, r.name, "label", { fill: TONE.hi, size: 8.6, weight: lead ? 650 : 520 });
  if (r.cohort) {
    const nb = nm.getBBox(), cx = nb.x + nb.width + 6;
    const ct = type(g, cx, yc + 2.4, r.cohort, "caps", { fill: TONE.faint, size: 5.6 });
    if (ct.getBBox().x + ct.getBBox().width > bx1) ct.remove(); // no room: drop the tag rather than collide
  }
  // the bar: a hairline track to the leader's length, the broker's value filled
  const by = yc + 9, bw = Math.max(2, xs(r.gross));
  mk("line", { x1: bx0, y1: by, x2: bx1, y2: by, class: "lo thin" }, g);
  mk("rect", { x: bx0, y: by - 2, width: bw, height: 4, rx: 2, style: lead ? "fill:var(--acc);stroke:none" : `fill:${TONE.edge};stroke:none` }, g);
  type(g, W - M, yc + 3, r.gross_s, "label", { fill: TONE.hi, size: 10.5, weight: lead ? 600 : 450, anchor: "end" });
  const wow = r.wow == null ? "new" : `${r.wow >= 0 ? "+" : "−"}${Math.abs(Math.round(r.wow))}% wk`;
  type(g, W - M, by + 3, `${r.share.toFixed(1)}% · ${wow}`, "label", { fill: TONE.faint, size: 6.2, anchor: "end" });
});
grain(0.06);
