const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const OUT = '/tmp/claude-0/-home-claude/8aadcd31-54f6-53df-a7c5-98a8d42b5d8e/scratchpad/bk/shots/';
const base = 'http://127.0.0.1:8766';
const jobs = [['글_경락가', '/price/', {width:1440,height:900}], ['글_공동구매', '/gongu/', {width:1440,height:900}], ['글_데이터업체', '/pro/', {width:1440,height:900}], ['글_시군_완도', '/p/전남/완도군/', {width:1440,height:900}], ['글_시군목록', '/p/', {width:1440,height:900}], ['글_콘솔', '/console/', {width:1440,height:900}], ['폰_공동구매', '/gongu/', {width:390,height:844}, true], ['폰_시군_완도', '/p/전남/완도군/', {width:390,height:844}, true]];
(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  for (const [name, p, vp, mob] of jobs) {
    const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: mob ? 2 : 1, isMobile: !!mob, hasTouch: !!mob, locale: 'ko-KR' });
    const page = await ctx.newPage(); const errs = [];
    page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); }); page.on('pageerror', e => errs.push(String(e)));
    await page.goto(base + p, { waitUntil: 'networkidle' }); await page.waitForTimeout(500);
    await page.screenshot({ path: OUT + name + '.png', fullPage: false });
    console.log(name, errs.length ? 'ERR ' + errs.join(' | ') : 'ok');
    await ctx.close();
  }
  await browser.close();
})();
