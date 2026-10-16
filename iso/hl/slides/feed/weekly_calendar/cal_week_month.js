// Weekly calendar hook, variant D: an actual calendar page. The whole month as a grid (Mon–Sun, weekends narrow
// and dim); the rows of this week open up tall and carry each day's logos; past days fade, today is ringed.
// Same DATA as cal_week (days need `date`).
const D = DATA, S = D.slide;
setAccent(D.direction);
dotField(0, 0, W, H, { fx: W * 0.5, fy: 260, reach: 300, op: 0.3 });
frame(D);

const first = new Date(S.days[0].date + "T00:00:00Z");
const Y0 = first.getUTCFullYear(), MO = first.getUTCMonth();
const monthName = first.toLocaleDateString("en-GB", { month: "long", timeZone: "UTC" });
const byDate = Object.fromEntries(S.days.map((d) => [d.date, d]));
const iso = (t) => new Date(t).toISOString().slice(0, 10);

// the page title: the month huge and light, the year and the count beside it
type(svg, M - 3, 92, monthName, "hero", { size: 58, weight: 440 });
type(svg, W - M, 70, String(Y0), "label", { fill: TONE.muted, size: 9, anchor: "end" });
typeRun(svg, W - M, 90, [[String(S.total), 16, 300, "var(--acc)"], [" events this week", 8, 500, TONE.hi]], { anchor: "end" });

// ---------------------------------------------------------------- the grid
const COLW = [1, 1, 1, 1, 1, 0.5, 0.5], unit = (W - 2 * M) / COLW.reduce((a, b) => a + b, 0);
const colX = COLW.reduce((acc, w, i) => (acc.push(i ? acc[i - 1] + COLW[i - 1] * unit : M), acc), []);
const DOW = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"];
const HEAD = 112;
DOW.forEach((n, i) => type(svg, colX[i] + (COLW[i] * unit) / 2, HEAD, i < 5 ? n : n[0], "caps", { fill: i < 5 ? TONE.muted : TONE.faint, size: 5.4, anchor: "middle" }));
mk("line", { x1: M, y1: HEAD + 6, x2: W - M, y2: HEAD + 6, class: "lo thin" }, svg);

// weeks of the month, Monday first
const start = Date.UTC(Y0, MO, 1), lead = (new Date(start).getUTCDay() + 6) % 7;
const weeks = [];
for (let t = start - lead * 864e5; new Date(t).getUTCMonth() <= MO && new Date(t).getUTCFullYear() === Y0 || weeks.length === 0; t += 7 * 864e5) {
  weeks.push(Array.from({ length: 7 }, (_, k) => t + k * 864e5));
  if (weeks.length > 6) break;
}
const isOpen = (wk) => wk.some((t) => byDate[iso(t)]);
const SHORT = 22, TOP = HEAD + 10, BOT = H - 44;
const nOpen = weeks.filter(isOpen).length;
// open rows share the free height by how many logo rows their busiest day needs
const need = (wk) => Math.max(1, ...wk.map((t) => byDate[iso(t)]).filter(Boolean).map((d) => Math.ceil(Math.min(6, d.groups.reduce((s, g) => s + g.items.length, 0)) / 2)));
const free = BOT - TOP - SHORT * (weeks.length - nOpen), wsum = weeks.filter(isOpen).reduce((s, wk) => s + need(wk) + 1, 0);
const tallOf = (wk) => Math.min(free * (need(wk) + 1) / wsum, 34 + need(wk) * 23);
const today = S.days.find((d) => d.today)?.date;

let y = TOP;
for (const wk of weeks) {
  const open = isOpen(wk), rh = open ? tallOf(wk) : SHORT;
  wk.forEach((t, i) => {
    const ds = iso(t), d = byDate[ds], inMonth = new Date(t).getUTCMonth() === MO, x = colX[i], cw = COLW[i] * unit;
    const past = today && ds < today, weekend = i >= 5, g = mk("g", {}, svg);
    // the cell
    if (open && d && !weekend) {
      mk("rect", { x: x + 1.5, y: y + 1.5, width: cw - 3, height: rh - 3, rx: 5,
        style: d.today ? "fill:var(--acc);fill-opacity:.09;stroke:var(--acc);stroke-width:1px" : `fill:${TONE.hi};fill-opacity:.035;stroke:${TONE.mid};stroke-width:.8px` }, g);
    }
    const numFill = !inMonth ? TONE.lo : d?.today ? "var(--acc)" : open && d ? TONE.hi : past || weekend ? TONE.faint : TONE.muted;
    if (d?.today) mk("circle", { cx: x + 12, cy: y + 11, r: 8.5, style: "fill:none;stroke:var(--acc);stroke-width:1px" }, g);
    type(g, x + 12, y + (open ? 14 : 14), String(new Date(t).getUTCDate()), "label", { fill: numFill, size: open ? 10 : 8, weight: open && d ? 650 : 450, anchor: "middle" });
    // the logos: a 2-wide grid, then "+N"
    if (open && d && !weekend) {
      const items = d.groups.flatMap((gr) => gr.items);
      const r = 8.4, per = 2, fit = Math.max(1, Math.floor((rh - 30) / (2 * r + 4))) * per, show = items.length > fit ? fit - 1 : fit;
      items.slice(0, show).forEach((it, k) => {
        logoChip(g, x + cw / 2 + (k % per ? r + 2 : -r - 2), y + 30 + Math.floor(k / per) * (2 * r + 4) + r - 4, r, it.logo, it.sym);
      });
      if (items.length > show) {
        const k = show, cx = x + cw / 2 + (k % per ? r + 2 : -r - 2), cy = y + 30 + Math.floor(k / per) * (2 * r + 4) + r - 4;
        mk("circle", { cx, cy, r, style: `fill:none;stroke:${TONE.edge};stroke-width:.8px;stroke-dasharray:1.5 2` }, g);
        type(g, cx, cy + 2.6, `+${items.length - show}`, "label", { fill: TONE.hi, size: 7, weight: 650, anchor: "middle" });
      }
      type(g, x + cw - 6, y + 14, String(items.length), "caps", { fill: d.today ? "var(--acc)" : TONE.faint, size: 5.4, anchor: "end" });
    }
  });
  y += rh;
  mk("line", { x1: M, y1: y, x2: W - M, y2: y, class: "lo thin" }, svg);
}
grain();
