// Card styles for list/ranking posts, inspired by the top-engaging Indonesian finance accounts
// (Algo Research, Henan Sekuritas, MNC Sekuritas): one bold title, the chart is the whole slide,
// every row starts with the company logo, values printed at the bar ends, no axes.
// Each template takes DATA and returns the HTML body of a 1080 × 1350 card.

const LOGO_CDN = "https://storage.googleapis.com/sectorsapp-sea/logo/";
const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;");
const logo = (r) => `<img class="logo" src="${r.logo ?? LOGO_CDN + r.sym + ".webp"}" onerror="this.style.visibility='hidden'">`;
const rp = (v) => {
  const a = Math.abs(v);
  const [d, u] = a >= 1e12 ? [1e12, "T"] : a >= 1e9 ? [1e9, "B"] : [1e6, "M"];
  const n = a / d;
  return `Rp ${n >= 100 ? n.toFixed(0) : n.toFixed(1)} ${u}`;
};
const pct = (v, d = 1) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(d)}%`;
const day = (s) => new Date(s + "T00:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
const title = (text, accent) => esc(text).replace(esc(accent), `<em>${esc(accent)}</em>`);

const BASE = `
*{box-sizing:border-box;margin:0;padding:0}
body{width:1080px;height:1350px;font-family:"Inter Tight",Inter,sans-serif;font-feature-settings:"tnum" 1;overflow:hidden}
.card{position:relative;width:1080px;height:1350px;padding:84px 72px 0;display:flex;flex-direction:column}
.logo{width:100%;height:100%;object-fit:contain;border-radius:50%;background:#fff}
.lg{width:64px;height:64px;border-radius:50%;padding:7px;background:#fff;flex:none;box-shadow:0 2px 10px rgba(0,0,0,.18)}
h1{font-weight:800;letter-spacing:-.025em;line-height:1.04}
h1 em{font-style:normal}
.foot{position:absolute;left:72px;right:72px;bottom:44px;display:flex;justify-content:space-between;align-items:flex-end;font-size:21px}
.brand{font-weight:800;font-size:34px;letter-spacing:-.02em}
`;

export const templates = {
  // 1 · Algo "Biggest Budget": dark, gradient bars with a slanted end, logo + names on the left
  dark_bars: (D) => {
    const max = Math.max(...D.rows.map((r) => r.value));
    return `<style>${BASE}
body{background:#0b0b16}
.card{background:radial-gradient(120% 70% at 85% 95%,#2a1f4d 0%,transparent 60%),linear-gradient(180deg,#0f0f1f,#090912);color:#f4f2ff}
h1{font-size:76px}h1 em{color:#b89bff}
.rule{display:flex;align-items:center;gap:18px;margin:30px 0 34px;color:#a8a3c7;font-size:22px}
.rule:before{content:"";flex:1;height:2px;background:linear-gradient(90deg,transparent,#5b5390)}
.rule span{border:2px solid #5b5390;border-radius:99px;padding:6px 18px;font-weight:600}
.row{display:grid;grid-template-columns:64px 300px 1fr;align-items:center;gap:20px;height:86px}
.who{border-left:2px solid #3a3560;padding-left:18px;line-height:1.15}
.who b{display:block;font-size:30px}.who small{color:#a8a3c7;font-size:19px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block;max-width:280px}
.bar{display:flex;align-items:center;gap:16px}
.fill{height:54px;clip-path:polygon(0 0,100% 0,calc(100% - 22px) 100%,0 100%);background:linear-gradient(90deg,#2f6bff,#4f8cff)}
.row:nth-child(even) .fill{background:linear-gradient(90deg,#7b4dff,#a77bff)}
.val{font-size:32px;font-weight:800;white-space:nowrap}
.foot{color:#8c86b3}
</style><div class="card"><h1>${title(D.title, D.accent)}</h1>
<div class="rule">${esc(D.sub)}<span>${esc(D.unit)}</span></div>
<div>${D.rows.map((r) => `<div class="row"><div class="lg">${logo(r)}</div><div class="who"><b>${esc(r.sym)}</b><small>${esc(r.label)}</small></div>
<div class="bar"><div class="fill" style="width:${Math.max(4, (r.value / max) * 92)}%"></div><span class="val">${esc(r.display)}</span></div></div>`).join("")}</div>
<div class="foot"><span>${esc(D.source)}</span><span class="brand">sectors</span></div></div>`;
  },

  // 2 · Henan "Emiten Sektor": light, glossy glass bars around a zero line, logo at the bar's root
  glass_bars: (D) => {
    const max = Math.max(...D.rows.map((r) => Math.abs(r.value)));
    // with negatives the zero line sits right of centre and bars are capped, so a value label always fits
    const neg = D.rows.some((r) => r.value < 0), zero = neg ? 54 : 0, span = neg ? 34 : 80;
    return `<style>${BASE}
body{background:#eef3ff}
.card{background:radial-gradient(90% 60% at 80% 70%,#dbe6ff 0%,transparent 70%),linear-gradient(180deg,#f6f8ff,#e9efff);color:#13265c;text-align:center}
h1{font-size:74px;background:linear-gradient(180deg,#2c6bf0,#163a96);-webkit-background-clip:text;color:transparent}
.sub{font-size:28px;margin:14px 0 40px;color:#1d2b55}
.rows{position:relative;text-align:left}
.rows:before{content:"";position:absolute;left:calc(120px + (100% - 120px) * ${zero / 100});top:0;bottom:0;width:2px;background:#9fb3e8;display:${neg ? "block" : "none"}}
.row{display:grid;grid-template-columns:120px 1fr;align-items:center;height:72px}
.t{font-size:28px;font-weight:700;color:#2a4fb8}
.track{position:relative;height:56px}
.g{position:absolute;top:0;height:56px;border-radius:14px;background:linear-gradient(180deg,rgba(150,180,255,.75),rgba(90,130,240,.55));border:2px solid rgba(255,255,255,.9);box-shadow:inset 0 2px 6px rgba(255,255,255,.9),0 6px 16px rgba(60,90,200,.18)}
.g.n{background:linear-gradient(180deg,rgba(255,160,175,.7),rgba(230,90,110,.5))}
.lgw{position:absolute;top:-4px;width:64px;height:64px}
.v{position:absolute;top:13px;font-size:26px;font-weight:800;white-space:nowrap}
.v.p{color:#1c9a5b}.v.n{color:#d23b52}
.foot{color:#334a86}.brand{color:#163a96}
</style><div class="card"><h1>${title(D.title, D.accent)}</h1><div class="sub">${esc(D.sub)}</div><div class="rows">
${D.rows.map((r) => {
  const w = (Math.abs(r.value) / max) * span;
  const left = r.value >= 0 ? zero : zero - w;
  const lgLeft = `calc(${zero}% - 32px)`; // the logo always sits on the zero line
  const vPos = r.value >= 0 ? `left:calc(${left + w}% + 14px)` : `right:calc(${100 - left}% + 14px)`;
  return `<div class="row"><span class="t">${esc(r.sym)}</span><div class="track">
<div class="g ${r.value < 0 ? "n" : ""}" style="left:${left}%;width:${Math.max(w, 6)}%"></div>
<div class="lgw" style="left:${lgLeft}"><div class="lg" style="width:64px;height:64px">${logo(r)}</div></div>
<span class="v ${r.value < 0 ? "n" : "p"}" style="${vPos}">${pct(r.value, 2)}</span></div></div>`;
}).join("")}</div>
<div class="foot"><span>${esc(D.source)}</span><span class="brand">sectors</span></div></div>`;
  },

  // 3 · Henan "Right Issue Radar" / MNC "Dividend Hunter": deep blue, glass row pills, a few columns
  glass_table: (D) => `<style>${BASE}
body{background:#0a2a7a}
.card{background:radial-gradient(80% 50% at 50% 10%,#2f6be0 0%,transparent 70%),linear-gradient(180deg,#0d3a9e,#081f5c);color:#fff;text-align:center}
h1{font-size:82px;background:linear-gradient(180deg,#d8ecff,#7fb8ff);-webkit-background-clip:text;color:transparent}
.sub{font-size:34px;font-weight:600;margin:10px 0 42px;color:#e4efff}
.head,.row{display:grid;grid-template-columns:130px 70px 1.5fr 1.15fr .8fr;align-items:center;gap:0 12px}
.head{font-size:22px;font-weight:700;color:#cfe2ff;margin-bottom:12px;line-height:1.2}
.row{height:84px;margin-bottom:12px}
.t{font-size:34px;font-weight:800;text-align:left}
.pill{grid-column:2 / span 4;display:grid;grid-template-columns:70px 1.5fr 1.15fr .8fr;gap:0 12px;align-items:center;height:76px;border-radius:40px;background:linear-gradient(180deg,rgba(255,255,255,.28),rgba(255,255,255,.1));border:2px solid rgba(255,255,255,.35);box-shadow:inset 0 2px 0 rgba(255,255,255,.35)}
.pill .lg{margin-left:4px}
.c{font-size:24px;line-height:1.15}.c b{font-weight:800}
.c.h{text-align:left;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.up{color:#7dffb8}.dn{color:#ff9aa8}
.foot{color:#b8cdf5}
</style><div class="card"><h1>${title(D.title, D.accent)}</h1><div class="sub">${esc(D.sub)}</div>
<div class="head"><span></span><span></span><span style="text-align:left">${esc(D.cols[0])}</span><span>${esc(D.cols[1])}</span><span>${esc(D.cols[2])}</span></div>
${D.rows.map((r) => `<div class="row"><span class="t">${esc(r.sym)}</span><div class="pill"><div class="lg">${logo(r)}</div>
<span class="c h">${esc(r.holder)}</span><span class="c"><b class="${r.after > r.before ? "up" : "dn"}">${r.before.toFixed(1)}% → ${r.after.toFixed(1)}%</b></span><span class="c">${rp(r.value)}</span></div></div>`).join("")}
<div class="foot"><span>${esc(D.source)}</span><span class="brand">sectors</span></div></div>`,

  // 4 · Algo "Trust Most": dark navy ranked table, numbered, two value columns with mini bars
  rank_table: (D) => {
    const max = Math.max(...D.rows.flatMap((r) => [Math.abs(r.a), Math.abs(r.b)]));
    const cell = (v) => `<span class="n ${v < 0 ? "neg" : ""}">${pct(v)}</span><span class="mb"><i class="${v < 0 ? "neg" : ""}" style="width:${(Math.abs(v) / max) * 100}%"></i></span>`;
    return `<style>${BASE}
body{background:#0e1424}
.card{background:linear-gradient(180deg,#141b30,#0b1020);color:#eef2ff}
.kick{font-size:24px;color:#9fb0d8;font-style:italic;border-bottom:2px solid #3a4670;align-self:flex-start;padding-bottom:6px;margin-bottom:18px}
h1{font-size:70px}h1 em{color:#86a6ff;font-style:italic}
.tbl{margin-top:36px;border-radius:14px;overflow:hidden}
.head,.row{display:grid;grid-template-columns:60px 64px 1fr 110px 150px 110px 150px;align-items:center;gap:0 16px}
.head{background:#24305a;font-size:22px;font-weight:700;padding:14px 18px;color:#c9d5ff}
.head span:nth-child(4){grid-column:4 / span 2}.head span:nth-child(5){grid-column:6 / span 2}
.row{padding:0 18px;height:70px;border-bottom:2px dotted #2b3558;font-size:26px}
.num{width:42px;height:42px;border-radius:50%;background:#3d55b8;display:grid;place-items:center;font-size:20px;font-weight:700}
.row .lg{width:52px;height:52px;padding:5px}
.n{font-weight:800;font-style:italic;text-align:right;color:#86a6ff}.n.neg{color:#ff8f9c}
.mb{height:10px;background:#26304f;border-radius:6px;overflow:hidden}.mb i{display:block;height:100%;background:#6f8dff}.mb i.neg{background:#ff7d8c}
.foot{color:#8a97c2}
</style><div class="card"><div class="kick">${esc(D.kicker)}</div><h1>${title(D.title, D.accent)}</h1>
<div class="tbl"><div class="head"><span></span><span></span><span>${esc(D.cols[0])}</span><span style="text-align:center">${esc(D.cols[1])}</span><span style="text-align:center">${esc(D.cols[2])}</span></div>
${D.rows.map((r, i) => `<div class="row"><span class="num">${i + 1}</span><div class="lg">${logo(r)}</div><span><b>${esc(r.sym)}</b></span>${cell(r.a)}${cell(r.b)}</div>`).join("")}</div>
<div class="foot"><span>${esc(D.source)}</span><span class="brand">sectors</span></div></div>`;
  },

  // 5 · Algo "Miracle Crop": light, two-sided bars around a centre column of logos + tickers
  butterfly: (D) => {
    const max = Math.max(...D.rows.flatMap((r) => [r.left, r.right]));
    const w = (v) => (v / max) * 100;
    return `<style>${BASE}
body{background:#f1f4fb}
.card{background:linear-gradient(180deg,#fbfcff,#eef2fb);color:#1a2340}
h1{font-size:74px}h1 em{color:#5a3fd6}
.sub{font-size:26px;margin:16px 0 30px;color:#3b4566;border-bottom:2px solid #d5dbec;padding-bottom:18px}
.box{background:#fff;border-radius:28px;padding:22px;box-shadow:0 10px 30px rgba(30,50,120,.08)}
.hd{display:grid;grid-template-columns:1fr 210px 1fr;gap:14px;margin-bottom:12px}
.hd span{border-radius:20px;padding:14px 20px;font-size:24px;font-weight:700;text-align:center}
.hd .l{background:#ffe9ec;color:#c2344c}.hd .r{background:#e6fbf3;color:#14845a}
.row{display:grid;grid-template-columns:1fr 210px 1fr;gap:14px;align-items:center;height:76px}
.side{height:52px;background:#f2f4fa;border-radius:12px;position:relative}
.side i{position:absolute;top:0;height:100%;border-radius:10px}
.side.l i{right:0;background:linear-gradient(90deg,#ff9aaa,#e2425c)}.side.r i{left:0;background:linear-gradient(90deg,#3ccf93,#8ee6c2)}
.side b{position:absolute;top:12px;font-size:24px;white-space:nowrap}
.mid{display:flex;align-items:center;gap:14px;background:#f6f7fb;border-radius:16px;height:66px;padding:0 14px;font-size:28px;font-weight:700}
.mid .lg{width:46px;height:46px;padding:4px}
.note{margin-top:22px;font-size:23px;color:#3b4566;background:#fff4f6;border-left:6px solid #e2425c;padding:16px 20px;border-radius:10px}
.foot{color:#55607f}.brand{color:#5a3fd6}
</style><div class="card"><h1>${title(D.title, D.accent)}</h1><div class="sub">${esc(D.sub)}</div>
<div class="box"><div class="hd"><span class="l">${esc(D.leftLabel)}</span><span></span><span class="r">${esc(D.rightLabel)}</span></div>
${D.rows.map((r) => `<div class="row"><div class="side l">${r.left ? `<i style="width:${w(r.left)}%"></i>` : ""}<b style="${w(r.left) > 55 ? "left:14px;color:#fff" : `right:calc(${w(r.left)}% + 12px)`}">${r.left ? rp(r.left) : "–"}</b></div>
<div class="mid"><div class="lg">${logo(r)}</div>${esc(r.sym)}</div>
<div class="side r">${r.right ? `<i style="width:${w(r.right)}%"></i>` : ""}<b style="${w(r.right) > 55 ? "right:14px;color:#fff" : `left:calc(${w(r.right)}% + 12px)`}">${r.right ? rp(r.right) : "–"}</b></div></div>`).join("")}</div>
${D.note ? `<div class="note">${esc(D.note)}</div>` : ""}
<div class="foot"><span>${esc(D.source)}</span><span class="brand">sectors</span></div></div>`;
  },
};
