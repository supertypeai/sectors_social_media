// Insider cover, approach 2 — the filing as an artefact: a paper deed on the dark desk, typed fields, a rubber
// stamp with the size of the move, and the holder's name on the signature line. Every field is real data.
// DATA.slide: the vp_cover payload from image_generator/insider_v_people.build().
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

const pc = (v) => (v < 0.005 ? "0%" : (v >= 10 ? v.toFixed(1) : v.toFixed(2)).replace(/\.?0+$/, "") + "%");
const moved = Math.abs(S.after - S.before);
const INK = "#2a2420", PAPER = "#efe9df", RULE = "#cfc6b8", SOFT = "#7d7268";
const ACC = S.sell ? "#a95a43" : "#4f7d5a"; // the accents, deepened to read as ink on paper

// ---------------------------------------------------------------- the sheet
const px = M + 6, py = 52, pw = W - 2 * M - 12, ph = 344;
const sheet = mk("g", { transform: `rotate(-1.4 ${W / 2} ${py + ph / 2})` }, svg);
mk("rect", { x: px + 3, y: py + 5, width: pw, height: ph, rx: 2, style: "fill:#000;opacity:.35;filter:blur(6px);stroke:none" }, sheet);
mk("rect", { x: px, y: py, width: pw, height: ph, rx: 2, style: `fill:${PAPER};stroke:none` }, sheet);
// the perforated tear strip at the top
for (let x = px + 6; x < px + pw - 4; x += 7) mk("circle", { cx: x, cy: py + 10, r: 1.1, style: `fill:${TONE.ground};stroke:none;opacity:.55` }, sheet);
const t = (x, y, s, o = {}) => { const e = type(sheet, x, y, s, o.role || "label", { fill: o.fill || INK, size: o.size, weight: o.weight, anchor: o.anchor }); return e; };
const ix = px + 18, iw = pw - 36;

t(ix, py + 32, "Notice of share transaction", { role: "caps", fill: SOFT, size: 6.2, weight: 700 });
t(ix + iw, py + 32, `No. ${S.sym}-${S.year}`, { role: "caps", fill: SOFT, size: 6.2, anchor: "end" });
t(ix, py + 58, S.name, { role: "title", size: 19, weight: 600 });
mk("line", { x1: ix, y1: py + 68, x2: ix + iw, y2: py + 68, style: `stroke:${INK};stroke-width:.9px` }, sheet);

// typed fields: label left in small caps, value right
const rows = [
  ["Holder", S.holder.name + (S.holder.sym ? ` (${S.holder.sym})` : "")],
  ["Action", S.other ? `bought from ${S.other.name}` : S.sell ? (S.after < 0.005 ? "sold the whole stake" : "sold") : "bought"],
  ["Stake", `${pc(S.before)}  →  ${pc(S.after)}`],
  ...(S.other ? [["Seller's stake", `${pc(S.otherBefore)}  →  ${pc(S.otherAfter)}`]] : []),
  ["Value", S.value],
  ["Trade date", `${S.span} ${S.year}`],
];
let y = py + 92;
const fs = rows.length > 5 ? 10 : 11.5, lh = fs * 1.2;
for (const [k, v] of rows) {
  t(ix, y, k, { role: "caps", fill: SOFT, size: 5.8 });
  const lines = wrapText(v, fs, iw - 70, 0.5);
  lines.slice(0, 2).forEach((l, i) => t(ix + 70, y + i * lh, l, { size: fs, weight: k === "Holder" ? 650 : 500 }));
  y += lh * Math.min(2, lines.length) + 9;
  mk("line", { x1: ix, y1: y - lh, x2: ix + iw, y2: y - lh, style: `stroke:${RULE};stroke-width:.5px;stroke-dasharray:1 2` }, sheet);
}

// ---------------------------------------------------------------- the stamp: the size of the move
const sx = ix + iw - 66, sy = py + ph - 82, sr = 56;
const st = mk("g", { transform: `rotate(-14 ${sx} ${sy})`, style: "opacity:.88" }, sheet);
mk("circle", { cx: sx, cy: sy, r: sr, style: `fill:none;stroke:${ACC};stroke-width:2.4px` }, st);
mk("circle", { cx: sx, cy: sy, r: sr - 5, style: `fill:none;stroke:${ACC};stroke-width:.8px` }, st);
const sv = S.other ? "Bought" : S.sell ? (S.after < 0.005 ? "Fully sold" : "Sold") : "Bought";
type(st, sx, sy - 18, sv, "caps", { fill: ACC, size: 7.4, weight: 800, anchor: "middle" });
typeRun(st, sx, sy + 12, [[pc(moved).slice(0, -1), 30, 650, ACC], ["%", 14, 650, ACC]], { anchor: "middle" });
type(st, sx, sy + 26, `of ${S.sym}`, "caps", { fill: ACC, size: 6.4, weight: 750, anchor: "middle" });
// a little ink wear: paper-coloured specks over the stamp
for (let i = 0; i < 40; i++) {
  const a = (i * 137.5 * Math.PI) / 180, rr = sr * Math.sqrt(((i * 0.618) % 1));
  mk("circle", { cx: sx + Math.cos(a) * rr, cy: sy + Math.sin(a) * rr, r: 0.5 + (i % 3) * 0.35, style: `fill:${PAPER};stroke:none;opacity:.7` }, st);
}

// ---------------------------------------------------------------- the signature line
const gy = py + ph - 34;
mk("line", { x1: ix, y1: gy, x2: ix + 140, y2: gy, style: `stroke:${INK};stroke-width:.7px` }, sheet);
const sig = type(sheet, ix + 2, gy - 5, S.holder.name, "title", { fill: INK, size: S.holder.name.length > 18 ? 12.5 : 15, weight: 300 });
sig.setAttribute("font-style", "italic");
t(ix, gy + 10, S.other ? "the buyer" : S.sell ? "the seller" : "the buyer", { role: "caps", fill: SOFT, size: 5.6 });

grain(0.06);
