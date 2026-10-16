// Story frame 2: the broker with the biggest net position. Hero net, its net day by day, the stocks behind it.
// DATA: { broker: {code, name, foreign, cohort}, net, net_s, gross_s, rank, daily: [{dow, v, s}], stocks: [{sym, logo, v, s, pct}] }
setAccent(DATA.direction);
const { top, bottom } = storyFrame(DATA);
dotField(0, 0, W, H, { fx: W * 0.2, fy: H * 0.3, reach: 300, op: 0.2 });
glow(W * 0.5, top + 70, 200, 90, 0.1);

const g = mk("g", {}, svg), B = DATA.broker, buy = DATA.net > 0;

// who: the code in a box, the name, what kind of house it is
const bw = 34, bh = 22;
mk("rect", { x: M, y: top, width: bw, height: bh, rx: 5, style: "fill:none;stroke:var(--acc);stroke-width:1px" }, g);
type(g, M + bw / 2, top + 15.2, B.code, "label", { fill: "var(--acc)", size: 11.5, weight: 700, anchor: "middle" });
type(g, M + bw + 10, top + 10, B.name, "label", { fill: TONE.hi, size: 11, weight: 600 });
type(g, M + bw + 10, top + 20.5, [B.foreign ? "Foreign" : "Local", B.cohort].filter(Boolean).join(" · "), "caps", { fill: TONE.muted, size: 5.8 });

// the number
let y = top + 76;
type(g, M - 2, y, DATA.net_s, "num", { size: 50, weight: 380, fill: "var(--acc)" });
y += 22;
type(g, M, y, `net ${buy ? "bought" : "sold"} last week · #${DATA.rank} by value traded (${DATA.gross_s})`, "label", { fill: TONE.muted, size: 7.6 });

// day by day: diverging bars around zero
y += 26;
type(g, M, y, "Net, day by day", "caps", { fill: TONE.hi });
const cy0 = y + 14, cy1 = y + 104, vals = DATA.daily.map((d) => d.v);
// one scale for both sides, the zero line placed so each side gets room in proportion to its biggest day;
// 11 units kept above and below for the value labels
const P = Math.max(0, ...vals), N = Math.max(0, ...vals.map((v) => -v)), span = cy1 - cy0 - 22;
const zero = cy0 + 11 + span * (P / (P + N || 1)), ys = scale(0, Math.max(P + N, 1), 0, span);
mk("line", { x1: M, y1: zero, x2: W - M, y2: zero, class: "nf thin", style: `stroke:${TONE.mid}` }, g);
const cw = (W - 2 * M) / DATA.daily.length;
DATA.daily.forEach((d, i) => {
  const x = M + cw * i + cw / 2, h = Math.max(1.2, ys(Math.abs(d.v))), up = d.v >= 0, same = (d.v > 0) === buy;
  const yTop = up ? zero - h : zero;
  mk("rect", { x: x - 11, y: yTop, width: 22, height: h, rx: 2,
    style: same ? "fill:var(--acc);stroke:none" : `fill:none;stroke:${TONE.edge};stroke-width:.8px` }, g);
  type(g, x, up ? yTop - 4 : yTop + h + 9, d.s.replace("Rp ", ""), "label", { fill: same ? TONE.hi : TONE.muted, size: 7, weight: 550, anchor: "middle" });
  type(g, x, cy1 + 9, d.dow.toUpperCase(), "caps", { fill: TONE.faint, size: 5.6, anchor: "middle" });
});

// where it went
y = cy1 + 32;
type(g, M, y, buy ? "What it bought" : "What it sold", "caps", { fill: TONE.hi });
const S = DATA.stocks, rh = Math.min(30, (bottom - y - 8) / Math.max(1, S.length));
const smax = Math.max(...S.map((s) => Math.abs(s.v))) || 1, bx0 = M + 66, bx1 = W - M - 58;
S.forEach((s, i) => {
  const yc = y + 18 + i * rh;
  tickerChip(g, M, yc + 3, s.sym, s.logo, { size: 9.5 });
  mk("line", { x1: bx0, y1: yc, x2: bx1, y2: yc, class: "lo thin" }, g);
  mk("rect", { x: bx0, y: yc - 2.5, width: Math.max(2, (bx1 - bx0) * Math.abs(s.v) / smax), height: 5, rx: 2.5, style: "fill:var(--acc);stroke:none" }, g);
  type(g, W - M, yc + 1, s.s, "label", { fill: TONE.hi, size: 9.5, weight: 550, anchor: "end" });
  type(g, W - M, yc + 10, `${Math.round(s.pct)}% of its net`, "label", { fill: TONE.faint, size: 6, anchor: "end" });
});
grain(0.06);
