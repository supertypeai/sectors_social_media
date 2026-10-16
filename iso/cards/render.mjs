#!/usr/bin/env node
/**
 * Renders one list/ranking card to a 1080 × 1350 PNG.
 *
 *   node iso/cards/render.mjs <template> <data.json> --out <file.png>
 *
 * <template> is a key of iso/cards/templates.mjs (dark_bars, glass_bars, glass_table, rank_table, butterfly).
 */
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { parseArgs } from "node:util";
import { launch } from "../vendor/browser.mjs";
import { templates } from "./templates.mjs";

const { values, positionals } = parseArgs({ allowPositionals: true, options: { out: { type: "string" } } });
const [name, dataFile] = positionals;
if (!templates[name] || !dataFile || !values.out) {
  console.error(`usage: node iso/cards/render.mjs <${Object.keys(templates).join("|")}> <data.json> --out file.png`);
  process.exit(2);
}
const body = templates[name](JSON.parse(readFileSync(dataFile, "utf8")));
const page = `<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter+Tight:ital,wght@0,400..800;1,600..800&display=swap">
</head><body>${body}</body></html>`;

const out = resolve(values.out);
mkdirSync(dirname(out), { recursive: true });
const htmlFile = out.replace(/\.png$/, ".html");
writeFileSync(htmlFile, page);
const browser = await launch();
try {
  const tab = await browser.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 1 });
  await tab.goto(`file://${htmlFile}`, { waitUntil: "networkidle" });
  await tab.evaluate(() => document.fonts.ready);
  await tab.screenshot({ path: out, clip: { x: 0, y: 0, width: 1080, height: 1350 } });
  console.log(out);
} finally {
  await browser.close();
}
