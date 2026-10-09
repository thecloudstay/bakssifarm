const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const OUT = '/tmp/claude-0/-home-claude/8aadcd31-54f6-53df-a7c5-98a8d42b5d8e/scratchpad/bk/shots/';
const base = 'http://127.0.0.1:8766/';
const q = (o) => '?' + new URLSearchParams(o).toString();
const jobs = [
  ['데스크_동물농장_한우', '', {width:1440,height:900}],
  ['데스크_어장_전국', q({mode:'sea'}), {width:1440,height:900}],
  ['데스크_어장_완도', q({mode:'sea', u:'전남|완도군'}), {width:1440,height:900}],
  ['데스크_어장_구역확대', q({mode:'sea', z:'34.33,126.75,11'}), {width:1440,height:900}],
  ['데스크_어장_전복', q({mode:'sea', sp:'전복'}), {width:1440,height:900}],
  ['데스크_농장_전국', q({mode:'crop'}), {width:1440,height:900}],
  ['데스크_농장_청도', q({mode:'crop', u:'경북|청도군'}), {width:1440,height:900}],
  ['데스크_농장_사과', q({mode:'crop', sp:'사과'}), {width:1440,height:900}],
  ['데스크_농장_도매시장', q({mode:'crop', pin:'d01'}), {width:1440,height:900}],
  ['데스크_어장_품종고르기', q({mode:'sea', pick:1}), {width:1440,height:900}],
  ['폰_동물농장', '', {width:390,height:844}, true],
  ['폰_어장_완도펼침', q({mode:'sea', u:'전남|완도군', open:1}), {width:390,height:844}, true],
  ['폰_농장_전국', q({mode:'crop'}), {width:390,height:844}, true],
  ['폰_농장_품목고르기', q({mode:'crop', pick:1}), {width:390,height:844}, true],
];
(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const only = process.argv[2];
  for (const [name, qq, vp, mob] of jobs) {
    if (only && !name.includes(only)) continue;
    const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: mob ? 2 : 1, isMobile: !!mob, hasTouch: !!mob, locale: 'ko-KR' });
    const page = await ctx.newPage();
    const errs = [];
    page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
    page.on('pageerror', e => errs.push(String(e)));
    await page.goto(base + qq, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: OUT + name + '.png' });
    console.log(name, errs.length ? 'ERR ' + errs.join(' | ') : 'ok');
    await ctx.close();
  }
  await browser.close();
})();
