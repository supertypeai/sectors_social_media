// Top movers story, frame 2: the week's #1 gainer and #1 loser, day by day. Each panel: who it is, the week's
// move large, its path from last week's close through each session against IHSG (dashed), and how much it traded
// compared with its normal.
// DATA.slide: { title, days: [iso], up: row, down: row, ihsg: {base, path} }   row: {sym, logo, name, sector, rank,
//             ret, base, path: [{date, close}], value_x}
const D = DATA, S = D.slide;
setAccent("buy");
const UP = ACCENTS.buy, DN = ACCENTS.sell;
dotField(0, 0, W, H, { fx: W * 0.25, fy: H * 0.55, reach: 300, op: 0.2 });
const band = storyFrame(D);
const pct = (v, d = 1) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v * 100).toFixed(d)}%`;
const DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

para(svg, M, band.top + 8, S.title, "title");

/** One mover: header, big %, its path (base → each close) as % from base, IHSG dashed on the same scale. */
function panel(r, y0, y1, col, label) {
  const g = mk("g", {}, svg);
  type(g, M, y0, label, "caps", { fill: col });
  const hy = y0 + 22;
  logoChip(g, M + 9, hy - 4, 9, r.logo, r.sym);
  type(g, M + 24, hy, r.sym, "label", { fill: TONE.hi, size: 13, weight: 700 });
  const sub = [r.sector, `#${r.rank} by market cap`].filter(Boolean).join(" · ");
  type(g, M + 24, hy + 12, sub, "label", { fill: TONE.muted, size: 7 });
  type(g, W - M, hy + 10, pct(r.ret), "num", { fill: col, size: 30, weight: 380, anchor: "end" });

  // the chart: x = sessions (prev close, then each day), y = % change from last week's close
  const C = { x0: M + 4, x1: W - M - 4, y0: hy + 34, y1: y1 - 30 };
  const pts = [0, ...r.path.map((p) => p.close / r.base - 1)];
  const ix = S.ihsg ? [0, ...S.ihsg.path.map((p) => p.price ?? p.close).map((v) => v / S.ihsg.base - 1)] : [];
  const all = [...pts, ...ix], lo = Math.min(0, ...all), hi = Math.max(0, ...all), padv = (hi - lo) * 0.1 || 0.01;
  const n = Math.max(pts.length, ix.length) - 1;
  const xs = scale(0, n, C.x0, C.x1), ys = scale(lo - padv, hi + padv, C.y1, C.y0);
  mk("line", { x1: C.x0, y1: ys(0), x2: C.x1, y2: ys(0), class: "lo thin" }, g);
  if (ix.length > 1) {
    mk("path", { d: `M${ix.map((v, i) => `${xs(i).toFixed(1)} ${ys(v).toFixed(1)}`).join("L")}`, class: "nf dash" }, g);
    type(g, C.x1, ys(ix.at(-1)) + (ix.at(-1) > pts.at(-1) ? -5 : 10), `IHSG ${pct(ix.at(-1))}`, "label", { fill: TONE.faint, size: 6.6, anchor: "end" });
  }
  const sp = pts.map((v, i) => [xs(i), ys(v)]);
  areaLine(g, sp, ys(0), { color: col, width: 1.8, fill: 0.16, smooth: false });
  sp.forEach(([x, yy], i) => i && i < sp.length - 1 && mk("circle", { cx: x, cy: yy, r: 1.6, style: `fill:${col};stroke:none` }, g));
  glowDot(g, sp.at(-1)[0], sp.at(-1)[1], col, 3);
  // day names under the sessions
  const labels = ["Prev", ...r.path.map((p) => DOW[new Date(p.date + "T00:00:00Z").getUTCDay()])];
  labels.forEach((l, i) => type(g, xs(i), C.y1 + 12, l, "label", { fill: TONE.faint, size: 6.6, anchor: i === 0 ? "start" : i === labels.length - 1 ? "end" : "middle" }));

  // footer line: price and trading value vs normal
  const fy = y1 - 2;
  const rp0 = (v) => Math.round(v).toLocaleString("en-US");
  typeRun(g, M, fy, [[`Rp ${rp0(r.base)} → `, 8, 500, TONE.muted], [`Rp ${rp0(r.path.at(-1).close)}`, 8, 650, TONE.hi]]);
  if (r.value_x) {
    const vx = r.value_x >= 10 ? r.value_x.toFixed(0) : r.value_x.toFixed(1);
    typeRun(g, W - M, fy, [[`${vx}×`, 8, 700, r.value_x >= 1.5 ? col : TONE.hi], [" usual trading value", 8, 500, TONE.muted]], { anchor: "end" });
  }
}

const top = band.top + 34, mid = (top + band.bottom) / 2;
panel(S.up, top, mid - 10, UP, "Top gainer");
mk("line", { x1: M, y1: mid + 2, x2: W - M, y2: mid + 2, class: "lo thin" }, svg);
panel(S.down, mid + 22, band.bottom, DN, "Top loser");
grain(0.06);
