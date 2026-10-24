const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');

(async () => {
  const target = process.argv[2];
  const outDir = process.argv[3] || path.join(__dirname, 'shots');
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({
    executablePath: 'C:/Users/wsrji/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe'
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  await page.goto('file:///' + target.replace(/\\/g, '/'));
  await page.waitForTimeout(1500);
  await page.screenshot({ path: path.join(outDir, '01-default.png') });

  // 侧栏各导航项截图
  const navs = await page.$$eval('.nav-btn, .nav-parent', els => els.map(e => e.textContent.trim()).filter(Boolean));
  console.log(JSON.stringify(navs));
  await browser.close();
})();
