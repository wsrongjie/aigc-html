const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');

(async () => {
  const target = process.argv[2];
  const outDir = process.argv[3];
  const width = parseInt(process.argv[4] || '1440', 10);
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({
    executablePath: 'C:/Users/wsrji/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe'
  });
  const page = await browser.newPage({ viewport: { width, height: 900 }, deviceScaleFactor: width > 700 ? 2 : 2 });
  await page.goto('file:///' + target.replace(/\\/g, '/'));
  await page.waitForSelector('.nav-btn', { timeout: 15000 });
  await page.waitForTimeout(800);

  // 展开所有分组，便于遍历子页面
  for (const p of await page.$$('.nav-parent')) { await p.click().catch(() => {}); }
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(outDir, `w${width}-00-assets.png`) });

  const labels = await page.$$eval('.nav-btn', els => els.map(e => e.textContent.trim()).filter(Boolean));
  console.log(JSON.stringify(labels));
  for (let i = 0; i < labels.length; i++) {
    const btn = page.locator('.nav-btn', { hasText: labels[i] }).first();
    try {
      await btn.click({ timeout: 4000 });
      await page.waitForTimeout(650);
      const name = labels[i].replace(/[\\/:*?"<>|]/g, '');
      await page.screenshot({ path: path.join(outDir, `w${width}-${String(i + 1).padStart(2, '0')}-${name}.png`) });
    } catch (e) {
      console.log('skip', labels[i]);
    }
  }
  await browser.close();
})();
