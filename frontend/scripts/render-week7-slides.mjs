import { chromium } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const evidence = resolve(process.argv[2] || '../docs/release/week7-evidence');
const directory = resolve(evidence, 'slide-preview');
await mkdir(directory, { recursive: true });
const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 780 } });
  await page.goto(pathToFileURL(resolve(evidence, 'Week7-Slides.html')).href);
  const count = await page.locator('.slide').count();
  const checks = [];
  for (let i = 0; i < count; i++) {
    const slide = page.locator('.slide.active');
    const bounds = await slide.evaluate(node => ({ width: node.clientWidth, scrollWidth: node.scrollWidth, height: node.clientHeight, scrollHeight: node.scrollHeight }));
    if (bounds.scrollWidth > bounds.width || bounds.scrollHeight > bounds.height) throw new Error('Slide overflow: ' + (i + 1));
    await slide.screenshot({ path: resolve(directory, `slide-${i + 1}.png`) });
    checks.push({ slide: i + 1, ...bounds });
    await page.getByRole('button', { name: 'Next', exact: true }).click();
  }
  await writeFile(resolve(directory, 'layout-checks.json'), JSON.stringify(checks, null, 2));
  console.log('Rendered and checked', count, 'slides');
} finally { await browser.close(); }
