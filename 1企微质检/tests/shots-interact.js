const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');

(async () => {
  const target = process.argv[2];
  const outDir = process.argv[3];
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({
    executablePath: 'C:/Users/wsrji/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe'
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
  await page.goto('file:///' + target.replace(/\\/g, '/'));
  await page.waitForTimeout(1200);

  // 展开侧栏分组
  const parents = await page.$$('.nav-parent');
  for (const p of parents) { await p.click().catch(() => {}); }
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(outDir, 'nav-expanded.png'), clip: { x: 0, y: 0, width: 260, height: 900 } });

  // 抽屉
  await page.locator('tbody tr .link, tbody tr button').first().click().catch(() => {});
  await page.waitForTimeout(900);
  await page.screenshot({ path: path.join(outDir, 'drawer.png') });

  await browser.close();
})();
