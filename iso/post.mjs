#!/usr/bin/env node
/**
 * Renders an isometric feed post: data + shared parts + a story → still PNGs.
 *
 *   node iso/post.mjs <story> <data.json> --out <dir> [--prefix name] [--at 2.9,1.2] [--aspect 4:5] [--size 1080] [--html]
 *
 * <story> is a file name in iso/stories (without .js). Each --at time is one slide.
 * Prints one output path per line. Needs Chrome or Playwright's Chromium (installed once by browser.mjs).
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";
import { assemble } from "./vendor/build.mjs";
import { launch, openFrames } from "./vendor/browser.mjs";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
const { values, positionals } = parseArgs({
  allowPositionals: true,
  options: { out: { type: "string", default: "output" }, prefix: { type: "string" }, at: { type: "string" },
    aspect: { type: "string", default: "4:5" }, size: { type: "string", default: "1080" }, html: { type: "boolean" } },
});
const [storyName, dataFile] = positionals;
if (!storyName || !dataFile) {
  console.error("usage: node iso/post.mjs <story> <data.json> --out dir [--prefix name] [--at 2.9] [--aspect 4:5] [--html]");
  process.exit(2);
}

const data = readFileSync(dataFile, "utf8");
const src = [
  `const DATA = ${data.trim()};`,
  readFileSync(here("./parts.js"), "utf8"),
  readFileSync(here("./scenes.js"), "utf8"),
  readFileSync(here("./carousel.js"), "utf8"),
  readFileSync(here(`./stories/${storyName}.js`), "utf8"),
].join("\n");

const outDir = resolve(values.out);
mkdirSync(outDir, { recursive: true });
const prefix = values.prefix ?? storyName;
const html = join(outDir, `${prefix}.html`);
writeFileSync(html, assemble(src, { logo: here("./sectors-logo.svg") }));

const browser = await launch();
try {
  const { page, stage, info, errors } = await openFrames(browser, html, { aspect: values.aspect, short: Number(values.size) });
  const times = values.at ? values.at.split(",").map(Number) : [info.poster];
  for (const [k, t] of times.entries()) {
    await page.evaluate((s) => __iso.seek(s), t);
    // the flat overlay (charts, tiles, signs): stats stay flat, in the view's own units
    await page.evaluate(() => {
      const stage = document.querySelector(".iso-stage");
      stage.querySelector(".feed-overlay")?.remove();
      if (!globalThis.__OVERLAY__) return;
      const holder = document.createElement("div");
      holder.className = "feed-overlay";
      holder.style.cssText = "position:absolute;inset:0;pointer-events:none";
      holder.innerHTML = __OVERLAY__(__iso.view);
      stage.appendChild(holder);
    });
    await page.evaluate(() => document.fonts?.ready);
    const file = join(outDir, `${prefix}_${k + 1}.png`);
    await stage.screenshot({ path: file });
    console.log(file);
  }
  if (errors.length) {
    console.error("page errors:\n" + errors.join("\n"));
    process.exitCode = 1;
  }
} finally {
  await browser.close();
}
if (values.html) console.log(html);
