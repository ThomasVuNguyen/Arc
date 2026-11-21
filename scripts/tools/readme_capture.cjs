#!/usr/bin/env node
// readme_capture.cjs: export README images from the local brand book.
//
// Opens vault/brand-book.html#/capture/<name> for each job below and saves a
// PNG (still) or a looping animated WebP (motion) into docs/readme/.
// JS time is driven by Playwright's fake clock and CSS time by __advanceCss,
// so every frame is deterministic.
//
// usage:
//   npm i playwright-core            (anywhere; then run with NODE_PATH pointing at it)
//   NODE_PATH=<dir>/node_modules CHROME=<chromium or headless-shell binary> node scripts/tools/readme_capture.cjs [only-name ...]
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
const BOOK = 'file://' + path.join(ROOT, 'vault', 'brand-book.html');
const OUT = path.join(ROOT, 'docs', 'readme');
const SCALE = 2, ANIM_SCALE = 1.5, QUALITY = '60';

// name, width, height, seconds of animation (0 = still), fps
const JOBS = [
  ['hero', 1200, 360, 0],
  ['header-motion', 1200, 220, 0], ['header-icons', 1200, 220, 0], ['header-color', 1200, 220, 0],
  ['header-spaces', 1200, 220, 0], ['header-type', 1200, 220, 0], ['header-glyphs', 1200, 220, 0],
  ['rings', 400, 400, 8, 12], ['halftone', 400, 400, 5.71, 12], ['particles', 400, 400, 6, 12],
  ['lottiegrid', 400, 400, 6, 12], ['tidytabs', 400, 400, 7.2, 12], ['cmdbar', 400, 400, 6, 12],
  ['logo', 400, 400, 3, 15], ['heart', 400, 400, 2, 15], ['spacearc', 400, 400, 6, 12],
  ['iconwall', 1200, 500, 0],
  ['gradient', 400, 400, 0], ['arcblue', 400, 400, 0], ['ink', 400, 400, 0],
  ['brand', 400, 400, 0], ['extended', 400, 400, 0], ['scales', 400, 400, 0],
  ['picker', 400, 400, 0], ['space-moss', 400, 400, 6, 12], ['space-night', 400, 400, 6, 12],
  ['type-eb-garamond', 400, 400, 0], ['type-inter', 400, 400, 0], ['type-space-mono', 400, 400, 0],
  ['glyphs1', 400, 400, 4.4, 10], ['glyphs2', 400, 400, 4.4, 10], ['vibrant', 400, 400, 6, 12],
];

(async () => {
  const only = process.argv.slice(2);
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ executablePath: process.env.CHROME, args: ['--allow-file-access-from-files'] });
  for (const [name, w, h, secs, fps = 15] of JOBS) {
    if (only.length && !only.includes(name)) continue;
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: secs ? ANIM_SCALE : SCALE, reducedMotion: 'no-preference' });
    const page = await ctx.newPage();
    await page.clock.install({ time: 0 });
    await page.goto(`${BOOK}#/capture/${name}`);
    await page.evaluate(() => document.fonts.ready);
    await page.clock.runFor(1500);                       // lottie load, first frames, fonts settle
    await page.evaluate(() => window.__advanceCss(1500));
    await page.waitForTimeout(300);                      // real time for font/image decode
    if (!secs) {
      await page.screenshot({ path: path.join(OUT, `${name}.png`), omitBackground: true });
      console.log(`${name}.png`);
    } else {
      const dt = 1000 / fps, total = Math.round(secs * fps), overlap = Math.round(total * 0.18);
      const dir = fs.mkdtempSync(path.join(require('os').tmpdir(), `cap-${name}-`));
      for (let i = 0; i < total + overlap; i++) {
        await page.screenshot({ path: path.join(dir, `${String(i).padStart(4, '0')}.png`), omitBackground: true });
        await page.clock.runFor(dt);
        await page.evaluate(d => window.__advanceCss(d), dt);
      }
      execFileSync('python3', ['-I', path.join(__dirname, 'frames_to_webp.py'), dir, path.join(OUT, `${name}.webp`), String(fps), String(overlap), QUALITY], { stdio: 'inherit' });
      fs.rmSync(dir, { recursive: true, force: true });
    }
    await ctx.close();
  }
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
