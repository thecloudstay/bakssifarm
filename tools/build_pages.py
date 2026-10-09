# 박씨팜 글 화면 생성기: 경락가·공동구매·데이터·소개·콘솔·시군 글·사이트 지도·새 소식·robots
# 실행: python3 tools/build_pages.py  (저장소 뿌리에서)
import json, os, re, datetime, html, urllib.parse, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'site')
# 사이트 주소: 환경변수 SITE_BASE_URL(없으면 깃허브 페이지 주소). 하위 경로면 PREFIX 가 '/bakssifarm' 처럼 붙음
BASE = (os.environ.get('SITE_BASE_URL') or 'https://thecloudstay.github.io/bakssifarm').rstrip('/')
PREFIX = urllib.parse.urlparse(BASE).path.rstrip('/')
# 양식(제보·모집·등록)은 넷리파이 양식 기능이 받으므로, 어디에 올라가 있든 넷리파이 주소로 보냄
FORM_BASE = (os.environ.get('FORM_BASE_URL') or 'https://bakssine.netlify.app').rstrip('/')
# 접수함 주소(구글 앱스 스크립트 웹앱 /exec)가 있으면 모든 양식을 그리로 보냄(넷리파이 없이도 동작)
FORM_ENDPOINT = (os.environ.get('FORM_ENDPOINT') or '').strip()
TODAY = datetime.date.today().isoformat()
NOW = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))

def J(p, default=None):
    fp = os.path.join(SITE, 'data', p)
    if not os.path.exists(fp): return default
    return json.load(open(fp, encoding='utf-8'))
LS = J('livestock.json'); AQ = J('aqua.json'); CR = J('crops.json'); PL = J('places.json'); MK = J('markets.json')
PRICE = J('price/latest.json', {}); TRADE = J('trade.json', {'items': []}); SIG = J('signals.json', {'items': []}); GONGU = J('gongu.json', {'items': []}); STATUS = J('status.json', {})
YEARS = LS['years']
E = html.escape
def man(n):
    if n is None: return '–'
    if n >= 100000000: return f'{n / 100000000:.1f}억'.replace('.0억', '억')
    if n >= 10000: return (f'{n / 10000:.0f}만' if n >= 1000000 else f'{n / 10000:.1f}만'.replace('.0만', '만'))
    return f'{n:,.0f}' if float(n).is_integer() else f'{n:,.1f}'
def uname(u): a, b = u.split('|'); return a if a == b else b
def ufull(u): a, b = u.split('|'); return a + ' 전체' if a == b else a + ' ' + b
def upath(u): a, b = u.split('|'); return f'/p/{a}/{b if a != b else a}/'

# 구글 애널리틱스·네이버 서치어드바이저·카카오 열쇠: tools/config.json 또는 환경변수(GA_ID, NAVER_SITE_VERIFICATION, KAKAO_JS_KEY)
CFG = {}
if os.path.exists(os.path.join(ROOT, 'tools', 'config.json')): CFG = json.load(open(os.path.join(ROOT, 'tools', 'config.json'), encoding='utf-8'))
GA = os.environ.get('GA_ID') or CFG.get('ga_id') or ''
NAVER = os.environ.get('NAVER_SITE_VERIFICATION') or CFG.get('naver_verification') or ''
KAKAO = os.environ.get('KAKAO_JS_KEY') or CFG.get('kakao_js_key') or ''
FORM_ENDPOINT = FORM_ENDPOINT or (CFG.get('form_endpoint') or '').strip()
def head_extra():
    h = ''
    if NAVER: h += f'<meta name="naver-site-verification" content="{html.escape(NAVER)}">\n'
    if GA: h += f'<script async src="https://www.googletagmanager.com/gtag/js?id={html.escape(GA)}"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag("js",new Date());gtag("config","{html.escape(GA)}",{{anonymize_ip:true}});</script>\n'
    if KAKAO: h += f'<script>window.BK_CFG={{kakaoKey:"{html.escape(KAKAO)}"}};</script>\n'
    return h
def inject_index():
    p = os.path.join(SITE, 'index.html'); s = open(p, encoding='utf-8').read()
    s = re.sub(r'<!--head-extra-->.*?<!--/head-extra-->', '<!--head-extra-->' + head_extra() + '<!--/head-extra-->', s, flags=re.S)
    s = re.sub(r'https://[a-z0-9.\-]+(?:/bakssine|/bakssifarm)?(?=/og/home\.png|/"|/rss\.xml)', BASE, s)
    open(p, 'w', encoding='utf-8').write(s)
    st = json.load(open(os.path.join(SITE, 'data', 'status.json'), encoding='utf-8')) if os.path.exists(os.path.join(SITE, 'data', 'status.json')) else {}
    st.setdefault('keys', {}).update({'ga': bool(GA), 'naver': bool(NAVER), 'kakao': bool(KAKAO)})
    json.dump(st, open(os.path.join(SITE, 'data', 'status.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
ICON = "data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 32 32%27%3E%3Crect x=%271%27 y=%271%27 width=%2730%27 height=%2730%27 rx=%277%27 fill=%27%232c5530%27/%3E%3Cpath d=%27M6 24.5h20M16 24.5V14.5%27 stroke=%27%23fff%27 stroke-width=%272%27 stroke-linecap=%27round%27/%3E%3Cpath d=%27M16 16.2c-.4-3.9-3.3-6.3-7.4-6.3.3 3.9 3.1 6.4 7.4 6.3Z%27 fill=%27%23fff%27/%3E%3Cpath d=%27M16 14.6c.4-4.3 3.4-7 8-7-.3 4.3-3.4 7.1-8 7Z%27 fill=%27%23fff%27/%3E%3C/svg%3E"
SEAL = '''<svg class="seal" viewBox="0 0 32 32" aria-hidden="true"><rect x="1" y="1" width="30" height="30" rx="7" fill="var(--moss)"/><path d="M6 24.5h20" stroke="#fff" stroke-width="1.8" stroke-linecap="round"/><path d="M16 24.5V14.5" stroke="#fff" stroke-width="1.8" stroke-linecap="round"/><path d="M16 16.2c-.4-3.9-3.3-6.3-7.4-6.3.3 3.9 3.1 6.4 7.4 6.3Z" fill="#fff"/><path d="M16 14.6c.4-4.3 3.4-7 8-7-.3 4.3-3.4 7.1-8 7Z" fill="#fff"/></svg>'''
NAV = [('/', '지도'), ('/price/', '경락가'), ('/buy/', '구입가'), ('/gongu/', '공동구매'), ('/sheet/', '시세 한 장'), ('/pro/', '업체·데이터'), ('/p/', '시군별'), ('/about/', '소개')]
BUY = J('buyprice.json', {'items': [], 'n': 0})

def shell(path, title, desc, body, og=None, extra_head='', jsonld=None, noindex=False):
    url = BASE + path
    nav = ''.join(f'<a href="{p}"{" aria-current=page" if p == path else ""}>{E(t)}</a>' for p, t in NAV)
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>' if jsonld else ''
    return f'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
{'<meta name="robots" content="noindex">' if noindex else ''}
<meta name="theme-color" content="#ffffff">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="박씨팜">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}{og or '/og/home.png'}">
<meta name="twitter:card" content="summary_large_image">
<link rel="alternate" type="application/rss+xml" title="박씨팜 새 소식" href="/rss.xml">
<link rel="icon" href="{ICON}">
<link rel="stylesheet" href="/style.css">
<link rel="stylesheet" href="/page.css">
{head_extra()}{extra_head}{ld}
</head>
<body class="page">
<header class="bar">
  <a class="brand" href="/" aria-label="박씨팜 처음 화면">{SEAL}<span class="word">박씨팜</span></a>
  <nav class="modes pagenav" aria-label="화면">{nav}</nav>
</header>
<main class="wrap">
{body}
{FORM_JS % (json.dumps(FORM_ENDPOINT), PREFIX)}
<footer class="foot">
  <p>박씨팜 — 전국 시군별 가축 사육·양식 어장·대표 품목 지도. 개별 농가·어가의 위치와 이름은 싣지 않습니다. 자료 출처와 갱신 주기는 <a href="/about/">소개</a>에 있습니다.</p>
  <p><a href="/">지도</a><a href="/price/">경락가</a><a href="/buy/">구입가</a><a href="/gongu/">공동구매</a><a href="/pro/">데이터·업체</a><a href="/p/">시군별</a><a href="/rss.xml">새 소식</a><a href="/sitemap.xml">사이트 지도</a></p>
</footer>
</main>
</body>
</html>'''

PAGES = []  # (path, lastmod, priority)
def write(path, htmltext, prio='0.6'):
    fp = os.path.join(SITE, path.strip('/'), 'index.html') if path.endswith('/') else os.path.join(SITE, path.strip('/'))
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    if PREFIX: htmltext = re.sub(r'(href|src|action)="/(?!/)', lambda m: f'{m.group(1)}="{PREFIX}/', htmltext)
    open(fp, 'w', encoding='utf-8').write(htmltext)
    if not path.endswith('.html') or path == '/404.html':
        if path != '/404.html': PAGES.append((path, TODAY, prio))

def form(name, fields, button, thanks):
    h = f'<form class="form" name="{name}" method="POST" action="{FORM_BASE}{thanks}" data-netlify="true" netlify-honeypot="bot-field"><input type="hidden" name="form-name" value="{name}"><p hidden><label>사람이면 비워 두세요 <input name="bot-field"></label></p>'
    for f in fields:
        if f[0] == 'row': h += '<div class="row">' + ''.join(field(x) for x in f[1]) + '</div>'
        else: h += field(f)
    h += f'<label class="agree"><input type="checkbox" name="동의" value="예" required> 적은 연락처는 이 신청의 연락 목적으로만 쓰고, 박씨팜은 판매자·중개인이 아니며 거래의 당사자가 되지 않는다는 점에 동의합니다.</label>'
    h += f'<button class="btn prime wide" type="submit">{E(button)}</button><p class="mini form-msg" hidden></p></form>'
    return h
FORM_JS = '''<script>(function(){var EP=%s;document.querySelectorAll('form.form').forEach(function(f){f.addEventListener('submit',function(e){e.preventDefault();var b=f.querySelector('button[type=submit]');b.disabled=true;b.textContent='보내는 중…';var fd=new FormData(f);var body=new URLSearchParams(fd);var url=EP||f.getAttribute('action');fetch(url,{method:'POST',body:body,mode:EP?'no-cors':'cors'}).then(function(r){if(!EP&&!r.ok)throw new Error(r.status);location.href=f.getAttribute('action').replace(/^https?:\\/\\/[^/]+/,'%s');}).catch(function(){b.disabled=false;b.textContent='다시 보내기';var m=f.querySelector('.form-msg');m.hidden=false;m.textContent='지금은 접수 창구가 응답하지 않습니다. 잠시 뒤 다시 눌러 주세요.';});});});})();</script>'''
def field(f):
    kind, name, label = f[0], f[1], f[2]
    req = ' required' if (len(f) > 3 and f[3]) else ''
    if kind == 'text': return f'<label>{E(label)}<input type="text" name="{E(name)}"{req} placeholder="{E(f[4]) if len(f) > 4 else ""}"></label>'
    if kind == 'tel': return f'<label>{E(label)}<input type="tel" name="{E(name)}"{req} placeholder="010-0000-0000" autocomplete="tel"></label>'
    if kind == 'num': return f'<label>{E(label)}<input type="number" name="{E(name)}"{req} min="0" step="any" placeholder="{E(f[4]) if len(f) > 4 else ""}"></label>'
    if kind == 'date': return f'<label>{E(label)}<input type="date" name="{E(name)}"{req}></label>'
    if kind == 'area': return f'<label>{E(label)}<textarea name="{E(name)}" rows="4"{req} placeholder="{E(f[4]) if len(f) > 4 else ""}"></textarea></label>'
    if kind == 'sel': return f'<label>{E(label)}<select name="{E(name)}"{req}>' + ''.join(f'<option>{E(o)}</option>' for o in f[4]) + '</select></label>'
    return ''
SIGUN_OPTS = sorted(set(ufull(u) for u in [g['properties']['u'] for g in J('units.json')['objects']['units']['geometries']]))

# ── 경락가 화면
def price_page():
    ek = PRICE.get('ekape'); at = PRICE.get('at') or ''
    b = '<p class="crumb"><a href="/">박씨팜</a> › 경락가</p><h1 class="title">경락가 조회</h1><p class="lead">소·돼지는 축산물품질평가원 등급별 경락가, 농산물은 공영도매시장 경락가, 수산물은 수협 위판 시세. 연동창구가 붙는 순서대로 이 화면에 들어옵니다.</p>'
    b += '<div class="statusbar">' + ''.join(f'<span class="{c}"><i></i>{E(t)}</span>' for t, c in [('축산물품질평가원 등급별 경락가', 'on' if ek else 'soon'), ('공판장별 실시간 경매', 'soon'), ('농산물 도매시장 경락가', 'soon'), ('수협 위판 시세', 'soon')]) + '</div>'
    b += '<h2>오늘의 이상 신호 — 급등·급락, 고수온, 폐사</h2>'
    sig = SIG.get('items', [])
    if sig:
        b += '<table class="t"><tr><th>구분</th><th>신호</th><th>지역</th><th>설명</th></tr>' + ''.join(f'<tr><td class="{"bad" if i["level"] == "경보" else "wait"}">{E(i["level"])} · {E(i["kind"])}</td><td>{E(i["title"])}</td><td>{E(ufull(i["area"]) if "|" in i["area"] else i["area"])}</td><td>{E(i["body"])}<br><span class="mini">{E(i["src"])}</span></td></tr>' for i in sig) + '</table>'
    else:
        b += '<p>고수온·저수온(국립해양조사원 실측 수온, 매일), 경락가 급등락(직전 5거래일 중위값 대비 ±5%), 가축전염병 발생(재난안전데이터)을 아침마다 살펴 여기와 지도 첫 화면, 텔레그램 보고에 올립니다. 지금은 잡힌 신호가 없습니다.</p>'
    b += '<h2>소·돼지 등급별 경락가</h2>'
    if ek:
        b += f'<p class="mini">축산물품질평가원 · {E(at)} 기준 · 원/㎏</p>'
        for sec in ek:
            b += f'<h3>{E(sec["title"])}</h3><table class="t"><tr><th>등급</th><th class="num">평균 경락가</th><th class="num">전일 대비</th><th class="num">두수</th></tr>'
            for r in sec['rows']:
                d = r.get('d'); dc = 'ok' if (d or 0) > 0 else 'bad' if (d or 0) < 0 else ''
                b += f'<tr><td>{E(r["g"])}</td><td class="num">{r["p"]:,}</td><td class="num {dc}">{("+" if (d or 0) > 0 else "") + format(d, ",") if d is not None else "–"}</td><td class="num">{r.get("n", "–")}</td></tr>'
            b += '</table>'
    else:
        b += '''<div class="note">공공데이터포털에서 받은 열쇠를 저장소 비밀값(DATA_GO_KR_KEY)에 넣으면 수집기가 아침마다 전날 경락가를 받아 이 표를 채웁니다. 아래는 표가 어떻게 보이는지 확인용 <span class="tag">예시 숫자</span>입니다.</div>
<h3>한우 거세 <span class="tag">예시 숫자</span></h3><table class="t"><tr><th>등급</th><th class="num">평균 경락가(원/㎏)</th><th class="num">전일 대비</th><th class="num">두수</th></tr>
<tr class="ex"><td>1++</td><td class="num">23,180</td><td class="num">+120</td><td class="num">예시</td></tr><tr class="ex"><td>1+</td><td class="num">21,040</td><td class="num">−40</td><td class="num">예시</td></tr><tr class="ex"><td>1</td><td class="num">19,350</td><td class="num">+85</td><td class="num">예시</td></tr><tr class="ex"><td>2</td><td class="num">16,220</td><td class="num">0</td><td class="num">예시</td></tr><tr class="ex"><td>3</td><td class="num">12,480</td><td class="num">−60</td><td class="num">예시</td></tr></table>
<h3>돼지 탕박 <span class="tag">예시 숫자</span></h3><table class="t"><tr><th>등급</th><th class="num">평균 경락가(원/㎏)</th><th class="num">전일 대비</th><th class="num">두수</th></tr>
<tr class="ex"><td>1+</td><td class="num">5,820</td><td class="num">+35</td><td class="num">예시</td></tr><tr class="ex"><td>1</td><td class="num">5,610</td><td class="num">+22</td><td class="num">예시</td></tr><tr class="ex"><td>2</td><td class="num">4,980</td><td class="num">−10</td><td class="num">예시</td></tr><tr class="ex"><td>등외</td><td class="num">3,900</td><td class="num">0</td><td class="num">예시</td></tr></table>'''
    b += '<h2>공판장별 경매</h2><p>전국 축산물 공판장 13곳의 당일 경매는 축산물품질평가원 실시간 경매 창구(소·돼지, 등급별)로 받습니다. 열쇠가 연결되면 공판장을 고를 수 있는 표가 이 자리에 들어오고, 지도의 공판장 핀에서도 바로 보입니다.</p>'
    b += '<table class="t"><tr><th>공판장</th><th>지역</th><th>연결</th></tr>' + ''.join(f'<tr><td>{E(m["name"])}</td><td>{E(m["sido"] + " " + m["sigun"])}</td><td class="wait">연동 전</td></tr>' for m in MK['items'] if m['type'] == '공판장') + '</table>'
    b += '<h2>농산물 도매시장 경락가</h2><p>공영도매시장 32곳의 품목·등급별 경락가는 농림축산식품부 도매시장 통합 창구(농넷)로 받습니다. 지도의 <a href="/?mode=crop">농장 보기</a>에서 시군을 누르면 그 지역 대표 품목의 경락가가 함께 보이도록 준비하고 있습니다.</p>'
    b += '<h2>수산물 위판 시세</h2><p>수협 위판장 63곳의 품종별 위판 시세는 수협중앙회 위판정보 창구로 받습니다. 지도의 <a href="/?mode=sea">어장 보기</a>에서 위판장을 누르면 보이게 됩니다.</p>'
    b += '<h2>수입 단가와 비교</h2>'
    tr = TRADE.get('items', [])
    if tr:
        b += '<p class="mini">관세청 수출입실적(월) · 달러/㎏ · 국내 경락가·구입가와 나란히 보는 용도</p><table class="t"><tr><th>품목(관세 부호)</th><th class="num">최근 달 수입 단가</th><th class="num">수입량(톤)</th><th>비교 대상</th></tr>'
        for it in tr:
            r = it['rows'][-1] if it['rows'] else None
            wt = f'{r["wgt_t"]:,}' if r else '–'; up = f'{r["usd_kg"]} 달러' if r else '–'
            b += f'<tr><td>{E(it["name"])} <span class="mini">{E(it["hs"])}</span></td><td class="num">{up}</td><td class="num">{wt}</td><td>{E(it["cmp"])}</td></tr>'
        b += '</table>'
    else:
        b += '<p>쇠고기·돼지고기·옥수수·대두박·어분·전복·김·넙치·새우의 월별 수입 단가(관세청 수출입실적)를 받아 국내 경락가·구입가 옆에 나란히 둡니다. 「수입산이 들어오는 값」과 「내가 받는 값」의 차이가 보이면 출하 시점과 사료 구매 시점을 잡기 쉬워집니다. 공공데이터포털 열쇠가 붙으면 자동으로 채워집니다.</p>'
    b += '<h2>내 품목 가격 알림 받기</h2><p>품목과 지역을 적어 두면, 경락가가 들어오기 시작할 때 아침 보고에 함께 넣어 드립니다.</p>'
    b += form('price-alert', [('row', [('sel', '갈래', '갈래', True, ['소', '돼지', '닭·오리', '농산물', '수산물']), ('text', '품목', '품목', True, '예: 한우 거세 1+ / 사과 부사 / 전복')]), ('sel', '지역', '지역(시군)', True, ['전국'] + SIGUN_OPTS), ('tel', '연락처', '연락처(휴대전화)', True), ('text', '메모', '참고(선택)', False, '예: 매주 화요일 출하')], '알림 신청', '/price/thanks/')
    b += '<h2>자료 출처</h2><ul><li>축산물품질평가원 등급판정정보 — 등급별 경락가·공판장 실시간 경매(공공데이터포털, 하루 1,000건 한도)</li><li>농림축산식품부 도매시장 통합 창구(농넷) — 공영도매시장 경락가</li><li>수협중앙회 — 위판 시세</li></ul>'
    write('/price/', shell('/price/', '경락가 조회 — 소·돼지 등급별, 도매시장, 위판 시세 | 박씨팜', '축산물품질평가원 등급별 경락가, 공판장별 경매, 농산물 도매시장 경락가, 수협 위판 시세를 한 화면에서. 내 품목 가격 알림 신청.', b, '/og/price.png'), '0.8')
    write('/price/thanks/', shell('/price/thanks/', '알림 신청이 접수되었습니다 | 박씨팜', '경락가 알림 신청 접수', '<h1 class="title">알림 신청이 접수되었습니다</h1><p class="lead">경락가가 들어오기 시작하면 적어 주신 연락처로 안내드립니다. <a href="/price/">경락가 화면으로 돌아가기</a></p>', noindex=True))

# ── 구입가 시세판(옆집은 사료·종묘·자재를 얼마에 사나)
BUY_KINDS = ['배합사료(소)', '배합사료(돼지)', '배합사료(닭·오리)', '조사료(볏짚·건초·사일리지)', '양식 사료(배합)', '양식 사료(생사료)', '종묘·치어', '종자·묘목', '비료', '농약·동물약품', '포장 박스·상자(농산물)', '스티로폼 상자·아이스팩(수산물)', '그물망·봉지·라벨', '농자재(비닐·끈·지주)', '어구·양식 자재', '기타']
def buy_page():
    items = BUY.get('items', []); n = BUY.get('n', 0)
    b = '<p class="crumb"><a href="/">박씨팜</a> › 구입가</p><h1 class="title">옆집은 얼마에 사나 — 원자료 구입가 시세판</h1><p class="lead">사료·종묘·비료·자재를 남들은 얼마에 사는지. 농가·어가가 익명으로 적어 준 구입가를 시군별 중위값으로 보여 줍니다. 제보하면 「내 가격은 우리 시군보다 몇 % 비싼지」 성적표를 바로 받습니다. 박씨팜은 팔지도 사지도 않습니다.</p>'
    b += '<div class="grid3"><div class="card"><h3>왜 중위값인가</h3><p>가장 싼 값·가장 비싼 값에 흔들리지 않게 가운데 값을 씁니다. 제보 5건이 모여야 숫자를 엽니다.</p></div><div class="card"><h3>누가 제보하나</h3><p>영수증·거래명세서 기준으로 농가·어가가 직접. 업체 홍보 가격은 받지 않습니다.</p></div><div class="card"><h3>무엇을 돌려주나</h3><p>제보자에게 시군 중위값 대비 내 가격 차이, 같은 품목 전국 흐름을 보냅니다.</p></div></div>'
    b += '<h2>시군별 구입가 중위값</h2>'
    if items:
        b += '<table class="t"><tr><th>품목·규격</th><th>지역</th><th class="num">중위 단가</th><th class="num">제보</th><th>최근</th></tr>'
        for it in items:
            b += f'<tr><td>{E(it["kind"])} · {E(it["item"])}</td><td>{E(it["area"])}</td><td class="num">{it["median"]:,}원/{E(it["unit"])}</td><td class="num">{it["n"]}건</td><td>{E(it["last"])}</td></tr>'
        b += f'</table><p class="mini">제보 {n}건 집계 · 5건 미만인 품목·시군은 숫자를 열지 않습니다.</p>'
    else:
        b += '<div class="empty">아직 공개할 만큼 모이지 않았습니다. 품목·시군별로 제보 5건이 모이면 중위값을 엽니다. 첫 제보를 남겨 주세요 — 제보자에게는 모이는 대로 먼저 알려 드립니다.</div>'
    b += '<h2>내 구입가 제보하기</h2><p>연락처는 성적표와 알림에만 쓰고 공개하지 않습니다. 농장 이름도 받지 않습니다.</p>'
    b += form('buy-report', [('row', [('sel', '종류', '종류', True, BUY_KINDS), ('text', '품목규격', '품목·규격', True, '예: 비육 후기 25㎏ 포대 / 전복 치패 2㎝ / 요소비료 20㎏')]), ('row', [('num', '단가', '단가(원)', True, '예: 14500'), ('sel', '단위', '단위', True, ['포대', '㎏', '톤', '마리', '개', '병', '롤', '기타'])]), ('row', [('sel', '지역', '지역(시군)', True, SIGUN_OPTS), ('sel', '구매처', '구매처 종류', True, ['농협·수협', '대리점', '공장 직거래', '온라인', '종묘장·육묘장', '기타'])]), ('row', [('date', '구입일', '구입일', True), ('sel', '결제', '결제 방식', False, ['현금·즉시', '외상(월말)', '외상(출하 후)', '기타'])]), ('tel', '연락처', '연락처(휴대전화, 성적표 받을 번호)', True), ('text', '메모', '참고(선택)', False, '예: 운송비 포함, 10포대 이상 할인')], '제보하고 성적표 받기', '/buy/thanks/')
    b += '<h2>어떻게 쓰이나</h2><ol class="steps"><li>제보가 들어오면 품목·규격·시군별로 묶어 중위값을 냅니다(5건 이상).</li><li>제보자에게 「내 가격 vs 우리 시군 중위값」 차이를 문자로 보냅니다.</li><li>차이가 큰 시군은 <a href="/gongu/">공동구매 모집</a>으로 이어 줍니다. 업체 견적은 그때 받습니다.</li><li>집계값은 시군 단위로만 공개하고, 개별 제보는 공개하지 않습니다.</li></ol>'
    write('/buy/', shell('/buy/', '옆집은 얼마에 사나 — 사료·종묘·비료·자재 구입가 시세판 | 박씨팜', '사료·종묘·비료·농자재를 남들은 얼마에 사는지 시군별 중위값으로. 익명 제보하고 내 가격 성적표 받기.', b, '/og/buy.png'), '0.8')
    write('/buy/thanks/', shell('/buy/thanks/', '제보가 접수되었습니다 | 박씨팜', '구입가 제보 접수', '<h1 class="title">제보가 접수되었습니다</h1><p class="lead">같은 품목·시군 제보가 5건 모이면 중위값과 내 가격 차이를 문자로 보내 드립니다. <a href="/buy/">구입가 시세판으로</a></p>', noindex=True))

# ── 공동구매 모집판
def gongu_page():
    items = GONGU.get('items', [])
    b = '<p class="crumb"><a href="/">박씨팜</a> › 공동구매</p><h1 class="title">사료·박스·자재 공동구매 모집판</h1><p class="lead">같은 시군 농가·어가끼리 모아서 사면 배합사료·양식 사료·포장 박스·스티로폼 상자·비료·농자재를 더 싸게 받을 수 있습니다. 특히 포장 박스는 규격이 같고 부피가 커서 한 차로 모으는 효과가 가장 큽니다. 박씨팜은 모집을 열고 참여자를 모아 드릴 뿐, 판매자나 중개인이 아닙니다.</p>'
    b += '<div class="grid3"><div class="card"><h3>왜 같은 시군끼리인가</h3><p>사료·박스는 운송비가 큰 몫입니다. 한 차에 실어 한 동선으로 돌면 그만큼 내려갑니다. 박스는 같은 규격(5㎏·10㎏·15㎏ 상자)끼리 묶으면 인쇄판 비용도 나눕니다.</p></div><div class="card"><h3>지도와 이어집니다</h3><p>시군별 사육 마릿수·양식 면허 수를 보면 어디서 모집이 성립할지 먼저 압니다.</p></div><div class="card"><h3>돈은 박씨팜을 거치지 않습니다</h3><p>모집이 성립하면 참여자와 공급처가 직접 계약합니다. 박씨팜은 연락처만 전달합니다.</p></div></div>'
    b += '<h2>지금 열려 있는 모집</h2>'
    if items:
        b += '<table class="t"><tr><th>번호</th><th>종류·품목</th><th>지역</th><th class="num">목표</th><th class="num">모인 양</th><th>마감</th><th>상태</th></tr>'
        for it in items:
            b += f'<tr><td>{E(it["id"])}</td><td>{E(it["kind"])} · {E(it["item"])}</td><td>{E(it["area"])}</td><td class="num">{E(str(it["goal"]))}</td><td class="num">{E(str(it.get("got", 0)))}</td><td>{E(it["due"])}</td><td class="{"ok" if it.get("status") == "성립" else "wait"}">{E(it.get("status", "모집 중"))}</td></tr>'
        b += '</table>'
    else:
        b += '<div class="empty">아직 열린 모집이 없습니다. 첫 모집을 열어 주세요. 열리면 이 자리에 번호와 함께 올라갑니다.</div>'
    b += '<h2>진행 절차</h2><ol class="steps"><li>모집 열기 — 종류·품목·규격·목표 수량·마감일을 적습니다. 하루 안에 번호를 붙여 모집판에 올립니다.</li><li>참여 신청 — 같은 시군 농가가 번호와 수량을 적어 신청합니다. 목표에 닿으면 「성립」으로 바뀝니다.</li><li>견적 받기 — 성립된 모집은 공급처(사료 공장·대리점·농자재상) 두세 곳에 견적을 받아 참여자 모두에게 보냅니다.</li><li>직접 계약 — 참여자가 공급처와 직접 계약하고 결제합니다. 박씨팜은 돈을 받지 않습니다.</li></ol>'
    b += '<h2>모집 열기</h2>' + form('gongu-open', [('row', [('sel', '종류', '종류', True, ['배합사료(소)', '배합사료(돼지)', '배합사료(닭·오리)', '조사료(볏짚·건초)', '양식 사료', '비료', '포장 박스·상자(농산물)', '스티로폼 상자·아이스팩(수산물)', '그물망·봉지·라벨', '농자재(비닐·끈·지주)', '어구·양식 자재', '기타']), ('text', '품목규격', '품목·규격', True, '예: 비육 후기 25㎏ 포대')]), ('row', [('sel', '지역', '지역(시군)', True, SIGUN_OPTS), ('num', '목표수량', '목표 수량(포대·톤·개)', True, '예: 400')]), ('row', [('date', '마감일', '마감일', True), ('tel', '연락처', '연락처(휴대전화)', True)]), ('text', '이름', '이름 또는 농장 이름', True, '예: 박씨농장'), ('area', '설명', '참여자에게 알릴 내용(선택)', False, '예: 매달 1일 수령, 농장 앞 하차 가능')], '모집 열기', '/gongu/thanks/')
    b += '<h2>참여 신청</h2>' + form('gongu-join', [('row', [('text', '모집번호', '모집 번호', True, '예: 공구-0001'), ('num', '수량', '참여 수량', True, '예: 40')]), ('row', [('sel', '지역', '지역(시군)', True, SIGUN_OPTS), ('tel', '연락처', '연락처(휴대전화)', True)]), ('text', '이름', '이름 또는 농장 이름', True, '')], '참여 신청', '/gongu/thanks/')
    b += '<h2>자주 묻는 것</h2><h3>가격은 누가 정하나요</h3><p>공급처가 견적을 냅니다. 박씨팜은 견적을 모아 비교해 보여 드릴 뿐입니다.</p><h3>수수료가 있나요</h3><p>농가 참여는 무료입니다. 공급처가 박씨팜에 업체 등록(유료)을 하면 모집 성립 소식을 먼저 받습니다.</p><h3>개인정보는요</h3><p>연락처는 그 모집의 연락에만 쓰고, 모집이 끝나면 지웁니다. 지도에는 어떤 농가의 위치도 올리지 않습니다.</p>'
    write('/gongu/', shell('/gongu/', '사료·자재 공동구매 모집판 — 같은 시군끼리 모아서 싸게 | 박씨팜', '배합사료·양식 사료·비료·농자재를 같은 시군 농가끼리 모아 사는 모집판. 모집 열기와 참여 신청. 박씨팜은 판매자가 아닙니다.', b, '/og/gongu.png'), '0.8')
    write('/gongu/thanks/', shell('/gongu/thanks/', '접수되었습니다 | 박씨팜', '공동구매 신청 접수', '<h1 class="title">접수되었습니다</h1><p class="lead">하루 안에 적어 주신 연락처로 안내드립니다. 모집은 번호를 붙여 <a href="/gongu/">모집판</a>에 올립니다.</p>', noindex=True))

# ── 데이터·업체
def pro_page():
    # 면허 만료 연도 분포(어장 자료에서)
    exp = collections.Counter()
    adir = os.path.join(SITE, 'data', 'aqua')
    for fn in os.listdir(adir):
        for z in json.load(open(os.path.join(adir, fn), encoding='utf-8')):
            if z.get('e') and z['k'] in 'PHY':
                m = re.search(r'(20\d\d)', str(z['e']))
                if m: exp[m.group(1)] += 1
    years = sorted(exp)[:8]
    b = '<p class="crumb"><a href="/">박씨팜</a> › 업체·데이터</p><h1 class="title">업체와 기관을 위한 박씨팜</h1><p class="lead">농가에게는 전부 무료입니다. 돈은 농가와 거래하는 쪽 — 사료·박스·종묘·도축·운송 업체, 보험·금융, 지자체 — 이 냅니다. 박씨팜은 거래에 끼지 않고 숫자만 다룹니다. 그래서 「이 숫자엔 우리 이해관계가 없다」고 말할 수 있습니다.</p>'
    b += '<h2>네 가지 상품</h2><div class="grid2">'
    b += '<div class="card on"><h3>1. 산지 시세 한 장 <span class="tag mute">시험 발송 중</span></h3><p>소·돼지 등급별 경락가(전국·공판장별), 돈육 대표가격, 수입 단가, 위판·도매 시세, 오늘의 이상 신호를 아침마다 한 장으로. 1858년부터 시세만 팔아 온 미국 어너 배리 방식을 한국 축·수산에 그대로. 가공·유통·사료 업체의 아침 회의용.</p><p><a href="/sheet/">오늘 시세 한 장 보기 →</a></p><div class="pricebox"><b>업체 구독</b><span>가격 확정 전 · 시험 발송 신청은 시세 한 장 화면에서</span></div></div>'
    b += '<div class="card"><h3>2. 우리 업체 이름이 붙은 화면 <span class="tag">바로 시험 가능</span></h3><p>사료 대리점·도축장·공판장·수협이 「○○에서 드리는 오늘의 시세」 화면을 자기 농가에게 줍니다. 농가는 공짜, 업체가 냅니다. 미국 곡물 수매업체 1,200곳이 쓰는 부셸 방식. 경락가·우리 시군 구입가·공동구매 성립 소식·이상 신호가 들어갑니다.</p><p><a href="/partner/?biz=예시 사료 대리점&u=전남|고흥군">화면 예시 보기 →</a></p><div class="pricebox"><b>화면 사용료</b><span>가격 확정 전 · 아래 업체 등록에서 「내 화면」 표시</span></div></div>'
    b += '<div class="card"><h3>3. 지역 수요·원가 지수 <span class="tag">자료 쌓는 중</span></h3><p>구입가 제보와 출하 자료가 쌓이면 시군·축종별 원가·수익 지수와 리별 사료 수요 지도, 진입·이탈 지수가 나옵니다. 보험사·농협 금융·지자체가 사는 층. 생산자가 만든 미국 캐틀팩스처럼, 개별 농가 자료는 절대 밖으로 나가지 않고 집계만 나갑니다.</p><p class="mini" style="margin-top:8px">양식 면허 만료 달력(어장정보도): ' + ' · '.join(f'{y}년 {exp[y]:,}건' for y in years) + '</p></div>'
    b += '<div class="card"><h3>4. 공동구매 견적 참여 <span class="tag mute">모집판 성립 때</span></h3><p>포장 박스·조사료·자재처럼 규제가 없는 품목부터, 같은 시군 농가의 수요가 모이면 등록 업체에 먼저 알리고 견적을 받습니다. 돈과 물건은 박씨팜을 거치지 않습니다.</p><p><a href="/gongu/">모집판 보기 →</a></p></div></div>'
    b += '<h2>업체 등록</h2><p>지역과 업종을 적어 주시면 그 시군에서 공동구매가 성립할 때 먼저 알려 드리고, 원하시면 「우리 업체 이름 화면」을 만들어 드립니다. 등록은 지금 무료이며, 유료 전환 전에 미리 안내드립니다.</p>'
    b += form('biz', [('row', [('sel', '업종', '업종', True, ['사료 공장', '사료 대리점', '조사료', '포장 박스·포장재', '도축·가공', '운송', '동물병원·수의', '종축·종묘·종자', '어구·양식 자재', '비료·농자재', '보험·금융', '지자체·협회', '기타']), ('text', '상호', '상호', True, '')]), ('row', [('sel', '지역', '주된 지역(시군)', True, ['전국'] + SIGUN_OPTS), ('text', '담당', '담당자 이름', True, '')]), ('row', [('tel', '연락처', '연락처', True), ('text', '전자우편', '전자우편(선택)', False, '')]), ('row', [('sel', '원하는것', '원하는 것', True, ['우리 업체 이름 화면', '시세 한 장 구독', '공동구매 견적 참여', '지역 수요 보고서', '아직 모름']), ('text', '농가수', '거래 농가 수(대략, 선택)', False, '예: 120')]), ('area', '소개', '취급 품목과 배송 가능 지역', True, '예: 비육우 배합사료, 전남 서부 배송')], '업체 등록', '/pro/thanks/')
    b += '<h2>하지 않는 것 — 해외에서 무너진 곳이 가르쳐 준 것</h2><ul><li>농가에게 월 회비를 받지 않습니다(농가 회원비를 받던 곳은 전부 접었습니다).</li><li>직접 팔거나 재고를 들거나 결제를 대신하지 않습니다(거래를 떠안은 곳은 5년 안에 무너졌습니다).</li><li>「연결해 드립니다」 성사 수수료를 받지 않습니다. 업체는 등록비·화면 사용료·구독료만 냅니다.</li><li>개별 농가·어가의 위치·이름·연락처는 어떤 상품에도 넣지 않습니다. 가장 작은 단위는 리·읍면동입니다.</li></ul>'
    write('/pro/', shell('/pro/', '업체와 기관을 위한 박씨팜 — 시세 한 장 구독, 업체 이름 화면, 지역 수요 지수 | 박씨팜', '사료·박스·도축·운송 업체와 보험·금융·지자체를 위한 상품: 산지 시세 한 장 구독, 우리 업체 이름 화면, 지역 수요·원가 지수, 공동구매 견적 참여.', b, '/og/pro.png'), '0.7')
    write('/pro/thanks/', shell('/pro/thanks/', '등록되었습니다 | 박씨팜', '업체 등록 접수', '<h1 class="title">등록되었습니다</h1><p class="lead">확인 뒤 연락드립니다. 「우리 업체 이름 화면」을 고르셨으면 화면 주소를 함께 보내 드립니다. <a href="/pro/">업체·데이터 화면으로</a></p>', noindex=True))

# ── 산지 시세 한 장(어너 배리 식) — 아침마다 다시 생성되는 한 장
def sheet_page():
    ek = PRICE.get('ekape') or []; rep = PRICE.get('pigRep') or []; ab = J('price/abattoir.json', {}); sig = SIG.get('items', []); tr = TRADE.get('items', []); buy = BUY.get('items', [])
    d = PRICE.get('date') or TODAY
    b = f'<p class="crumb"><a href="/">박씨팜</a> › 시세 한 장</p><h1 class="title">산지 시세 한 장 <small class="mini">{E(d)} 기준</small></h1><p class="lead">축·수산 가공·유통·사료 업체의 아침 회의용 한 장. 등급별 경락가와 공판장별 차이, 돈육 대표가격, 수입 단가, 구입가 중위값, 오늘의 이상 신호를 한 화면에. 매일 아침 자동으로 다시 만들어집니다.</p>'
    b += '<div class="statusbar">' + ''.join(f'<span class="{c}"><i></i>{E(t)}</span>' for t, c in [('경락가 ' + ('연동' if ek else '연동 전'), 'on' if ek else 'soon'), ('수입 단가 ' + ('연동' if tr else '연동 전'), 'on' if tr else 'soon'), ('위판 시세 연동 전', 'soon'), ('이상 신호 ' + (f'{len(sig)}건' if sig else '없음'), 'off' if sig else 'on')]) + '</div>'
    b += '<h2>소·돼지 등급별 경락가</h2>'
    if ek:
        for sec in ek:
            b += f'<h3>{E(sec["title"])}</h3><table class="t"><tr><th>등급</th><th class="num">전국 평균(원/㎏)</th><th class="num">전일 대비</th><th class="num">두수</th><th>공판장별(높은 순)</th></tr>'
            for r in sec['rows']:
                dd = r.get('d'); dc = 'ok' if (dd or 0) > 0 else 'bad' if (dd or 0) < 0 else ''
                abs_ = sorted((r.get('ab') or {}).items(), key=lambda x: -x[1])
                b += f'<tr><td>{E(r["g"])}</td><td class="num">{r["p"]:,}</td><td class="num {dc}">{("+" if (dd or 0) > 0 else "") + format(dd, ",") if dd is not None else "–"}</td><td class="num">{r.get("n") or "–"}</td><td class="mini">{E(" · ".join(f"{k} {v:,}" for k, v in abs_[:5]))}</td></tr>'
            b += '</table>'
        if rep: b += '<p class="mini">돈육 대표가격: ' + ' · '.join(f'{x["date"]} {x["kind"]} {x["p"]:,}원' for x in rep if x.get('p')) + '</p>'
    else:
        b += '<p>공공데이터포털 열쇠가 붙으면 이 자리에 전날 경락가가 등급별·공판장별로 들어옵니다. 지금은 표의 틀만 있습니다.</p>'
    b += '<h2>수입 단가(관세청, 달러/㎏)</h2>'
    if tr: b += '<table class="t"><tr><th>품목</th><th class="num">최근 달 단가</th><th class="num">수입량(톤)</th><th>비교</th></tr>' + ''.join(f'<tr><td>{E(it["name"])}</td><td class="num">{(it["rows"][-1]["usd_kg"] if it["rows"] else "–")}</td><td class="num">{(format(it["rows"][-1]["wgt_t"], ",") if it["rows"] else "–")}</td><td>{E(it["cmp"])}</td></tr>' for it in tr) + '</table>'
    else: b += '<p>쇠고기·돼지고기·옥수수·대두박·어분·전복·김·넙치·새우. 열쇠가 붙으면 매달 3일 갱신.</p>'
    b += '<h2>구입가 중위값(제보 5건 이상)</h2>'
    if buy: b += '<table class="t"><tr><th>품목</th><th>지역</th><th class="num">중위 단가</th><th class="num">제보</th></tr>' + ''.join(f'<tr><td>{E(it["kind"])} · {E(it["item"])}</td><td>{E(it["area"])}</td><td class="num">{it["median"]:,}원/{E(it["unit"])}</td><td class="num">{it["n"]}</td></tr>' for it in buy[:12]) + '</table>'
    else: b += '<p>아직 공개할 만큼 모이지 않았습니다. <a href="/buy/">구입가 시세판</a>에 제보가 쌓이면 품목·시군별 중위값이 여기 실립니다.</p>'
    b += '<h2>오늘의 이상 신호</h2>'
    if sig: b += '<ul>' + ''.join(f'<li><b>{E(i["level"])} · {E(i["kind"])}</b> {E(i["title"])} — {E(i["body"])}</li>' for i in sig) + '</ul>'
    else: b += '<p>잡힌 신호가 없습니다(고수온·저수온, 경락가 급등락, 가축전염병).</p>'
    b += '<h2>시험 발송 신청(업체·기관)</h2><p>아침마다 이 한 장을 전자우편으로 받습니다. 시험 기간은 무료이며, 유료 전환 전에 미리 안내드립니다. 농가는 신청 없이 이 화면을 그냥 보시면 됩니다.</p>'
    b += form('sheet-sub', [('row', [('sel', '업종', '업종', True, ['사료 공장·대리점', '도축·가공', '유통·급식', '수산 가공·유통', '보험·금융', '지자체·협회·연구', '언론', '기타']), ('text', '상호', '상호·기관명', True, '')]), ('row', [('text', '전자우편', '받을 전자우편', True, ''), ('text', '관심품목', '관심 품목(선택)', False, '예: 한우, 돼지, 전복')]), ('tel', '연락처', '연락처(선택)', False)], '시험 발송 신청', '/sheet/thanks/')
    b += '<p class="mini">출처: 축산물품질평가원 등급판정정보 · 관세청 수출입실적 · 국립해양조사원 실측 수온(해루낚 보관) · 박씨팜 구입가 제보. 숫자가 없는 칸은 연동 전입니다.</p>'
    write('/sheet/', shell('/sheet/', f'산지 시세 한 장 — {d} | 박씨팜', '소·돼지 등급별·공판장별 경락가, 돈육 대표가격, 수입 단가, 구입가 중위값, 오늘의 이상 신호를 아침마다 한 장으로. 업체·기관 시험 발송 신청.', b, '/og/price.png'), '0.8')
    write('/sheet/thanks/', shell('/sheet/thanks/', '신청되었습니다 | 박씨팜', '시세 한 장 시험 발송 신청 접수', '<h1 class="title">신청되었습니다</h1><p class="lead">다음 거래일 아침부터 보내 드립니다. <a href="/sheet/">시세 한 장으로</a></p>', noindex=True))

# ── 우리 업체 이름 화면(부셸 식) — ?biz=상호&u=시도|시군 로 업체 이름이 붙은 농가용 화면
def partner_page():
    b = '<p class="crumb"><a href="/">박씨팜</a> › 업체 화면</p><div id="pt-head"><h1 class="title"><span id="pt-biz">업체 이름</span>에서 드리는 오늘의 시세</h1><p class="lead"><span id="pt-area">시군</span> 농가를 위한 화면입니다. 오늘 경락가, 우리 시군 구입가 중위값, 공동구매 모집, 이상 신호를 한 번에. 자료는 박씨팜이 공공 자료와 농가 제보로 만듭니다.</p></div>'
    b += '<div id="pt-sig"></div><h2>오늘 경락가</h2><div id="pt-price"><p class="mini">불러오는 중…</p></div>'
    b += '<h2>우리 시군 구입가 중위값</h2><div id="pt-buy"></div>'
    b += '<h2>우리 시군 공동구매</h2><div id="pt-gongu"></div>'
    b += '<h2>이 화면은</h2><p>업체가 자기 농가에게 주는 화면입니다. 농가는 무료이고 업체가 사용료를 냅니다. 숫자는 업체가 아니라 박씨팜이 만들며, 업체는 숫자를 고칠 수 없습니다. 그래서 농가가 믿고 볼 수 있습니다. <a href="/pro/">우리 업체 화면 만들기 →</a></p>'
    js = """<script>(function(){var P=%s;var q=new URLSearchParams(location.search);var biz=q.get('biz')||'예시 사료 대리점';var u=q.get('u')||'전남|고흥군';var sd=u.split('|')[0],sg=u.split('|')[1];var name=sd===sg?sd:sd+' '+sg;function $(s){return document.querySelector(s)}function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}$('#pt-biz').textContent=biz;$('#pt-area').textContent=name;document.title=biz+'에서 드리는 오늘의 시세 | 박씨팜';function get(f){return fetch(P+'/data/'+f).then(function(r){return r.ok?r.json():null}).catch(function(){return null})}
Promise.all([get('price/latest.json'),get('buyprice.json'),get('gongu.json'),get('signals.json')]).then(function(r){var pr=r[0],buy=r[1],go=r[2],sg2=r[3];var h='';if(pr&&pr.ekape){pr.ekape.forEach(function(sec){h+='<h3>'+esc(sec.title)+' <span class="mini">'+esc(pr.date||'')+'</span></h3><table class="t"><tr><th>등급</th><th class="num">원/㎏</th><th class="num">전일 대비</th></tr>'+sec.rows.map(function(x){return '<tr><td>'+esc(x.g)+'</td><td class="num">'+x.p.toLocaleString('ko-KR')+'</td><td class="num">'+(x.d==null?'–':(x.d>0?'+':'')+x.d.toLocaleString('ko-KR'))+'</td></tr>'}).join('')+'</table>'})}else h='<p>경락가는 공공데이터 열쇠가 붙는 아침부터 들어옵니다. 지금은 틀만 있습니다.</p>';$('#pt-price').innerHTML=h;
var bi=(buy&&buy.items||[]).filter(function(x){return x.area===name});$('#pt-buy').innerHTML=bi.length?'<table class="t"><tr><th>품목</th><th class="num">중위 단가</th><th class="num">제보</th></tr>'+bi.map(function(x){return '<tr><td>'+esc(x.kind)+' · '+esc(x.item)+'</td><td class="num">'+x.median.toLocaleString('ko-KR')+'원/'+esc(x.unit)+'</td><td class="num">'+x.n+'</td></tr>'}).join('')+'</table>':'<p>아직 '+esc(name)+' 제보가 5건 모이지 않았습니다. <a href="'+P+'/buy/">내 구입가 제보하고 성적표 받기 →</a></p>';
var gi=(go&&go.items||[]).filter(function(x){return x.area===name});$('#pt-gongu').innerHTML=gi.length?'<table class="t"><tr><th>번호</th><th>품목</th><th class="num">목표</th><th class="num">모인 양</th><th>상태</th></tr>'+gi.map(function(x){return '<tr><td>'+esc(x.id)+'</td><td>'+esc(x.kind)+' · '+esc(x.item)+'</td><td class="num">'+esc(x.goal)+'</td><td class="num">'+esc(x.got)+'</td><td>'+esc(x.status)+'</td></tr>'}).join('')+'</table>':'<p>열린 모집이 없습니다. <a href="'+P+'/gongu/">사료·박스·자재 모집 열기 →</a></p>';
var si=(sg2&&sg2.items||[]).filter(function(x){return x.area===u||x.area==='전국'});if(si.length)$('#pt-sig').innerHTML='<div class="note"><b>오늘의 이상 신호</b> '+si.map(function(x){return esc(x.kind)+' · '+esc(x.title)}).join(' / ')+'</div>';});})();</script>"""
    write('/partner/', shell('/partner/', '우리 업체 이름이 붙은 오늘의 시세 | 박씨팜', '사료 대리점·도축장·공판장·수협이 자기 농가에게 주는 시세 화면. 오늘 경락가, 우리 시군 구입가 중위값, 공동구매, 이상 신호.', b, '/og/price.png', extra_head='', noindex=True) .replace('<footer class="foot">', js % (json.dumps(PREFIX), ) + '<footer class="foot">'))

# ── 소개
def about_page():
    b = '<p class="crumb"><a href="/">박씨팜</a> › 소개</p><h1 class="title">박씨팜은 무엇을 하나</h1><p class="lead">농장(식물)·어장(어류·패류)·동물농장(가축)을 한 지도에서 봅니다. 시군을 누르면 거기서 무엇을 얼마나 키우는지, 어디서 팔고, 오늘 얼마인지 나오게 만드는 중입니다.</p>'
    b += '<h2>자료 출처와 갱신</h2><table class="t"><tr><th>보기</th><th>자료</th><th>단위</th><th>갱신</th></tr>'
    b += '<tr><td>동물농장</td><td>가축위생방역지원본부 「전국 시군별 사육규모 현황」 35개 축종 (공공데이터포털, 공공누리 제1유형)</td><td>시군 · 2018~2026년 1월</td><td>해마다</td></tr>'
    b += '<tr><td>어장</td><td>국립해양조사원 어장정보도 2025 (개방해) — 양식·마을어업·정치망 면허 구역 11,486곳</td><td>구역 · 시군 집계</td><td>해마다</td></tr>'
    b += '<tr><td>농장</td><td>지리적표시 등록부 (국립농산물품질관리원·산림청·국립수산물품질관리원) 204건</td><td>시군</td><td>등록 때마다</td></tr>'
    b += '<tr><td>경계</td><td>통계청 통계지리정보서비스 시군 경계(2018), 광역시는 구·군 합침</td><td>161개 시군</td><td>–</td></tr>'
    b += '<tr><td>시장</td><td>축산물 공판장 13곳·가축시장 9곳(박씨팜 정리), 수협 위판장 63곳(지구별 조합), 공영도매시장 32곳</td><td>핀</td><td>확인 때마다</td></tr></table>'
    b += '<h2>지키는 것</h2><ul><li>개별 농가·어가의 위치와 이름은 싣지 않습니다. 가장 작은 단위는 리·읍면동입니다.</li><li>예시 숫자는 「예시」라고 씁니다. 확인 전 위치는 「위치 근사」로 표시합니다.</li><li>공공 자료의 출처를 밝히고, 이용 조건을 지킵니다.</li></ul>'
    b += '<h2>해외에서 배운 것</h2><p>시세만 판 미국 어너 배리는 1858년부터 살아 있고, 생산자가 만든 캐틀팩스는 1968년부터, 수매업체가 농가에게 앱을 주는 부셸은 북미 1,200곳에서 쓰입니다. 반대로 거래·재고·물류까지 떠안은 곳(독일 아그란도, 캐나다 파머스 엣지, 인도네시아 이피셔리)은 몇 해 안에 무너졌습니다. 박씨팜은 앞쪽을 따릅니다 — 숫자만 다루고, 돈은 농가가 아니라 업체·기관이 냅니다.</p>'
    b += '<h2>앞으로</h2><ul><li>축산물품질평가원 경락가·실시간 경매, 농산물 도매시장 경락가, 수협 위판 시세 연동</li><li>지방행정 인허가(가축사육업·도축장·사료 공장) 리 단위 집계</li><li>도매시장·산지공판장 경락 원자료(산지 항목)로 시군별 실제 출하 품목·금액 순위 — 등록 수가 아닌 「팔린 돈」 기준</li><li>관세청 수출입실적으로 수입 단가 비교</li><li>카카오 바탕지도(확대 단계)</li></ul>'
    b += '<h2>연락</h2><p>자료 오류, 위치 정정, 제휴는 <a href="/pro/">업체 등록</a> 양식이나 <a href="/gongu/">모집판</a>의 양식으로 남겨 주세요.</p>'
    write('/about/', shell('/about/', '소개 — 자료 출처·갱신·원칙 | 박씨팜', '박씨팜이 쓰는 자료와 출처, 갱신 주기, 개별 농가 비공개 원칙.', b), '0.5')

# ── 콘솔(공개 읽기 전용)
def console_page():
    st = STATUS
    b = '<p class="crumb"><a href="/">박씨팜</a> › 콘솔</p><h1 class="title">콘솔</h1><p class="lead">수집기·연동창구·양식 접수 상태. 이 화면은 읽기 전용이며 숫자는 아침 작업 흐름이 갱신합니다.</p>'
    b += f'<p class="mini">마지막 생성: {E(st.get("built", NOW.strftime("%Y-%m-%d %H:%M")))} (한국 시간)</p>'
    b += '<h2>연동창구·열쇠</h2><div class="statusbar">'
    for k, t in [('data_go_kr', '공공데이터포털 열쇠'), ('kakao', '카카오 지도 열쇠'), ('telegram', '텔레그램 보고'), ('ga', '구글 애널리틱스'), ('naver', '네이버 서치어드바이저'), ('indexnow', '색인 알림(인덱스나우)')]:
        v = (st.get('keys') or {}).get(k)
        b += f'<span class="{"on" if v else "off"}"><i></i>{E(t)} {"연결" if v else "미연결"}</span>'
    b += '</div>'
    b += '<h2>수집기</h2><table class="t"><tr><th>수집기</th><th>마지막 실행</th><th>결과</th><th>메모</th></tr>'
    cols = st.get('collectors') or {}
    for k, t in [('ekape_price', '축평원 등급별 경락가'), ('ekape_live', '축평원 실시간 경매'), ('license', '지방행정 인허가(가축사육업 등)'), ('wholesale', '도매시장 경락가'), ('wharf', '수협 위판 시세'), ('pages', '글 화면·사이트 지도·새 소식'), ('og', '미리보기 그림'), ('indexnow', '색인 알림')]:
        c = cols.get(k) or {}
        ok = c.get('ok'); cls = 'ok' if ok else ('bad' if ok is False else 'wait')
        b += f'<tr><td>{E(t)}</td><td>{E(c.get("at", "–"))}</td><td class="{cls}">{"정상" if ok else ("실패" if ok is False else "대기")}</td><td>{E(c.get("msg", ""))}</td></tr>'
    b += '</table>'
    cnt = st.get('counts') or {}
    b += '<h2>자료 규모</h2><dl class="kv">'
    b += f'<dt>가축 축종</dt><dd>{len(LS["species"])}개 · {len(YEARS)}개 연도</dd><dt>양식 면허 구역</dt><dd>{sum(c["n"] for c in AQ["cells"]):,}곳 · {len(AQ["units"])}개 시군</dd><dt>지리적표시</dt><dd>{len([i for i in CR["items"] if not i["off"]])}건 · {len(CR["units"])}개 시군</dd><dt>핀</dt><dd>공판장·가축시장 {len(MK["items"])} · 위판장 {len(PL["wharfs"])} · 도매시장 {len(PL["markets"])}</dd>'
    b += f'<dt>글 화면</dt><dd>{cnt.get("pages", "–")}</dd><dt>양식 접수</dt><dd>{E(str(cnt.get("forms", "넷리파이 양식 화면에서 확인")))}</dd></dl>'
    b += '<h2>양식(접수함)</h2><p>모집 열기·참여 신청·업체 등록·가격 알림은 넷리파이 양식으로 받습니다. 접수 내용은 넷리파이 콘솔의 「양식」에서 보고, 모집판 반영은 data/gongu.json 을 고쳐 다시 올리면 됩니다.</p>'
    write('/console/', shell('/console/', '콘솔 | 박씨팜', '박씨팜 수집기·열쇠·양식 상태', b, noindex=True))

# ── 시군 글
def sigun_pages():
    units = [g['properties']['u'] for g in J('units.json')['objects']['units']['geometries']]
    last = YEARS[-1]
    # 시군별 가축 상위
    ani = collections.defaultdict(list)
    for s in LS['species']:
        for u, r in s['d'].items():
            y = r['y'][-1]
            if y and y[1] > 0: ani[u].append((s['k'], y[0], y[1], s['w']))
    for u in ani: ani[u].sort(key=lambda x: -x[2])
    idx = collections.defaultdict(list)
    for u in sorted(units):
        sd = u.split('|')[0]; name = ufull(u)
        a = ani.get(u, []); e = AQ['units'].get(u); c = CR['units'].get(u)
        pins = [m for m in MK['items'] if m['sido'] == sd and (m['sigun'] in uname(u) or uname(u) in m['sigun'] + '시' + m['sigun'] + '군')] + [w for w in PL['wharfs'] if w['u'] == u] + [m for m in PL['markets'] if m['u'] == u]
        parts = []
        if a: parts.append('가축 ' + ', '.join(f'{x[0]} {man(x[2])}{x[3]}' for x in a[:3]))
        if e: parts.append('양식 면허 ' + f'{e["n"]:,}건' + (' · ' + ', '.join(t[0] for t in e['top'][:2]) if e['top'] else ''))
        if c: parts.append('대표 품목 ' + ', '.join(c['items'][:3]))
        desc = f'{name} — ' + (' / '.join(parts) if parts else '사육·양식·지리적표시 기록 정리') + f'. {last}년 1월 기준 시군 집계, 개별 농가 위치는 싣지 않습니다.'
        b = f'<p class="crumb"><a href="/">박씨팜</a> › <a href="/p/">시군별</a> › {E(sd)}</p><h1 class="title">{E(name)}</h1><p class="lead">{E(desc)}</p>'
        b += f'<p><a class="btn prime" href="/?u={urllib.parse.quote(u)}">지도에서 보기</a></p>'
        b += '<h2>동물농장 — 무엇을 얼마나 키우나</h2>'
        if a:
            b += f'<table class="t"><tr><th>축종</th><th class="num">농가</th><th class="num">마릿수</th><th class="num">{YEARS[0]}년 대비 농가</th></tr>'
            for k, h, n, w in a[:10]:
                s = next(x for x in LS['species'] if x['k'] == k); r = s['d'][u]['y']
                i0 = next((i for i, v in enumerate(r) if v and v[0] > 0), None)
                ch = f'{(h / r[i0][0] - 1) * 100:+.0f}%' if i0 is not None and i0 < len(r) - 1 and r[i0][0] >= 10 else '–'
                b += f'<tr><td><a href="/?sp={urllib.parse.quote(k)}&u={urllib.parse.quote(u)}">{E(k)}</a></td><td class="num">{h:,}호</td><td class="num">{n:,}{E(w)}</td><td class="num">{ch}</td></tr>'
            b += f'</table><p class="mini">가축위생방역지원본부 사육규모 현황, {last}년 1월 기준.</p>'
        else: b += '<p>이 시군의 가축 사육 기록이 없습니다.</p>'
        b += '<h2>어장 — 양식 면허</h2>'
        if e:
            b += f'<p>양식 면허 <b>{e["n"]:,}건</b>, 면허 면적 <b>{man(e["ha"])}㏊</b>. 마을어장(어촌계) {e["v"][0]}곳 · {man(e["v"][1])}㏊' + (f', 정치망 {e["j"]}곳' if e['j'] else '') + '.</p>'
            if e['top']: b += '<table class="t"><tr><th>품종</th><th class="num">면허</th><th class="num">면적</th></tr>' + ''.join(f'<tr><td><a href="/?mode=sea&sp={urllib.parse.quote(t[0])}&u={urllib.parse.quote(u)}">{E(t[0])}</a></td><td class="num">{t[1]:,}건</td><td class="num">{man(t[2])}㏊</td></tr>' for t in e['top']) + '</table><p class="mini">국립해양조사원 어장정보도 2025. 지도를 확대하면 면허 구역이 하나씩 보입니다.</p>'
        else: b += '<p>이 시군에는 어장 면허 기록이 없습니다.</p>'
        b += '<h2>농장 — 대표 판매 품목</h2>'
        if c:
            b += '<p>' + ', '.join(f'<a href="/?mode=crop&sp={urllib.parse.quote(i)}">{E(i)}</a>' for i in c['items']) + '</p>'
            b += '<table class="t"><tr><th>등록 명칭</th><th>갈래</th><th>등록일</th></tr>' + ''.join(f'<tr><td>{E(x["name"])}</td><td>{E(x["cat"])} · {E(x["kind"])}</td><td>{E(x["date"])}</td></tr>' for x in c['list']) + '</table><p class="mini">지리적표시 등록부(2024년 4월). 주력 품목의 실제 출하 금액(도매시장·공판장 경락 원자료의 산지 기준)이 쌓이는 대로 보탭니다. 등록 농가 수는 쓰지 않습니다.</p>'
        else: b += '<p>아직 지리적표시로 등록된 품목이 없습니다.</p>'
        b += '<h2>팔 곳 — 공판장·가축시장·위판장·도매시장</h2>'
        if pins: b += '<ul>' + ''.join(f'<li><a href="/?mode={"sea" if p["type"] == "위판장" else "crop" if p["type"] == "도매시장" else "ani"}&pin={p["id"]}">{E(p["name"])}</a> <span class="mini">{E(p["type"])}{"" if p.get("verified") else " · 위치 근사"}</span></li>' for p in pins) + '</ul>'
        else: b += '<p>이 시군 안에는 등록된 공판장·위판장·도매시장이 없습니다. 지도에서 이웃 시군의 시장을 보세요.</p>'
        b += f'<p><a href="/gongu/">이 시군에서 사료·자재 공동구매 열기 →</a></p>'
        ld = {'@context': 'https://schema.org', '@type': 'Dataset', 'name': f'{name} 농장·어장·동물농장 현황', 'description': desc, 'url': BASE + upath(u), 'license': 'https://www.kogl.or.kr/info/license.do', 'creator': {'@type': 'Organization', 'name': '박씨팜'}, 'spatialCoverage': name, 'temporalCoverage': f'{YEARS[0]}/{last}'}
        write(upath(u), shell(upath(u), f'{name} 농장·어장·동물농장 — 가축 사육, 양식 면허, 대표 품목 | 박씨팜', desc, b, f'/og/p/{sd}_{uname(u)}.png', jsonld=ld), '0.7')
        idx[sd].append((u, name, a[0][0] if a else None, c['items'][0] if c and c['items'] else None))
    b = '<p class="crumb"><a href="/">박씨팜</a> › 시군별</p><h1 class="title">시군별 보기</h1><p class="lead">161개 시군의 가축 사육·양식 면허·대표 품목을 글로 정리했습니다. 시군을 누르면 자세히, 「지도에서 보기」를 누르면 지도로 갑니다.</p>'
    b += '<div class="toc">' + ''.join(f'<a href="#{E(sd)}">{E(sd)}</a>' for sd in idx) + '</div><div class="sgrid">'
    for sd, lst in idx.items():
        b += f'<h3 id="{E(sd)}">{E(sd)}</h3>' + ''.join(f'<a href="{upath(u)}">{E(uname(u))}<span class="mini"> {E(" · ".join(x for x in [a, c] if x))}</span></a>' for u, name, a, c in lst)
    b += '</div>'
    write('/p/', shell('/p/', '시군별 농장·어장·동물농장 — 161개 시군 | 박씨팜', '전국 161개 시군의 가축 사육, 양식 면허, 대표 판매 품목을 시군별로.', b), '0.7')

def misc():
    write('/404.html', shell('/404.html', '그런 화면이 없습니다 | 박씨팜', '없는 화면', '<h1 class="title">그런 화면이 없습니다</h1><p class="lead">주소가 바뀌었거나 잘못 적힌 것 같습니다. <a href="/">지도로 돌아가기</a> · <a href="/p/">시군별 보기</a></p>', noindex=True))
    # 사이트 지도
    pages = [('/', TODAY, '1.0')] + PAGES
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(f'<url><loc>{BASE}{urllib.parse.quote(p)}</loc><lastmod>{d}</lastmod><priority>{pr}</priority></url>\n' for p, d, pr in pages) + '</urlset>\n'
    open(os.path.join(SITE, 'sitemap.xml'), 'w', encoding='utf-8').write(sm)
    open(os.path.join(SITE, 'robots.txt'), 'w', encoding='utf-8').write(f'User-agent: *\nAllow: /\nDisallow: /console/\nSitemap: {BASE}/sitemap.xml\n')
    # 새 소식(갱신 기록)
    news = J('news.json', [])
    if not news:
        news = [{'date': TODAY, 'title': '박씨팜 문을 엽니다 — 동물농장·어장·농장 한 지도', 'url': '/', 'body': '전국 시군별 가축 사육(35개 축종, 2018~2026), 양식 면허 구역 11,486곳, 지리적표시 대표 품목 204건을 한 지도에 올렸습니다. 공판장·가축시장·수협 위판장·공영도매시장 위치와 경락가 조회, 공동구매 모집판을 함께 엽니다.'}]
    rss = '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>박씨팜 새 소식</title><link>' + BASE + '/</link><description>박씨팜 지도·자료 갱신 소식</description><language>ko</language>\n'
    for n in news[:50]:
        rss += f'<item><title>{E(n["title"])}</title><link>{BASE}{n["url"]}</link><guid>{BASE}{n["url"]}#{n["date"]}</guid><pubDate>{datetime.datetime.strptime(n["date"], "%Y-%m-%d").strftime("%a, %d %b %Y 09:00:00 +0900")}</pubDate><description>{E(n["body"])}</description></item>\n'
    rss += '</channel></rss>\n'
    open(os.path.join(SITE, 'rss.xml'), 'w', encoding='utf-8').write(rss)
    # 상태 갱신(글 화면 수)
    st = STATUS; st['built'] = NOW.strftime('%Y-%m-%d %H:%M'); st.setdefault('counts', {})['pages'] = len(pages)
    st.setdefault('collectors', {})['pages'] = {'ok': True, 'at': NOW.strftime('%Y-%m-%d %H:%M'), 'msg': f'{len(pages)}쪽'}
    json.dump(st, open(os.path.join(SITE, 'data', 'status.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # 사이트 지도 목록(색인 알림용)
    open(os.path.join(ROOT, 'tools', 'urls.txt'), 'w', encoding='utf-8').write('\n'.join(BASE + urllib.parse.quote(p) for p, d, pr in pages) + '\n')

if __name__ == '__main__':
    inject_index(); price_page(); buy_page(); gongu_page(); sheet_page(); partner_page(); pro_page(); about_page(); sigun_pages(); console_page(); misc()
    print('글 화면', len(PAGES) + 1)
