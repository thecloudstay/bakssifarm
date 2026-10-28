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
PRICE = J('price/latest.json', {}); WH = J('price/wholesale.json', {'items': []}); ORIG = J('origin.json', {'units': {}}); TRADE = J('trade.json', {'items': []}); SIG = J('signals.json', {'items': []}); GONGU = J('gongu.json', {'items': []}); STATUS = J('status.json', {}); WPN = J('wipan.json', {}); SSTK = J('seastock.json', {}); RISK = J('risk.json', {}); BUYS = J('buysignal.json', {}); OPPS = J('opps.json', {}); CROPS = J('cropsignal.json', {}); FC = J('forecast.json', {})
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
    p = os.path.join(SITE, 'map', 'index.html'); s = open(p, encoding='utf-8').read()   # 2026-10-28 지도는 /map/, 첫 화면은 가격 예보판(home_page)
    s = re.sub(r'<base href="[^"]*">', f'<base href="{PREFIX}/">', s)
    s = re.sub(r'<!--head-extra-->.*?<!--/head-extra-->', '<!--head-extra-->' + head_extra() + '<!--/head-extra-->', s, flags=re.S)
    s = re.sub(r'https://[a-z0-9.\-]+(?:/bakssine|/bakssifarm)?(?=/og/home\.png|/"|/rss\.xml)', BASE, s)
    open(p, 'w', encoding='utf-8').write(s)
    st = json.load(open(os.path.join(SITE, 'data', 'status.json'), encoding='utf-8')) if os.path.exists(os.path.join(SITE, 'data', 'status.json')) else {}
    st.setdefault('keys', {}).update({'ga': bool(GA), 'naver': bool(NAVER), 'kakao': bool(KAKAO)})
    json.dump(st, open(os.path.join(SITE, 'data', 'status.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
ICON = "data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 32 32%27%3E%3Crect x=%271%27 y=%271%27 width=%2730%27 height=%2730%27 rx=%277%27 fill=%27%232c5530%27/%3E%3Cpath d=%27M6 24.5h20M16 24.5V14.5%27 stroke=%27%23fff%27 stroke-width=%272%27 stroke-linecap=%27round%27/%3E%3Cpath d=%27M16 16.2c-.4-3.9-3.3-6.3-7.4-6.3.3 3.9 3.1 6.4 7.4 6.3Z%27 fill=%27%23fff%27/%3E%3Cpath d=%27M16 14.6c.4-4.3 3.4-7 8-7-.3 4.3-3.4 7.1-8 7Z%27 fill=%27%23fff%27/%3E%3C/svg%3E"
SEAL = '''<svg class="seal" viewBox="0 0 32 32" aria-hidden="true"><rect x="1" y="1" width="30" height="30" rx="7" fill="var(--moss)"/><path d="M6 24.5h20" stroke="#fff" stroke-width="1.8" stroke-linecap="round"/><path d="M16 24.5V14.5" stroke="#fff" stroke-width="1.8" stroke-linecap="round"/><path d="M16 16.2c-.4-3.9-3.3-6.3-7.4-6.3.3 3.9 3.1 6.4 7.4 6.3Z" fill="#fff"/><path d="M16 14.6c.4-4.3 3.4-7 8-7-.3 4.3-3.4 7.1-8 7Z" fill="#fff"/></svg>'''
NAV = [('/', '가격 예보'), ('/signal/', '근거·적중'), ('/risk/', '위험 예보'), ('/opps/', '수급 기회'), ('/price/', '경락가'), ('/sheet/', '시세 한 장'), ('/map/', '지도'), ('/calc/', '수익 계산'), ('/buy/', '구입가'), ('/gongu/', '공동구매'), ('/pro/', '업체·데이터'), ('/data/', '자료 대장'), ('/p/', '시군별'), ('/about/', '소개')]
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
{alert_bar(path)}
{body}
{FORM_JS % (json.dumps(FORM_ENDPOINT), PREFIX)}
<footer class="foot">
  <p>박씨팜 — 농축수산물 가격 예보. 축산·수산·농산 품목의 값 방향을 근거와 적중률과 함께 매일 아침 알려 드립니다. 물건을 사고팔지 않으며, 개별 농가·어가의 위치와 이름은 싣지 않습니다. 자료 출처와 갱신 주기는 <a href="/about/">소개</a>에 있습니다.</p>
  <p><a href="/">가격 예보</a><a href="/signal/">근거·적중</a><a href="/map/">지도</a><a href="/price/">경락가</a><a href="/buy/">구입가</a><a href="/gongu/">공동구매</a><a href="/pro/">데이터·업체</a><a href="/p/">시군별</a><a href="/rss.xml">새 소식</a><a href="/sitemap.xml">사이트 지도</a></p>
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
def wipan_html(n=20, h2=True):
    if not WPN.get('fish'): return ''
    mo = WPN['month'].replace('-', '년 ') + '월'
    b = (f'<h2>수협 산지 위판 시세 — {mo}</h2>' if h2 else '') + f'<p class="mini">해양수산부 일자별 위탁판매 현황(수협 산지 위판 {WPN["days"]}일치, {WPN["rows"]:,}줄). ㎏당 값은 위판 금액÷위판 중량. 위판 금액 큰 어종 순.' + (f' 앞달({E(WPN.get("prev_month", ""))}) 대비 변화 포함.' if WPN.get('prev_month') else '') + '</p>'
    b += '<table class="t"><tr><th>어종(상태)</th><th class="num">원/㎏</th>' + ('<th class="num">앞달 대비</th>' if WPN.get('prev_month') else '') + '<th class="num">위판 금액</th><th>비싸게 받은 조합</th></tr>'
    for f in WPN['fish'][:n]:
        hi = sorted([x for x in f['by'] if x[1]], key=lambda x: -x[1])[:3]
        chg = f.get('chg')
        b += f'<tr><td>{E(f["name"])}</td><td class="num">{format(f["wonkg"], ",") if f["wonkg"] else "–"}</td>' + (f'<td class="num {"bad" if (chg or 0) < 0 else "ok" if (chg or 0) > 0 else ""}">{("+" if (chg or 0) > 0 else "") + str(chg) + "%" if chg is not None else "–"}</td>' if WPN.get('prev_month') else '') + f'<td class="num">{man(f["amt"])}원</td><td class="mini">{E(" · ".join(x[0].replace("수산업협동조합", "수협") + " " + format(x[1], ",") for x in hi))}</td></tr>'
    b += '</table>'
    if WPN.get('farm'): b += '<p class="mini">양식 업종으로 위판된 어종(금액 순): ' + E(', '.join(f'{k} {man(v)}원' for k, v in WPN['farm'][:8])) + '</p>'
    return b

def seastock_html():
    if not SSTK.get('center') and not SSTK.get('coop'): return ''
    b = f'<h2>수산 재고 — {E(SSTK["month"].replace("-", "년 "))}월 초 대비 말</h2><p class="mini">창고에 쌓이는 재고가 늘면 값 내림 압력, 줄면 오름 압력. 해양수산부 수협 물류센터·공판장 재고(㎏)와 조합창고 재고(수량).</p><div class="grid2">'
    for k, t, u in (('center', '수협 물류센터·공판장', '㎏'), ('coop', '조합 창고', '수량')):
        x = SSTK.get(k)
        if not x: continue
        b += f'<div><h3>{t}</h3><table class="t"><tr><th>품목</th><th class="num">달 말({u})</th><th class="num">달 초 대비</th></tr>' + ''.join(
            f'<tr><td>{E(i[0])}</td><td class="num">{man(i[2])}</td><td class="num {"bad" if (i[3] or 0) > 15 else "ok" if (i[3] or 0) < -15 else ""}">{("+" if (i[3] or 0) > 0 else "") + str(i[3]) + "%" if i[3] is not None else "새로"}</td></tr>' for i in x['items'][:12]) + '</table></div>'
    return b + '</div>'

def price_page():
    ek = PRICE.get('ekape'); at = PRICE.get('at') or ''
    b = '<p class="crumb"><a href="/">박씨팜</a> › 경락가</p><h1 class="title">경락가 조회</h1><p class="lead">소·돼지는 축산물품질평가원 등급별 경락가, 농산물은 공영도매시장 경락가, 수산물은 수협 위판 시세. 연동창구가 붙는 순서대로 이 화면에 들어옵니다.</p>'
    b += '<div class="statusbar">' + ''.join(f'<span class="{c}"><i></i>{E(t)}</span>' for t, c in [('축산물품질평가원 등급별 경락가', 'on' if ek else 'soon'), ('공판장별 실시간 경매', 'soon'), ('농산물 도매시장 경락가', 'on' if WH.get('items') else 'soon'), ('수협 위판 시세' + (' ' + WPN['month'] if WPN.get('fish') else ''), 'on' if WPN.get('fish') else 'soon')]) + '</div>'
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
    abc = J('price/abattoir.json', {})
    if abc.get('cattle'):
        gs = ['1++', '1+', '1', '2', '3', '평균']
        b += f'<h2>공판장별 경매 — 한우 거세 {E(abc.get("date", ""))}</h2><p class="mini">축산물품질평가원 등급판정정보의 공판장 항목 · 원/㎏ · 그날 경매가 있었던 공판장만 · 돼지는 아직 전국 평균만 들어옵니다.</p>'
        b += '<table class="t"><tr><th>공판장</th>' + ''.join(f'<th class="num">{E(g)}</th>' for g in gs) + '</tr>' + ''.join(
            f'<tr><td>{E(k)}</td>' + ''.join(f'<td class="num">{format(v[g], ",") if v.get(g) else "–"}</td>' for g in gs) + '</tr>'
            for k, v in sorted(abc['cattle'].items(), key=lambda kv: -(kv[1].get('평균') or 0))) + '</table>'
    else:
        b += '<h2>공판장별 경매</h2><p>전국 축산물 공판장 13곳의 당일 경매는 축산물품질평가원 실시간 경매 창구(소·돼지, 등급별)로 받습니다. 열쇠가 연결되면 공판장을 고를 수 있는 표가 이 자리에 들어오고, 지도의 공판장 핀에서도 바로 보입니다.</p>'
        b += '<table class="t"><tr><th>공판장</th><th>지역</th><th>연결</th></tr>' + ''.join(f'<tr><td>{E(m["name"])}</td><td>{E(m["sido"] + " " + m["sigun"])}</td><td class="wait">연동 전</td></tr>' for m in MK['items'] if m['type'] == '공판장') + '</table>'
    if WH.get('items'):
        b += f'<h2>공영도매시장 경락가 — {E(WH.get("date", ""))}</h2><p class="mini">한국농수산식품유통공사 정산정보 · 거래 금액 큰 품목 순 · ㎏ 단위 거래만 ㎏당 값 계산</p><table class="t"><tr><th>품목</th><th>갈래</th><th class="num">원/㎏</th><th class="num">거래 금액</th><th>비싸게 받은 도매시장</th></tr>'
        for it in WH['items'][:40]:
            top = [m for m in it['markets'] if m[1]][:3]
            b += f'<tr><td>{E(it["item"])}</td><td>{E(it["grp"])}</td><td class="num">{format(it["won_kg"], ",") if it["won_kg"] else "–"}</td><td class="num">{man(it["amt"])}원</td><td class="mini">{E(" · ".join(f"{m[0]} {m[1]:,}" for m in sorted(top, key=lambda x: -x[1])))}</td></tr>'
        b += '</table>'
    if WH.get('items'):
        b += '<p>지도의 <a href="/map/?mode=crop">농장 보기</a>에서 시군의 품목을 고르면 같은 정산 자료의 ㎏당 값이, 도매시장 핀을 누르면 그 시장의 품목별 값이 함께 보입니다.</p>'
    else:
        b += '<h2>농산물 도매시장 경락가</h2><p>공영도매시장 32곳의 품목·등급별 경락가는 농림축산식품부 도매시장 통합 창구(농넷)로 받습니다. 지도의 <a href="/map/?mode=crop">농장 보기</a>에서 시군을 누르면 그 지역 대표 품목의 경락가가 함께 보이도록 준비하고 있습니다.</p>'
    b += wipan_html(30) + '<p><a href="/map/?mode=sea&m=w">지도에서 시군별 위판 금액 보기 →</a></p>' + seastock_html() if WPN.get('fish') else '<h2>수산물 위판 시세</h2><p>수협 위판장 63곳의 품종별 위판 시세는 해양수산부 위탁판매 현황 파일로 받습니다. 지도의 <a href="/map/?mode=sea">어장 보기</a>에서 위판장을 누르면 보이게 됩니다.</p>'
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
    b += '<h2>자료 출처</h2><ul><li>축산물품질평가원 등급판정정보 — 등급별 경락가·공판장 실시간 경매(공공데이터포털, 하루 1,000건 한도)</li><li>농림축산식품부 도매시장 통합 창구(농넷) — 공영도매시장 경락가</li><li>해양수산부 일자별 위탁판매 현황(수협 산지 위판, 공공데이터포털 파일데이터, 달마다)</li></ul>'
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
    b += '<div class="statusbar">' + ''.join(f'<span class="{c}"><i></i>{E(t)}</span>' for t, c in [('경락가 ' + ('연동' if ek else '연동 전'), 'on' if ek else 'soon'), ('수입 단가 ' + ('연동' if tr else '연동 전'), 'on' if tr else 'soon'), (('위판 시세 ' + WPN['month']) if WPN.get('fish') else '위판 시세 연동 전', 'on' if WPN.get('fish') else 'soon'), ('이상 신호 ' + (f'{len(sig)}건' if sig else '없음'), 'off' if sig else 'on')]) + '</div>'
    b += wipan_html(15) + seastock_html()
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
    if WH.get('items'):
        b += '<h2>공영도매시장 상위 품목</h2><table class="t"><tr><th>품목</th><th class="num">원/㎏</th><th class="num">거래 금액</th></tr>' + ''.join(f'<tr><td>{E(it["item"])}</td><td class="num">{format(it["won_kg"], ",") if it["won_kg"] else "–"}</td><td class="num">{man(it["amt"])}원</td></tr>' for it in WH['items'][:15]) + '</table>'
    b += '<h2>수입 단가(관세청, 달러/㎏)</h2>'
    if tr: b += '<table class="t"><tr><th>품목</th><th class="num">최근 달 단가</th><th class="num">수입량(톤)</th><th>비교</th></tr>' + ''.join(f'<tr><td>{E(it["name"])}</td><td class="num">{(it["rows"][-1]["usd_kg"] if it["rows"] else "–")}</td><td class="num">{(format(it["rows"][-1]["wgt_t"], ",") if it["rows"] else "–")}</td><td>{E(it["cmp"])}</td></tr>' for it in tr) + '</table>'
    else: b += '<p>쇠고기·돼지고기·옥수수·대두박·어분·전복·김·넙치·새우. 열쇠가 붙으면 매달 3일 갱신.</p>'
    km = EXTRA['kamis'].get('rows') or []
    b += '<h2>소매·도매 가격(축산·수산, 농산물유통정보)</h2>'
    if km:
        b += '<table class="t"><tr><th>구분</th><th>품목</th><th>단위</th><th class="num">어제</th><th class="num">1주 전</th><th class="num">1년 전</th></tr>' + ''.join(f'<tr><td>{E(r["구분"])}</td><td>{E(r["품목"])} {E(r.get("품종") or "")} {E(r.get("등급") or "")}</td><td>{E(r.get("단위") or "")}</td><td class="num">{E(r.get("당일") or "–")}</td><td class="num">{E(r.get("1주전") or "–")}</td><td class="num">{E(r.get("1년전") or "–")}</td></tr>' for r in km[:40]) + '</table>'
    else: b += '<p>산지 경락가와 소비자 가격의 차이(유통 마진)를 보는 칸입니다. 농산물유통정보 열쇠가 붙으면 축산·수산 부류 소매·도매 가격이 매일 들어옵니다.</p>'
    fx = EXTRA['fx']; oil = EXTRA['oil']
    if fx.get('원/달러') or oil.get('today'):
        b += '<h2>원가 바탕 — 환율·기름값</h2><dl class="kv">'
        if fx.get('원/달러'): b += f'<dt>원/달러</dt><dd>{fx["원/달러"][-1][1]:,.1f} ({E(fx["원/달러"][-1][0])})</dd>'
        if fx.get('원/100엔'): b += f'<dt>원/100엔</dt><dd>{fx["원/100엔"][-1][1]:,.1f}</dd>'
        for o in oil.get('today') or []:
            if any(k in (o.get('유종') or '') for k in ('경유', '등유')): b += f'<dt>{E(o["유종"])}</dt><dd>{E(o["값"])}원/ℓ (전일 {E(o.get("전일대비"))})</dd>'
        b += '</dl><p class="mini">수입 사료 원료·수입 축수산물 원가는 환율로, 어선·하우스·축사 난방 원가는 경유·등유 값으로 움직입니다.</p>'
    b += '<h2>구입가 중위값(제보 5건 이상)</h2>'
    if buy: b += '<table class="t"><tr><th>품목</th><th>지역</th><th class="num">중위 단가</th><th class="num">제보</th></tr>' + ''.join(f'<tr><td>{E(it["kind"])} · {E(it["item"])}</td><td>{E(it["area"])}</td><td class="num">{it["median"]:,}원/{E(it["unit"])}</td><td class="num">{it["n"]}</td></tr>' for it in buy[:12]) + '</table>'
    else: b += '<p>아직 공개할 만큼 모이지 않았습니다. <a href="/buy/">구입가 시세판</a>에 제보가 쌓이면 품목·시군별 중위값이 여기 실립니다.</p>'
    b += '<h2>오늘의 이상 신호</h2>'
    if sig: b += '<ul>' + ''.join(f'<li><b>{E(i["level"])} · {E(i["kind"])}</b> {E(i["title"])} — {E(i["body"])}</li>' for i in sig) + '</ul>'
    else: b += '<p>잡힌 신호가 없습니다(고수온·저수온, 경락가 급등락, 가축전염병).</p>'
    b += '<h2>시험 발송 신청(업체·기관)</h2><p>아침마다 이 한 장을 전자우편으로 받습니다. 시험 기간은 무료이며, 유료 전환 전에 미리 안내드립니다. 농가는 신청 없이 이 화면을 그냥 보시면 됩니다.</p>'
    b += form('sheet-sub', [('row', [('sel', '업종', '업종', True, ['사료 공장·대리점', '도축·가공', '유통·급식', '수산 가공·유통', '보험·금융', '지자체·협회·연구', '언론', '기타']), ('text', '상호', '상호·기관명', True, '')]), ('row', [('text', '전자우편', '받을 전자우편', True, ''), ('text', '관심품목', '관심 품목(선택)', False, '예: 한우, 돼지, 전복')]), ('tel', '연락처', '연락처(선택)', False)], '시험 발송 신청', '/sheet/thanks/')
    b += '<p class="mini">출처: 축산물품질평가원 등급판정정보 · 관세청 수출입실적 · 해양수산부 위탁판매 현황(수협 위판) · 국립해양조사원 실측 수온(해루낚 보관) · 박씨팜 구입가 제보. 숫자가 없는 칸은 연동 전입니다.</p>'
    write('/sheet/', shell('/sheet/', f'산지 시세 한 장 — {d} | 박씨팜', '소·돼지 등급별·공판장별 경락가, 돈육 대표가격, 수입 단가, 구입가 중위값, 오늘의 이상 신호를 아침마다 한 장으로. 업체·기관 시험 발송 신청.', b, '/og/price.png'), '0.8')
    write('/sheet/thanks/', shell('/sheet/thanks/', '신청되었습니다 | 박씨팜', '시세 한 장 시험 발송 신청 접수', '<h1 class="title">신청되었습니다</h1><p class="lead">다음 거래일 아침부터 보내 드립니다. <a href="/sheet/">시세 한 장으로</a></p>', noindex=True))


# ── 두당·칸당 수익 계산기(내 수익은 얼마) — 입력은 이 기기에만 저장, 경락가는 최신값 자동
def calc_page():
    b = '<p class="crumb"><a href="/">박씨팜</a> › 수익 계산기</p><h1 class="title">내 수익은 얼마 — 두당 수익 계산기</h1><p class="lead">내 숫자를 넣으면 한 마리(한 칸)당 남는 돈이 바로 나옵니다. 경락가는 최신 공판장 값을 자동으로 넣고, 공판장별 값으로 바꿔 「어디로 실으면 두당 얼마 더」도 봅니다. 넣은 숫자는 이 기기에만 남고 박씨팜으로 보내지지 않습니다.</p>'
    b += '<div class="note">기본값은 화면 확인용 <span class="tag">예시 숫자</span>입니다. 내 농장 숫자로 바꿔 쓰세요.</div>'
    b += '<div class="toc" id="ctab"><a href="#" data-t="hanwoo">한우 비육</a><a href="#" data-t="pig">돼지 비육</a><a href="#" data-t="sea">양식(칸당)</a></div>'
    b += '<div class="grid2"><form class="form calc" id="cform" onsubmit="return false"></form><div><div class="card on" id="cout"></div><div class="card" id="cab" style="margin-top:12px"></div></div></div>'
    b += '<h2>계산 방식</h2><ul><li>한우: 도체중 = 출하 체중 × 도체율, 판매액 = 도체중 × 경락가(원/㎏). 비용 = 송아지값 + 월 사료비 × 사육 개월 + 기타(약품·전기·출하비).</li><li>돼지: 두당 판매액 = 지육(㎏) × 탕박 경락가. 사료비 = (출하 체중 − 입식 체중) × 사료 요구율 × 사료 단가.</li><li>양식: 칸(줄·틀)당 수확량 × 위판 단가 − 종묘·사료·인건·시설 상각.</li><li>공판장별 차이는 축산물품질평가원 등급별 경락가의 공판장 항목을 씁니다(열쇠 연결 뒤).</li></ul>'
    b += '<p><a href="/buy/">내 사료·종묘 구입가를 제보하면 우리 시군 중위값과 비교한 성적표를 받습니다 →</a></p>'
    js = """<script>(function(){var P=%s;var M={
hanwoo:{t:'한우 거세 비육',f:[['calf','송아지 구입가(원/두)',3500000],['months','사육 개월',22],['feed','월 사료비(원/두)',240000],['etc','기타 비용(원/두)',600000],['wt','출하 체중(㎏)',780],['yield','도체율(%%)',59],['price','경락가(원/㎏, 1+ 기준)',21040]],k:'한우 거세',g:'1+'},
pig:{t:'돼지 비육(두당)',f:[['piglet','자돈 구입가 또는 생산비(원/두)',120000],['inw','입식 체중(㎏)',30],['outw','출하 체중(㎏)',116],['fcr','사료 요구율',2.9],['feedp','사료 단가(원/㎏)',620],['etc','기타 비용(원/두)',45000],['carc','지육(㎏)',88],['price','탕박 경락가(원/㎏)',5610]],k:'돼지 탕박',g:'1'},
sea:{t:'양식(한 칸·한 줄당)',f:[['harv','수확량(㎏/칸)',350],['unit','위판 단가(원/㎏)',32000],['seed','종묘비(원/칸)',2400000],['feed','사료·먹이비(원/칸)',3200000],['labor','인건비(원/칸)',1500000],['facil','시설 상각(원/칸/년)',800000],['etc','기타(원/칸)',400000]]}};
var T='hanwoo',PR=null,AB=null,WP=null,ST={};try{ST=JSON.parse(localStorage.getItem('bk_calc')||'{}')}catch(e){}
function v(k){var e=document.getElementById('c_'+k);return e?parseFloat(e.value)||0:0}function won(n){return Math.round(n).toLocaleString('ko-KR')+'원'}
function draw(){var m=M[T];var h='<h3 style="margin-top:0">'+m.t+'</h3>';m.f.forEach(function(x){var val=(ST[T]&&ST[T][x[0]]!=null)?ST[T][x[0]]:x[2];if(x[0]==='price'&&PR&&!(ST[T]&&ST[T].price!=null)){var sec=(PR.ekape||[]).filter(function(s){return s.title===m.k})[0];if(sec){var r=sec.rows.filter(function(r){return r.g===m.g})[0];if(r)val=r.p}}h+='<label>'+x[1]+'<input type="number" step="any" id="c_'+x[0]+'" value="'+val+'"></label>'});h+='<button type="button" class="btn" id="creset">예시 값으로 되돌리기</button>';document.getElementById('cform').innerHTML=h;document.querySelectorAll('#cform input').forEach(function(i){i.addEventListener('input',calc)});document.getElementById('creset').onclick=function(){delete ST[T];save();draw()};
document.querySelectorAll('#ctab a').forEach(function(a){a.style.background=a.getAttribute('data-t')===T?'var(--moss-soft)':''});calc()}
function save(){try{localStorage.setItem('bk_calc',JSON.stringify(ST))}catch(e){}}
function calc(){var m=M[T];ST[T]={};m.f.forEach(function(x){ST[T][x[0]]=v(x[0])});save();var rev,cost,unit='두',rows=[];
if(T==='hanwoo'){var carc=v('wt')*v('yield')/100;rev=carc*v('price');cost=v('calf')+v('feed')*v('months')+v('etc');rows=[['도체중',Math.round(carc)+'㎏'],['판매액',won(rev)],['비용',won(cost)],['월당 남는 돈',won((rev-cost)/Math.max(1,v('months')))]]}
else if(T==='pig'){var feedc=(v('outw')-v('inw'))*v('fcr')*v('feedp');rev=v('carc')*v('price');cost=v('piglet')+feedc+v('etc');rows=[['사료비',won(feedc)],['판매액',won(rev)],['비용',won(cost)],['100두 출하 시',won((rev-cost)*100)]]}
else{unit='칸';rev=v('harv')*v('unit');cost=v('seed')+v('feed')+v('labor')+v('facil')+v('etc');rows=[['판매액',won(rev)],['비용',won(cost)],['손익분기 단가',won(cost/Math.max(1,v('harv')))+'/㎏']]}
var pf=rev-cost;document.getElementById('cout').innerHTML='<h3>'+unit+'당 남는 돈</h3><div class="big" style="color:'+(pf>=0?'var(--moss)':'var(--brick)')+'">'+won(pf)+'</div><p>이익률 '+(rev?Math.round(pf/rev*1000)/10:0)+'%%</p><dl class="kv">'+rows.map(function(r){return '<dt>'+r[0]+'</dt><dd>'+r[1]+'</dd>'}).join('')+'</dl>';
var ab=document.getElementById('cab');if(T==='sea'){if(!WP){ab.innerHTML='<h3>조합별 비교</h3><p>수협 위판 시세가 들어오면 같은 어종의 조합별 ㎏당 값으로 「어느 조합에 내면 칸당 얼마 더」를 보여 드립니다.</p>';return}
var sel=ST.seaFish||WP.fish[0].name;var f=WP.fish.filter(function(x){return x.name===sel})[0]||WP.fish[0];
var h='<h3>조합별로 내면</h3><label>어종(상태)<select id="c_fish">'+WP.fish.slice(0,60).map(function(x){return '<option'+(x.name===f.name?' selected':'')+'>'+x.name+'</option>'}).join('')+'</select></label><button type="button" class="btn" id="c_usewp">전국 ㎏당 값('+(f.wonkg||0).toLocaleString('ko-KR')+'원)을 위판 단가에 넣기</button>';
h+='<table class="t"><tr><th>조합</th><th class="num">원/㎏</th><th class="num">칸당 차이</th></tr>'+f.by.filter(function(b){return b[1]}).sort(function(a,b){return b[1]-a[1]}).map(function(b){return '<tr><td>'+b[0].replace('수산업협동조합','수협')+'</td><td class="num">'+b[1].toLocaleString('ko-KR')+'</td><td class="num">'+won((b[1]-v('unit'))*v('harv'))+'</td></tr>'}).join('')+'</table><p class="mini">'+WP.month+' 수협 산지 위판(해양수산부 위탁판매 현황). 위판 수수료·운송비 별도.</p>';
ab.innerHTML=h;document.getElementById('c_fish').onchange=function(e){ST.seaFish=e.target.value;save();calc()};document.getElementById('c_usewp').onclick=function(){document.getElementById('c_unit').value=f.wonkg;calc()};return}
var g=AB&&AB.cattle?AB.cattle:null;if(T==='hanwoo'&&g){var list=Object.keys(g).map(function(k){return [k,g[k]['1+']||g[k]['1']||0]}).filter(function(x){return x[1]}).sort(function(a,b){return b[1]-a[1]});var carc2=v('wt')*v('yield')/100;ab.innerHTML='<h3>공판장별로 실으면(1+ 기준)</h3><table class="t"><tr><th>공판장</th><th class="num">원/㎏</th><th class="num">두당 차이</th></tr>'+list.map(function(x){return '<tr><td>'+x[0]+'</td><td class="num">'+x[1].toLocaleString('ko-KR')+'</td><td class="num">'+won((x[1]-v('price'))*carc2)+'</td></tr>'}).join('')+'</table><p class="mini">운송비를 빼고 비교하세요. '+AB.date+' 축산물품질평가원.</p>'}
else ab.innerHTML='<h3>공판장별로 실으면</h3><p>공판장별 경락가가 연결되면 「어느 공판장이 두당 얼마 더」를 이 자리에 순위로 보여 드립니다(같은 날·같은 등급 기준, 운송비 별도).</p>'}
document.querySelectorAll('#ctab a').forEach(function(a){a.addEventListener('click',function(e){e.preventDefault();T=a.getAttribute('data-t');draw()})});
Promise.all([fetch(P+'/data/price/latest.json').then(function(r){return r.ok?r.json():null}).catch(function(){return null}),fetch(P+'/data/price/abattoir.json').then(function(r){return r.ok?r.json():null}).catch(function(){return null}),fetch(P+'/data/wipan.json').then(function(r){return r.ok?r.json():null}).catch(function(){return null})]).then(function(r){PR=r[0]&&r[0].ekape?r[0]:null;AB=r[1]&&r[1].cattle?r[1]:null;WP=r[2]&&r[2].fish?r[2]:null;var q=new URLSearchParams(location.search);if(M[q.get('t')])T=q.get('t');draw()})})();</script>"""
    write('/calc/', shell('/calc/', '두당 수익 계산기 — 한우·돼지·양식, 공판장별 두당 차이 | 박씨팜', '한우 비육·돼지 비육·양식 칸당 수익을 내 숫자로 계산. 최신 경락가 자동 입력, 공판장별로 실으면 두당 얼마 더 받는지 비교.', b, '/og/price.png').replace('<footer class="foot">', js % (json.dumps(PREFIX),) + '<footer class="foot">'), '0.8')

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
    b = '<p class="crumb"><a href="/">박씨팜</a> › 소개</p><h1 class="title">박씨팜은 무엇을 하나</h1><p class="lead">박씨팜은 <b>농축수산물 가격 예보처</b>입니다. 날씨 예보처럼, 한우·돼지·수산물·농산물 값이 앞으로 오를지 내릴지를 매일 아침 근거와 함께 알려 드립니다.</p><h2>예보의 원칙</h2><ul><li><b>근거를 적습니다</b> — 창고 재고, 반입 물량, 값의 흐름, 해외 선물·환율, 수온·더위 위험처럼 무엇 때문에 그렇게 보는지 품목마다 적습니다.</li><li><b>채점해서 공개합니다</b> — 지난 예보는 실제 값이 나오면 자동으로 맞혔는지 채점하고, 틀린 것까지 그대로 보여 드립니다. 적중 기록이 곧 예보의 신용입니다.</li><li><b>사고팔지 않습니다</b> — 박씨팜은 거래·중개·재고를 하지 않습니다. 그래서 「이 숫자에 우리 이해관계가 없다」고 말할 수 있습니다.</li><li><b>공개 자료만 씁니다</b> — 축산물품질평가원, 수협 위판, 공영도매시장 정산, 관측 기관 전망, 해외 선물 시세 같은 공개 자료를 매일 자동으로 모읍니다.</li></ul><h2>누구를 위한 예보인가</h2><ul><li>유통·가공·급식 업체: 미리 사 둘 품목과 구매를 미룰 품목</li><li>농가·어가: 출하를 서두를지 늦출지, 사료를 미리 살지</li><li>지자체·기관: 수급 위험과 가격 파동 조기 경보</li></ul><p>예보의 바탕이 되는 시군별 사육·양식·대표 품목은 <a href="/map/">지도</a>에서 볼 수 있습니다.</p>'
    b += '<h2>자료 출처와 갱신</h2><table class="t"><tr><th>보기</th><th>자료</th><th>단위</th><th>갱신</th></tr>'
    b += '<tr><td>동물농장</td><td>가축위생방역지원본부 「전국 시군별 사육규모 현황」 35개 축종 (공공데이터포털, 공공누리 제1유형)</td><td>시군 · 2018~2026년 1월</td><td>해마다</td></tr>'
    b += '<tr><td>어장</td><td>국립해양조사원 어장정보도 2025 (개방해) — 양식·마을어업·정치망 면허 구역 11,486곳</td><td>구역 · 시군 집계</td><td>해마다</td></tr>'
    b += '<tr><td>농장</td><td>지리적표시 등록부 (국립농산물품질관리원·산림청·국립수산물품질관리원) 204건</td><td>시군</td><td>등록 때마다</td></tr>'
    b += '<tr><td>경계</td><td>통계청 통계지리정보서비스 시군 경계(2018), 광역시는 구·군 합침</td><td>161개 시군</td><td>–</td></tr>'
    b += '<tr><td>어장 시세</td><td>해양수산부 일자별 위탁판매 현황 — 전국 수협 산지 위판 낙찰(조합·어종·상태·업종별 금액과 중량), 수협 물류센터·조합창고 재고 (공공데이터포털 파일데이터)</td><td>조합 · 어종</td><td>달마다</td></tr>'
    b += '<tr><td>시장</td><td>축산물 공판장 13곳·가축시장 9곳(박씨팜 정리), 수협 위판장 63곳(지구별 조합), 공영도매시장 32곳</td><td>핀</td><td>확인 때마다</td></tr></table>'
    b += f'<p>그 밖에 가축·어장·농장·유통에 닿는 공공 연동창구 {len(APIS.get("items", {})):,}건을 매일 부릅니다. 목록과 상태는 <a href="/data/">자료 대장</a>에 있습니다.</p>'
    b += '<h2>지키는 것</h2><ul><li>개별 농가·어가의 위치와 이름은 싣지 않습니다. 가장 작은 단위는 리·읍면동입니다.</li><li>예시 숫자는 「예시」라고 씁니다. 확인 전 위치는 「위치 근사」로 표시합니다.</li><li>공공 자료의 출처를 밝히고, 이용 조건을 지킵니다.</li></ul>'
    b += '<h2>해외에서 배운 것</h2><p>시세만 판 미국 어너 배리는 1858년부터 살아 있고, 생산자가 만든 캐틀팩스는 1968년부터, 수매업체가 농가에게 앱을 주는 부셸은 북미 1,200곳에서 쓰입니다. 반대로 거래·재고·물류까지 떠안은 곳(독일 아그란도, 캐나다 파머스 엣지, 인도네시아 이피셔리)은 몇 해 안에 무너졌습니다. 박씨팜은 앞쪽을 따릅니다 — 숫자만 다루고, 돈은 농가가 아니라 업체·기관이 냅니다.</p>'
    b += '<h2>앞으로</h2><ul><li>축산물품질평가원 경락가·실시간 경매, 농산물 도매시장 경락가 연동(수협 위판 시세는 연동 완료)</li><li>지방행정 인허가(가축사육업·도축장·사료 공장) 리 단위 집계</li><li>도매시장·산지공판장 경락 원자료(산지 항목)로 시군별 실제 출하 품목·금액 순위 — 등록 수가 아닌 「팔린 돈」 기준</li><li>관세청 수출입실적으로 수입 단가 비교</li><li>카카오 바탕지도(확대 단계)</li></ul>'
    b += '<h2>연락</h2><p>자료 오류, 위치 정정, 제휴는 <a href="/pro/">업체 등록</a> 양식이나 <a href="/gongu/">모집판</a>의 양식으로 남겨 주세요.</p>'
    write('/about/', shell('/about/', '소개 — 자료 출처·갱신·원칙 | 박씨팜', '박씨팜이 쓰는 자료와 출처, 갱신 주기, 개별 농가 비공개 원칙.', b), '0.5')

# ── 수급 위험 예보 — 7일 수온·기온 예보 × 품종 한계 × 사육·면허 규모 × 위판 값
LVC = {'위험': 'bad', '경고': 'bad', '주의': 'wait', '': ''}
def sst_cell(v):
    if v is None: return '<td class="num">–</td>'
    c = 'background:#f6d5cf' if v >= 28 else 'background:#fbe7c6' if v >= 25 else 'background:#d9e8f3' if v <= 4 else ''
    return f'<td class="num" style="{c}">{v}</td>'
def risk_page():
    R = RISK
    b = '<p class="crumb"><a href="/">박씨팜</a> › 수급 위험 예보</p><h1 class="title">수급 위험 예보 <small class="mini">' + E(R.get('at', '')) + ' 기준</small></h1>'
    b += '<p class="lead">앞으로 7일 바다 수온과 기온·습도 예보를 품종별 한계 수온, 가축 더위지수와 맞춰 「어디서, 무엇이, 언제부터」 위험한지 매깁니다. 폐사가 나면 공급과 값이 움직이므로, 지금 위판 값과 재고를 함께 붙였습니다. 양식장·축산 농가는 대비를, 유통·가공·보험·사료 업체는 물량과 값 변동에 대비하는 데 씁니다.</p>'
    if not R.get('sea') and not R.get('land'):
        b += '<p>첫 예보를 받는 중입니다. 매일 아침 작업에서 갱신됩니다.</p>'
    else:
        sm = R.get('summary', {})
        b += '<div class="statusbar">' + ''.join(f'<span class="{c}"><i></i>{E(t)}</span>' for t, c in [(f'양식 위험 해역 {sm.get("sea_units", 0)}곳', 'off' if sm.get('sea_units') else 'on'), (f'그중 폐사 위험 {sm.get("sea_danger", 0)}곳', 'off' if sm.get('sea_danger') else 'on'), (f'가축 더위·추위 주의 이상 {sm.get("land_units", 0)}곳', 'soon' if sm.get('land_units') else 'on'), (f'경고 이상 {sm.get("land_danger", 0)}곳', 'off' if sm.get('land_danger') else 'on')]) + '</div>'
        sp = R.get('species') or []
        b += '<h2>품종별 — 폐사 위험과 값 움직임</h2>'
        if sp:
            b += '<table class="t"><tr><th>품종</th><th>단계</th><th>위험 해역</th><th class="num">노출 면허 면적</th><th class="num">지금 위판 값</th><th>값에 미칠 영향</th></tr>'
            for x in sp:
                pr = x.get('price')
                eff = '폐사 전 몰아 출하로 며칠 값 내림 → 물량이 줄면 몇 주 뒤 산지 값 오름 압력' if x['lv'] == '위험' else '출하 앞당김 가능성, 값 흔들림 지켜볼 것'
                b += f'<tr><td>{E(x["sp"])}</td><td class="{LVC[x["lv"]]}">{E(x["lv"])}</td><td class="mini">{E(", ".join(uname(u) for u in x["units"][:8]))}{" 외" if len(x["units"]) > 8 else ""}</td><td class="num">{man(x["ha"])}㏊</td><td class="num">{(format(pr["wonkg"], ",") + "원/㎏" + (f" ({pr["chg"]:+}%)" if pr.get("chg") is not None else "")) if pr else "–"}</td><td class="mini">{eff}</td></tr>'
            b += '</table>'
        else: b += '<p>앞으로 7일 동안 품종별 한계 수온을 넘는 해역이 없습니다.</p>'
        sea = R.get('sea') or {}
        if sea:
            ks = sorted(sea, key=lambda u: (-{'위험': 3, '경고': 2, '주의': 1, '': 0}[sea[u].get('lv', '')], -(sea[u].get('hi') or 0)))
            days = next(iter(sea.values()))['days']
            b += '<h2>양식 해역별 7일 바다 수온(하루 최고, ℃)</h2><p class="mini">' + E(R.get('official', '')) + '. 노란 칸 25℃ 이상, 붉은 칸 28℃ 이상, 파란 칸 4℃ 이하. 흐린 날짜는 지난 이틀(비교용).</p>'
            b += '<div style="overflow-x:auto"><table class="t"><tr><th>시군</th>' + ''.join(f'<th class="num" style="white-space:nowrap{";color:var(--faint)" if d < TODAY[5:] else ""}">{E(d.replace("-", "."))}</th>' for d in days) + '<th>주된 양식 · 위험</th></tr>'
            for u in ks:
                x = sea[u]; rk = [r for r in x.get('risks', []) if r['lv']]
                b += f'<tr><td><a href="{upath(u)}">{E(ufull(u))}</a></td>' + ''.join(sst_cell(v) for v in x['max']) + f'<td class="mini">{E(", ".join(r["sp"] + "(" + r["lv"] + ")" for r in rk[:4]) or ", ".join(r["sp"] for r in x.get("risks", [])[:3]) or "–")}</td></tr>'
            b += '</table></div>'
        land = R.get('land') or {}
        if land:
            ls = R.get('livestock') or {}
            b += '<h2>가축 — 더위·추위 위험(7일)</h2><p class="mini">가축 더위지수(온습도지수)를 하루 평균으로 셈해 72 이상이 이틀이면 주의, 79 이상이 이틀이면 경고, 한낮 지수가 89를 넘으면 위험. 최저 기온 −10℃ 주의 · −15℃ 경고. 두수는 위험 시군의 사육 두수 합.</p>'
            b += '<table class="t"><tr><th>축종</th><th class="num">주의 시군 두수</th><th class="num">경고</th><th class="num">위험</th></tr>' + ''.join(f'<tr><td>{g}</td><td class="num">{man(v["주의"])}</td><td class="num">{man(v["경고"])}</td><td class="num">{man(v["위험"])}</td></tr>' for g, v in ls.items()) + '</table>'
            hot = sorted([u for u in land if land[u].get('lv')], key=lambda u: -{'위험': 3, '경고': 2, '주의': 1, '': 0}[land[u]['lv']])
            if hot:
                b += '<table class="t"><tr><th>시군</th><th>단계</th><th class="num">더위지수(하루 평균 최고)</th><th class="num">최저 기온</th><th class="num">소</th><th class="num">돼지</th><th class="num">닭</th></tr>' + ''.join(
                    f'<tr><td><a href="{upath(u)}">{E(ufull(u))}</a></td><td class="{LVC[land[u]["lv"]]}">{E(land[u]["kind"])} {E(land[u]["lv"])}</td><td class="num">{land[u].get("thi_mean_max", land[u].get("thi_max"))}</td><td class="num">{land[u].get("tmin_min")}</td><td class="num">{man(land[u]["heads"].get("소", 0))}</td><td class="num">{man(land[u]["heads"].get("돼지", 0))}</td><td class="num">{man(land[u]["heads"].get("닭", 0))}</td></tr>' for u in hot[:40]) + '</table>'
            else: b += '<p>앞으로 7일 동안 가축 더위·추위 주의 단계에 드는 시군이 없습니다.</p>'
        b += seastock_html()
    b += '<h2>어떻게 매기나</h2><ul><li>바다 수온: 오픈메테오 공개 바다 예보(시간별)를 시군별 양식 면허 구역 가운데 지점에서 받아 하루 최고·최저로 묶습니다. 연안 실측(국립해양조사원 조위관측소)은 <a href="/sheet/">시세 한 장</a>의 이상 신호에 따로 씁니다.</li>'
    b += '<li>품종별 한계 수온: 국립수산과학원 고수온·저수온 특보 기준과 품종별 적정 수온 자료를 바탕으로 박씨팜이 정리한 참고값입니다(예: 조피볼락 25℃ 주의·27℃ 위험, 전복 25·27℃, 멍게 24·26℃, 넙치 26·28℃). 위험은 한계 수온을 이틀 이상 넘을 때, 주의는 하루라도 주의 수온에 닿을 때입니다.</li>'
    b += '<li>가축: 시군 중심의 하루 평균 기온·습도로 더위지수를 셈해(한낮 지수는 위험 판정에만) 축종별 사육 두수와 곱해 봅니다.</li>'
    b += '<li>예보는 매일 저장해 두었다가 실제 위판 값·재고·폐사 신고와 맞춰 보며 기준을 고칩니다. 이 기록이 쌓이면 「고수온 며칠 뒤 어느 품종 값이 몇 % 움직였나」를 숫자로 말할 수 있게 됩니다.</li></ul>'
    b += '<h2>업체·기관용</h2><p>보험사(양식·가축 재해보험), 수협·축협, 사료·종묘 업체, 유통·가공 업체에 해역·시군 단위 위험 예보와 값 영향 자료를 아침마다 보내 드립니다. <a href="/pro/">업체 등록 →</a></p>'
    write('/risk/', shell('/risk/', '수급 위험 예보 — 양식 폐사·가축 더위 위험과 값 움직임 7일 | 박씨팜', '7일 바다 수온·기온·습도 예보로 양식 품종별 폐사 위험 해역, 가축 더위·추위 위험 시군과 노출 두수를 매기고 위판 값·수산 재고와 함께 보여 줍니다.', b, '/og/price.png'), '0.8')

# ── 구매 신호(시험판) — 유통·가공·급식 업체용 「사 둘까, 미룰까」

def alert_bar(path=''):
    al = (FC.get('alerts') or [])
    if not al or path == '/signal/': return ''
    n2 = sum(1 for a in al if a['level'] == '경보'); top = al[0]
    cls = 'alarm' if n2 else 'warn'
    return f'<a class="alertbar {cls}" href="/signal/#alerts"><b>{"경보" if n2 else "주의"} {len(al)}건</b> {E(top["title"])} — 사전 대응 보기 →</a>'
def svg_line(pts, w=640, h=170, pad=26, color='var(--moss)'):
    if len(pts) < 2: return ''
    vs = [p[1] for p in pts]; lo, hi = min(vs), max(vs); rng = (hi - lo) or 1
    X = lambda i: pad + (w - 2 * pad) * i / (len(pts) - 1); Y = lambda v: h - pad - (h - 2 * pad) * (v - lo) / rng
    d = 'M' + ' L'.join(f'{X(i):.1f},{Y(v):.1f}' for i, v in enumerate(vs))
    ticks = [0, len(pts) // 2, len(pts) - 1]
    lab = ''.join(f'<text x="{X(i):.0f}" y="{h - 6}" font-size="11" text-anchor="middle" fill="var(--faint)">{pts[i][0][2:7].replace("-", ".")}</text>' for i in ticks)
    yl = f'<text x="4" y="{Y(hi) + 4:.0f}" font-size="11" fill="var(--faint)">{hi:,.0f}</text><text x="4" y="{Y(lo) + 4:.0f}" font-size="11" fill="var(--faint)">{lo:,.0f}</text>'
    return f'<svg viewBox="0 0 {w} {h}" class="chart" role="img" aria-label="추이 그래프"><path d="{d}" fill="none" stroke="{color}" stroke-width="2"/><circle cx="{X(len(vs) - 1):.1f}" cy="{Y(vs[-1]):.1f}" r="3.5" fill="{color}"/>{lab}{yl}</svg>'
def pct_cell(v):
    if v is None: return '<td class="num">–</td>'
    return f'<td class="num {"bad" if v > 0 else "ok" if v < 0 else ""}">{v:+.1f}%</td>'
def forecast_html():
    F = FC
    if not F.get('tiles'): return '<p class="note">해외 선물·환율을 받는 중입니다. 다음 아침 작업부터 예측·경보가 이 자리에 뜹니다.</p>'
    b = ''
    al = F.get('alerts') or []
    b += '<h2 id="alerts">오늘 경보와 사전 대응</h2>'
    if al:
        b += '<table class="t"><tr><th>단계</th><th>무엇이</th><th>미리 할 일</th></tr>' + ''.join(
            f'<tr><td class="{"bad" if a["level"] == "경보" else "wait"}">{E(a["level"])}</td><td>{E(a["title"])}<span class="mini"> {E(a.get("kind", ""))} · {E(a.get("date", ""))}</span></td><td class="mini">{E(a.get("react", ""))}</td></tr>' for a in al) + '</table>'
    else:
        b += '<p class="note">오늘은 기준을 넘은 급변이 없습니다.</p>'
    secs = F.get('sectors') or []
    if secs:
        b += '<h2 id="sectors">농산·축산·수산 — 부문별 압력</h2><p class="mini">원가 쪽(해외 연료·환율·사료 원가, 국내 반영은 몇 주~몇 달 늦음)과 공급 쪽(국내 시세 신호·공식 관측)을 부문마다 나눠 봅니다. 「오름 쪽」은 값이 오를 압력이 크다는 뜻입니다.</p><div class="cards">'
        def dcls(x): return 'bad' if x == '오름 쪽' else 'ok' if x == '내림 쪽' else ''
        for sx in secs:
            c = sx.get('cost') or {}
            li = []
            if c: li.append(f'<li>원가 압력 <b class="{dcls(c.get("dir"))}">{E(c.get("dir", ""))}</b> ({c.get("v", 0):+}%) — {E(" · ".join(c.get("why") or []))}</li>')
            fp = sx.get('feed_pass')
            if fp: li.append(f'<li>배합사료 전가 예상 {fp["exp"]:+}% (원가 지수 최근 3개월 평균 대 4~7개월 전 {fp["gap"]:+}%)</li>')
            for t in sx.get('dom') or []: li.append(f'<li>{E(t)}</li>')
            su = sx.get('supply')
            if su and su.get('n'): li.append(f'<li>국내 시세 신호 {su["n"]}품목 중 오름 쪽 {su["up"]} · 내림 쪽 {su["down"]}</li>')
            for n in sx.get('notes') or []:
                li.append(f'<li><b class="{dcls(n.get("dir"))}">{E(n["item"])} {E(n.get("dir", ""))}</b> — {E(n["text"])} <span class="mini">({E(n["src"])})</span></li>')
            b += f'<div class="card"><h3>{E(sx["sector"])}</h3><ul class="mini">' + ''.join(li) + '</ul>' + (f'<p class="mini">{E(sx["note"])}</p>' if sx.get('note') else '') + '</div>'
        b += '</div>'
        cm = F.get('common') or []
        if cm:
            b += '<p class="mini"><b>공통 요인</b> · ' + ' · '.join(f'{E(n["item"])} {E(n.get("dir", ""))}: {E(n["text"])} ({E(n["src"])})' for n in cm) + '</p>'
        b += '<p class="mini">공식 관측·보도 메모는 확인한 것만 적고, 유효 기한이 지나면 자동으로 빠집니다.</p>'
    b += '<h2 id="decide">선매·매도 판단</h2><div class="cards">'
    for d in F.get('decisions') or []:
        cls = 'bad' if ('선매' in d['act'] or '늦추기 검토(값 오름' in d['act']) else 'ok' if ('늦추기' in d['act'] or '서두르기' in d['act']) else ''
        tr = d.get('track') or d.get('live_track')
        trs = ''
        if d.get('live_track'): t = d['live_track']; trs = f'실제 채점 {t["n"]}건 · 적중 {t["rate"]}% (기준선 {t["base_rate"]}%)'
        elif d['id'] == 'feed': trs = '사료값 실제 채점은 배합사료 가격 자료가 붙으면 시작(지금은 연구 근거의 시차 규칙)'
        else: trs = f'채점 대기 — 판단 기록 후 10거래일 뒤 자동 채점'
        b += (f'<div class="card"><p class="mini">{E(d["who"])} · {E(d["horizon"])}</p><h3>{E(d["item"])}</h3>'
              f'<p class="{cls}" style="font-size:17px">{E(d["act"])}</p><p class="mini">신뢰도 {E(d["conf"])}{" · 참고용(기준선보다 못함)" if d.get("weak") else ""} · 점수 {d["score"]:+}</p>'
              f'<ul class="mini">' + ''.join(f'<li>{E(w)}</li>' for w in d['why']) + f'</ul><p class="mini">{E(trs)}</p></div>')
    b += '</div>'
    fd = (F.get('feed') or {}); st = fd.get('stats') or {}
    if fd.get('d'):
        w = fd.get('w') or {}
        b += f'<h2 id="feed">사료 원가 지수(원/㎏)</h2><p class="mini">시카고 옥수수 {int(w.get("corn", 0) * 100)}% · 대두박 {int(w.get("soymeal", 0) * 100)}% · 소맥 {int(w.get("wheat", 0) * 100)}% 가중 × 원/달러. 국내 배합사료 값은 이 원가를 몇 달 늦게, 덜 따라갑니다(근거: 예측 기법 검토).</p>'
        b += svg_line(fd['d'][-260:])
        b += f'<p class="mini">지금 {st.get("last", 0):,.0f}원/㎏ · 1개월 {st.get("c20") or 0:+}% · 3개월 {st.get("c60") or 0:+}% · 1년 {st.get("c250") or 0:+}% · 1년 범위 중 {st.get("pctl", "–")}% 위치</p>'
        fdec = next((d for d in F.get('decisions', []) if d.get('id') == 'feed'), None)
        if fdec and (fdec.get('expect') or {}).get('note'):
            b += f'<p class="mini">{E(fdec["expect"]["note"])}</p>'
        bt = fd.get('backtest')
        if bt: b += f'<p class="mini">검증: 「{E(bt["rule"])}」 규칙은 지난 3년 {bt["n"]}번 중 {bt["hit"]}번({bt["rate"]}%) 맞아 기준선({bt["base_rate"]}%)과 차이가 없습니다 — 그래서 원가의 앞날을 맞히려 하지 않고, 이미 움직인 원가가 사료값에 늦게 반영되는 시차만 판단에 씁니다.</p>'
    b += '<h2 id="macro">해외 선물·환율·운임</h2><table class="t"><tr><th>지표</th><th class="num">마지막</th><th class="num">1주</th><th class="num">1개월</th><th class="num">3개월</th><th class="num">1년</th><th>흐름</th></tr>'
    for t in F['tiles']:
        b += f'<tr><td>{E(t["name"])}<span class="mini"> {E(t["unit"])}{" · 만기 이월 보정" if t.get("rolls") else ""}</span></td><td class="num">{t["last"]:,}</td>{pct_cell(t.get("c5"))}{pct_cell(t.get("c20"))}{pct_cell(t.get("c60"))}{pct_cell(t.get("c250"))}<td>{E(t["trend"])}</td></tr>'
    b += f'</table><p class="mini">자료: {E(", ".join(sorted(set(t["src"] for t in F["tiles"]))))} 하루 한 번 종가 · 기준 {E(F.get("at", ""))}</p>'
    mi = F.get('micro') or []
    if mi:
        b += '<h2 id="micro">수산·농산 — 사 둘까, 미룰까</h2><table class="t"><tr><th>갈래</th><th>품목</th><th>방향</th><th>근거</th></tr>' + ''.join(
            f'<tr><td>{E(m["kind"])}</td><td>{E(m["item"])}</td><td class="{"bad" if m["dir"] == "오름 쪽" else "ok"}">{E(m["dir"])} · {E(m["act"])}</td><td class="mini">{E(" · ".join(m["why"]))}</td></tr>' for m in mi) + '</table>'
    tk = F.get('micro_track') or {}
    rows = []
    for k, v in (F.get('track') or {}).items(): rows.append((({'feed': '사료 원가', 'hanwoo': '한우 출하', 'pig': '돼지 출하'}).get(k, k), v['n'], f'{v["rate"]}%', f'{v["base_rate"]}%'))
    for k, v in tk.items():
        if v.get('n'): rows.append((k + ' 구매 신호', v['n'], f'{v["rate"]}%', '–'))
    b += '<h2 id="track">적중 기록 — 숨기지 않고 공개</h2>'
    b += ('<table class="t"><tr><th>갈래</th><th class="num">채점</th><th class="num">적중</th><th class="num">기준선(보합)</th></tr>' + ''.join(f'<tr><td>{E(r[0])}</td><td class="num">{r[1]}</td><td class="num">{r[2]}</td><td class="num">{r[3]}</td></tr>' for r in rows) + '</table>') if rows else '<p class="mini">채점이 쌓이는 중입니다.</p>'
    b += '<p class="mini">모든 판단은 그날 기록해 두고 기한(사료 60거래일·출하 10거래일)이 오면 실제 값으로 자동 채점합니다. 기준선은 「값이 그대로」라고 찍었을 때의 적중률입니다. 20건 넘게 채점됐는데 기준선보다 못한 갈래는 「참고용」으로 낮추고, 매주 월요일 가중치를 정해진 범위(0.2~1.0) 안에서 스스로 조정합니다.</p>'
    cal = (F.get('params') or {}).get('calib') or []
    if cal: b += '<p class="mini">최근 자가 조정: ' + E(' / '.join(f'{c["date"]} ' + ', '.join(c['changes']) for c in cal[-3:])) + '</p>'
    return b

def signal_page():
    S = BUYS; it = S.get('items') or []
    b = '<p class="crumb"><a href="/">박씨팜</a> › 예측·경보</p><h1 class="title">시장 예측·경보 — 미리 살까, 서둘러 팔까 <span class="tag">시험판</span></h1>'
    b += '<p class="lead">해외 곡물·축산 선물과 환율(거시)에 국내 경락가·위판·재고·반입량·수온(미시)을 묶어, 사료는 미리 사 둘지, 가축은 출하를 서두를지 늦출지, 원료는 사 둘지 미룰지를 근거·신뢰도와 함께 냅니다. 급변은 경보로 먼저 알리고, 모든 판단은 기록했다가 실제 값으로 채점해 그대로 공개합니다.</p>'
    b += '<p class="toc"><a href="#alerts">경보</a> <a href="#sectors">농산·축산·수산</a> <a href="#decide">선매·매도</a> <a href="#feed">사료 원가</a> <a href="#macro">해외 선물</a> <a href="#micro">수산·농산</a> <a href="#track">적중 기록</a> <a href="#sea">수협 위판 신호</a></p>'
    b += forecast_html()
    b += '<h2 id="sea">수협 위판 — 다음 달 산지 값 방향</h2>'
    if not it:
        b += '<p>첫 신호를 만드는 중입니다.</p>'
    else:
        sc = S.get('score') or {}
        hit = f'{sc["hit"]}/{sc["n"]} ({round(sc["hit"] / sc["n"] * 100)}%)' if sc.get('n') else '채점 대기 — 다음 달 위판 값이 들어오면 첫 채점'
        c = collections.Counter(i['dir'] for i in it)
        b += '<div class="statusbar">' + ''.join(f'<span class="{k}"><i></i>{E(t)}</span>' for t, k in [(f'오를 쪽 {c["오름 쪽"]}', 'off' if c['오름 쪽'] else 'on'), (f'내릴 쪽 {c["내림 쪽"]}', 'soon' if c['내림 쪽'] else 'on'), (f'보합 {c["보합"]}', 'on'), (f'적중 {hit}', 'on' if sc.get('n') else 'soon')]) + '</div>'
        b += f'<p class="mini">기준 자료 달: {E(S["month"].replace("-", "년 "))}월 · 맞히려는 것: {E(S["horizon"])} · 근거: {E(S["basis"])}</p>'
        for d, cls in (('오름 쪽', 'bad'), ('내림 쪽', 'ok')):
            rows = [i for i in it if i['dir'] == d]
            if not rows: continue
            b += f'<h2>{"오를 쪽 — 미리 사 두기 검토" if d == "오름 쪽" else "내릴 쪽 — 구매 미루기 검토"}</h2><table class="t"><tr><th>품목</th><th class="num">지금 ㎏당</th><th class="num">신호 세기</th><th>근거</th></tr>'
            b += ''.join(f'<tr><td>{E(i["item"])}<span class="mini"> {E(", ".join(i["names"][:2]))}</span></td><td class="num">{format(i["wonkg"], ",")}원</td><td class="num {cls}">{i["score"]:+}</td><td class="mini">{E(" · ".join(i["why"]))}</td></tr>' for i in sorted(rows, key=lambda x: -abs(x['score']))) + '</table>'
        rest = [i for i in it if i['dir'] == '보합']
        b += '<h2>보합 — 평소대로</h2><p class="mini">' + E(', '.join(f'{i["item"]} {format(i["wonkg"], ",")}원' for i in rest)) + '</p>'
        if sc.get('months'):
            b += '<h2>적중 기록</h2><table class="t"><tr><th>신호 달 → 채점 달</th><th class="num">품목</th><th class="num">적중</th></tr>' + ''.join(f'<tr><td>{E(m["month"])} → {E(m["to"])}</td><td class="num">{m["n"]}</td><td class="num">{m["hit"]} ({round(m["hit"] / m["n"] * 100)}%)</td></tr>' for m in sc['months']) + '</table>'
        tr = sc.get('trial') or {}
        b += '<p class="mini">' + E(f'새 기준({tr.get("rule", "")}) 시험 채점: ' + (f'{tr["hit"]}/{tr["n"]}' if tr.get('n') else '다음 달 위판 값이 들어오면 첫 채점')) + ' — 이미 공개한 예측은 고치지 않고 따로 채점합니다.</p>' if tr.get('rule') else ''
    C = CROPS
    b += '<h2 id="crop">농산물 — 공영도매시장 값 흐름 <span class="tag">새로</span></h2>'
    if C.get('items'):
        sc2 = C.get('score') or {}
        b += f'<p class="mini">거래일 {C["ndays"]}일치 · 맞히려는 것: {E(C["horizon"])} · 근거: {E(C["basis"])} · 적중 ' + (f'{sc2["hit"]}/{sc2["n"]}' if sc2.get('n') else '채점 대기(월요일 신호를 2주 뒤 자동 채점)') + '</p>'
        for d, cls in (('오름 쪽', 'bad'), ('내림 쪽', 'ok')):
            rows = [i for i in C['items'] if i['dir'] == d]
            if rows: b += f'<h3>{"오를 쪽 — 앞당겨 확보 검토" if d == "오름 쪽" else "내릴 쪽 — 구매 미루기 검토"}</h3><table class="t"><tr><th>품목</th><th class="num">최근 ㎏당</th><th class="num">신호 세기</th><th>근거</th></tr>' + ''.join(f'<tr><td>{E(i["item"])}</td><td class="num">{format(i["wonkg"], ",")}원</td><td class="num {cls}">{i["score"]:+}</td><td class="mini">{E(" · ".join(i["why"]))}</td></tr>' for i in rows) + '</table>'
        rest = [i for i in C['items'] if i['dir'] == '보합']
        if rest: b += '<p class="mini">보합: ' + E(', '.join(f'{i["item"]} {format(i["wonkg"], ",")}원' for i in rest)) + '</p>'
    else:
        b += f'<p>전국 공영도매시장 26곳의 정산 자료를 거래일마다 쌓는 중입니다(지금 {C.get("ndays", 0)}거래일). 10거래일이 모이면 품목별 「앞으로 2주 오를 쪽·내릴 쪽」 신호가 여기에 자동으로 뜹니다. 그 전에도 <a href="/opps/#c1">도매시장 간 값 차이</a>는 지금 바로 볼 수 있습니다.</p>'
    b += '<h2>신호를 만드는 방법</h2><ul><li>농산물: 최근 5거래일 ㎏당 값이 앞 15거래일보다 5% 넘게 오르면 +0.5, 반입 물량이 15% 넘게 줄면 +0.5(반대는 −). 합이 ±1이면 신호.</li><li>창고 재고: 수협 물류센터·조합창고 재고가 한 달 새 15% 넘게 줄면 오를 쪽(+1), 늘면 내릴 쪽(−1).</li><li>달 안 흐름: 달 후반 위판 값이 전반보다 5% 넘게 오르면 +1, 내리면 −1(2026년 10월 26일부터 — 8월 신호 채점에서 이 근거가 26건 중 19건 맞고 창고 재고는 7건 중 2건만 맞아 무게를 0.5에서 올림). 앞달 대비 10% 넘게 움직이면 같은 방향으로 ±0.5.</li><li>폐사 위험 예보: 7일 안에 폐사 위험이면 +1, 고수온 주의면 +0.5(공급이 줄 수 있음).</li><li>합이 +1 이상이면 오를 쪽, −1 이하면 내릴 쪽. 채점은 다음 달 ㎏당 값이 3% 넘게 움직인 방향과 맞는지로 봅니다.</li><li>축산(소·돼지 경락가)도 날짜별 값이 쌓이는 대로 같은 틀로 붙입니다.</li></ul>'
    b += '<p class="mini">이 신호는 공개 자료로 만든 참고 정보이며 거래를 권하는 것이 아닙니다. 박씨팜은 물건을 사고팔지 않습니다.</p>'
    b += '<p><a href="/opps/">싸게 사는 산지 · 넘치는 품목 · 마르는 품목 · 어족 동향 보기 →</a></p>'
    b += '<h2>업체용</h2><p>품목·지역을 골라 매주 받는 구독(급식·식자재 유통·수산 가공·횟집 묶음)과, 우리 회사 구매 품목만 따로 보는 신호표를 준비하고 있습니다. <a href="/pro/">업체 등록에서 「시세 한 장 구독」 →</a></p>'
    write('/signal/', shell('/signal/', '시장 예측·경보 — 사료 선매·출하 매도 판단과 적중 기록 | 박씨팜', '시카고 옥수수·대두박 선물과 환율로 만든 사료 원가 지수, 한우·돼지 출하 판단, 수산·농산 값 방향, 급변 조기 경보와 사전 대응. 모든 판단은 자동 채점해 공개.', b, '/og/price.png'), '0.8')

# ── 수급 기회 — 수요·공급이 어긋나는 곳을 유통업체용 추천으로
def opps_page():
    O = OPPS
    b = '<p class="crumb"><a href="/">박씨팜</a> › 수급 기회</p><h1 class="title">수급 기회 — 어긋난 곳에 장사가 있다 <span class="tag">시험판</span></h1>'
    b += '<p class="lead">같은 어종인데 산지마다 값이 크게 다르거나, 창고에 물량이 쌓이거나, 반대로 물량이 말라 가는 품목을 찾아 유통·가공·급식 업체가 바로 쓸 수 있는 말로 바꿉니다 — 「여기서 사라」, 「지금 싸게 사들여라」, 「이걸로 바꿔라」. 자연산 어획(어족)이 어디서 얼마나 잡히는지도 함께 봅니다.</p>'
    if not O.get('month'):
        b += '<p>첫 자료를 만드는 중입니다.</p>'
    else:
        mo = O['month'].replace('-', '년 ') + '월'
        b += f'<p class="mini">기준: {E(mo)} · {E(O["basis"])} · 크기·선도(상품 규격)가 섞인 평균이므로 실제 매입 전 규격을 맞춰 보세요.</p>'
        b += '<div class="toc"><a href="#c1">농산물 도매시장 간 값 차이</a><a href="#o1">싸게 사는 산지</a><a href="#o2">공급 넘침</a><a href="#o3">공급 빠듯</a><a href="#o4">어족(자연산)</a><a href="#o5">자연산·양식 값 차이</a></div>'
        if CROPS.get('spread'):
            b += f'<h2 id="c1">농산물 — 같은 품목, 도매시장마다 다른 값 <span class="tag">{E(CROPS.get("date") or "")}</span></h2><p class="mini">한국농수산식품유통공사 공영도매시장 정산(㎏ 단위 거래, 거래 금액 5백만 원 넘는 곳만). 등급·크기가 섞인 평균이라 실제 매입 전 규격을 맞춰 보세요.</p>'
            b += '<table class="t"><tr><th>품목</th><th class="num">전국 ㎏당</th><th>싸게 거래된 도매시장(㎏당 · 평균보다)</th><th>비싸게 거래된 곳</th><th class="num">차이</th></tr>' + ''.join(
                f'<tr><td>{E(x["item"])}</td><td class="num">{format(x["avg"], ",")}원</td><td class="mini">{E(" · ".join(f"{m[0]} {m[1]:,}원(−{m[2]}%)" for m in x["cheap"]))}</td><td class="mini">{E(x["high"][0])} {x["high"][1]:,}원</td><td class="num">{x["gap"]}%</td></tr>' for x in CROPS['spread'][:15]) + '</table>'
        b += '<h2 id="o1">1. 싸게 사는 산지 — 같은 어종, 조합마다 다른 값</h2>'
        if O.get('spread'):
            b += '<table class="t"><tr><th>어종</th><th class="num">전국 ㎏당</th><th>싸게 판 조합(㎏당 · 물량 · 평균보다)</th><th>비싸게 판 곳</th><th class="num">차익 크기</th></tr>'
            b += ''.join(f'<tr><td>{E(x["fish"])}</td><td class="num">{format(x["avg"], ",")}</td><td class="mini">{E(" · ".join(f"{c[0]} {c[1]:,}원 {man(c[2])}㎏ −{c[3]}%" for c in x["cheap"]))}</td><td class="mini">{E(x["high"][0])} {x["high"][1]:,}원</td><td class="num">{man(x["save"])}원</td></tr>' for x in O['spread']) + '</table>'
            b += '<p class="mini">차익 크기 = (전국 평균 − 싼 조합 값) × 그 조합 물량. 활어 운송비·선도 차이는 빼지 않았습니다.</p>'
        b += '<h2 id="o2">2. 공급 넘침 — 싸게 사들이거나 판촉할 품목</h2>'
        b += ('<table class="t"><tr><th>품목</th><th class="num">지금 ㎏당</th><th>근거</th><th>할 일</th></tr>' + ''.join(f'<tr><td>{E(x["item"])}<span class="mini"> {E(x["name"])}</span></td><td class="num">{format(x["wonkg"], ",")}</td><td class="mini">{E(" · ".join(x["why"]))}</td><td class="mini">{E(x["act"])}</td></tr>' for x in O['glut']) + '</table>') if O.get('glut') else '<p>이번 달에는 뚜렷한 공급 넘침 품목이 없습니다.</p>'
        b += '<h2 id="o3">3. 공급 빠듯 — 미리 확보하거나 바꿔 쓸 품목</h2>'
        b += ('<table class="t"><tr><th>품목</th><th class="num">지금 ㎏당</th><th>근거</th><th>바꿔 쓸 품목(㎏당)</th></tr>' + ''.join(f'<tr><td>{E(x["item"])}<span class="mini"> {E(x["name"])}</span></td><td class="num">{format(x["wonkg"], ",")}</td><td class="mini">{E(" · ".join(x["why"]))}</td><td class="mini">{E(", ".join(f"{a} {v:,}원" for a, v in x.get("subs", [])) or "–")}</td></tr>' for x in O['tight']) + '</table>') if O.get('tight') else '<p>이번 달에는 뚜렷한 공급 빠듯 품목이 없습니다.</p>'
        b += '<h2 id="o4">4. 어족 — 자연산이 어디서, 무슨 어업으로, 얼마나 잡히나</h2>'
        if O.get('wild'):
            b += '<table class="t"><tr><th>어종</th><th class="num">자연산 위판 물량</th><th class="num">㎏당</th><th>주로 잡히는 곳</th><th>어업 종류</th><th class="num">달 후반 물량</th><th class="num">앞달 대비</th></tr>'
            b += ''.join(f'<tr><td>{E(x["name"])}</td><td class="num">{man(x["kg"])}㎏</td><td class="num">{format(x["wonkg"], ",") if x["wonkg"] else "–"}</td><td class="mini">{E(", ".join(w[0] for w in x["where"]))}</td><td class="mini">{E(", ".join(g[0] for g in x["gear"]))}</td><td class="num">{(f"{x["kg_trend"]:+}%") if x.get("kg_trend") is not None else "–"}</td><td class="num">{(f"{x["wild_chg"]:+}%") if x.get("wild_chg") is not None else "다음 달부터"}</td></tr>' for x in O['wild']) + '</table>'
            b += '<p class="mini">자연산은 위판 업종이 양식이 아닌 줄만 셉니다. 달이 바뀌면 앞달 대비 물량으로 어장 이동·어획 부진(어족 변화)을 바로 잡습니다.</p>'
        if O.get('wildfarm'):
            b += '<h2 id="o5">5. 자연산과 양식 값 차이 — 바꿔 사면 얼마나 싸나</h2><table class="t"><tr><th>어종</th><th class="num">자연산 ㎏당</th><th class="num">양식 ㎏당</th><th class="num">차이</th></tr>' + ''.join(f'<tr><td>{E(x["name"])}</td><td class="num">{x["wild"]:,}</td><td class="num">{x["farm"]:,}</td><td class="num">{x["gap"]:+}%</td></tr>' for x in O['wildfarm']) + '</table>'
    b += '<h2>업체용</h2><p>우리 회사가 사는 품목·지역만 골라 매주 「싸게 사는 산지 · 넘치는 품목 · 마르는 품목」을 받아 보는 구독을 준비하고 있습니다. 박씨팜은 물건을 사고팔거나 거래를 중개하지 않고, 공개 위판 자료를 정리한 정보만 드립니다. <a href="/pro/">업체 등록 →</a> · <a href="/signal/">품목별 값 방향 신호 →</a> · <a href="/risk/">폐사 위험 예보 →</a></p>'
    write('/opps/', shell('/opps/', '수급 기회 — 싸게 사는 산지, 넘치는 품목, 마르는 품목, 어족 동향 | 박씨팜', '같은 어종의 조합별 위판 값 차이, 창고 재고·물량으로 본 공급 넘침과 빠듯, 자연산 어획이 잡히는 곳과 어업 종류, 자연산·양식 값 차이를 유통·가공·급식 업체용 추천으로.', b, '/og/price.png'), '0.8')

# ── 자료 대장(공개) — 박씨팜이 연동하는 공공 자료 전부를 영역·갈래별로
APIS = J('apis.json', {'items': {}})
APISUM = {}
_ad = os.path.join(SITE, 'data', 'api')
if os.path.isdir(_ad):
    for fn in os.listdir(_ad):
        try: APISUM[fn[:-5]] = json.load(open(os.path.join(_ad, fn), encoding='utf-8'))
        except Exception: pass
EXTRA = {k: J('extra/' + k + '.json', {}) for k in ('kamis', 'fx', 'oil', 'kosis_livestock', 'usda_beef')}
STATE_WORD = {'활용신청 필요': ('활용신청 대기', 'soon'), '정상': ('연동 중', 'on'), '빈 응답': ('연동 중(어제 자료 없음)', 'on'), '전용 수집기': ('연동 중', 'on'), '열쇠 대기': ('열쇠 들어오면 바로', 'soon'), '제공처 열쇠': ('제공처 열쇠 필요', 'soon'), '실패': ('점검 중', 'off'), '명세 없음': ('명세 확인 중', 'soon')}
def data_page():
    it = APIS.get('items', {})
    doms = ['동물농장', '어장', '농장', '공통']
    cats = ['시세·거래', '수출입', '질병·이상', '환경·관측', '업체·인허가', '사육·생산', '원가']
    cnt = collections.Counter(STATE_WORD.get(v.get('state'), ('?', ''))[0] for v in it.values())
    b = '<p class="crumb"><a href="/">박씨팜</a> › 자료 대장</p><h1 class="title">자료 대장 — 박씨팜이 연동하는 공공 자료</h1>'
    b += f'<p class="lead">가축·어장·농장과 그 유통에 닿는 공공 연동창구 <b>{len(it):,}건</b>을 모았습니다. 공공데이터포털 낱말 검색 140여 개로 훑고, 관련 없는 것(반려동물·관광·교통 등)을 걸러 낸 목록입니다. 열쇠 없이 바로 받는 파일데이터(수협 위판·수산 재고 등)는 열쇠가 없어도 지금 돌고 있습니다. 매일 아침 자동으로 부르고, 개별 사업장 자료는 시군 집계로만 공개합니다.</p>'
    b += '<div class="statusbar">' + ''.join(f'<span class="{c}"><i></i>{E(k)} {cnt.get(k, 0):,}</span>' for k, c in [('연동 중', 'on'), ('열쇠 들어오면 바로', 'soon'), ('제공처 열쇠 필요', 'soon'), ('점검 중', 'off')] if cnt.get(k)) + '</div>'
    b += '<div class="toc">' + ''.join(f'<a href="#d-{d}">{d}</a>' for d in doms) + '</div>'
    for d in doms:
        rows = [(k, v) for k, v in it.items() if (v.get('dom') or '공통') == d]
        if not rows: continue
        b += f'<h2 id="d-{d}">{d} <small class="mini">{len(rows)}건</small></h2>'
        for c in cats + sorted({v.get('cat') for k, v in rows} - set(cats)):
            rr = sorted([x for x in rows if x[1].get('cat') == c], key=lambda x: (STATE_WORD.get(x[1].get('state'), ('', ''))[1] != 'on', x[1].get('title', '')))
            if not rr: continue
            b += f'<h3>{E(c or "기타")} <small class="mini">{len(rr)}</small></h3><table class="t"><tr><th>자료</th><th>상태</th><th class="num">건수</th><th class="num">시군</th></tr>'
            for k, v in rr:
                w, cl = STATE_WORD.get(v.get('state'), (v.get('state', ''), ''))
                sm = APISUM.get(k) or {}
                title = re.sub(r'^[^_]*_', '', v.get('title', '')) or v.get('title', '')
                org = v.get('title', '').split('_')[0] if '_' in v.get('title', '') else ''
                b += f'<tr><td>{E(title)}<span class="mini"> {E(org)}</span></td><td class="{"ok" if cl == "on" else "bad" if cl == "off" else "wait"}">{E(w)}</td><td class="num">{format(v["n"], ",") if v.get("n") else ""}</td><td class="num">{len(sm.get("by_unit") or {}) or ""}</td></tr>'
            b += '</table>'
    b += '<h2>업체·기관이 이 자료로 받을 수 있는 것</h2><ul><li>원자료를 매일 정리한 <a href="/sheet/">산지 시세 한 장</a>(경락·도매·소매·수입 단가·출하 예약·이상 신호)</li><li>시군·축종별 집계 파일(업체·인허가 수, 출하 금액, 사육 규모 변화)</li><li>특정 자료의 맞춤 묶음 — <a href="/pro/">업체 등록</a>에서 「지역 수요 보고서」를 고르세요.</li></ul>'
    b += '<p class="mini">출처: 공공데이터포털, 식품안전나라, 국립수산물품질관리원, 농식품 공공데이터포털, 한국농수산식품유통공사 농산물유통정보, 한국은행, 한국석유공사 오피넷, 통계청, 미국 농무부. 각 자료의 이용 조건을 따릅니다.</p>'
    write('/data/', shell('/data/', f'자료 대장 — 가축·어장·농장 공공 자료 {len(it):,}건 | 박씨팜', f'박씨팜이 연동하는 가축·어장·농장·유통 공공 자료 {len(it):,}건. 경락가·도매·소매·수입·도축·위판·질병·인허가·관측 자료를 영역·갈래별로.', b), '0.6')

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
    for k, t in [('ekape_price', '축평원 등급별 경락가'), ('wholesale', '공영도매시장 정산 경락가'), ('origin', '실제 출하 금액(낙찰 원산지)'), ('wipan', '수협 산지 위판(파일, 열쇠 불필요)'), ('files', '파일데이터 일괄(열쇠 불필요)'), ('risk', '수급 위험 예보(7일)'), ('selfcheck', '자가 점검'), ('buysignal', '구매 신호(시험판)'), ('opps', '수급 기회(시험판)'), ('trade', '관세청 수입 단가'), ('license', '지방행정 인허가(가축사육업 등)'), ('signals_sea', '이상 신호 — 수온'), ('signals_price', '이상 신호 — 경락가 급등락'), ('signals_disease', '이상 신호 — 가축전염병'), ('apis', '연동창구 일괄 수집'), ('forms', '접수함(제보·모집·업체)'), ('pages', '글 화면·사이트 지도·새 소식'), ('indexnow', '색인 알림')]:
        c = cols.get(k) or {}
        ok = c.get('ok'); cls = 'ok' if ok else ('bad' if ok is False else 'wait')
        b += f'<tr><td>{E(t)}</td><td>{E(c.get("at", "–"))}</td><td class="{cls}">{"정상" if ok else ("실패" if ok is False else "대기")}</td><td>{E(c.get("msg", ""))}</td></tr>'
    b += '</table>'
    cnt = st.get('counts') or {}
    b += '<h2>자료 규모</h2><dl class="kv">'
    b += f'<dt>가축 축종</dt><dd>{len(LS["species"])}개 · {len(YEARS)}개 연도</dd><dt>양식 면허 구역</dt><dd>{sum(c["n"] for c in AQ["cells"]):,}곳 · {len(AQ["units"])}개 시군</dd><dt>지리적표시</dt><dd>{len([i for i in CR["items"] if not i["off"]])}건 · {len(CR["units"])}개 시군</dd><dt>핀</dt><dd>공판장·가축시장 {len(MK["items"])} · 위판장 {len(PL["wharfs"])} · 도매시장 {len(PL["markets"])}</dd>'
    b += f'<dt>글 화면</dt><dd>{cnt.get("pages", "–")}</dd><dt>양식 접수</dt><dd>{E(str(cnt.get("forms", "넷리파이 양식 화면에서 확인")))}</dd></dl>'
    ap = J('apis.json', {'items': {}})
    if ap.get('items'):
        sm = ap.get('summary', {})
        b += f'<h2>연동 대장 — 연동창구 {len(ap["items"])}건</h2><p class="mini">' + ' · '.join(f'{E(k)} {v}' for k, v in sm.items()) + f' · {E(ap.get("at", ""))}</p>'
        order = {'정상': 0, '실패': 1, '빈 응답': 2, '활용신청 필요': 3, '전용 수집기': 4, '열쇠 대기': 5, '제공처 열쇠': 6, '명세 없음': 7}
        rows = sorted(ap['items'].items(), key=lambda kv: (order.get(kv[1].get('state'), 9), kv[1].get('dom', ''), kv[1].get('cat', '')))
        b += '<table class="t"><tr><th>연동창구</th><th>갈래</th><th>상태</th><th class="num">건수</th><th>메모</th></tr>' + ''.join(
            f'<tr><td>{E(v.get("title", ""))} <span class="mini">{E(k)}</span></td><td>{E(v.get("dom", ""))} · {E(v.get("cat", ""))}</td><td class="{"ok" if v.get("state") == "정상" else "bad" if v.get("state") == "실패" else "wait"}">{E(v.get("state", ""))}</td><td class="num">{v.get("n", "") if v.get("n") is not None else ""}</td><td class="mini">{E(v.get("msg", "") or v.get("at", ""))}</td></tr>' for k, v in rows) + '</table>'
    sc = J('selfcheck.json', {})
    if sc.get('todo') is not None:
        b += f'<h2>자가 점검 — {E(sc.get("at", ""))}</h2><p class="mini">매일 아침 스스로 재고(수집기·자료 신선도·깨진 연결·빈 칸·적중률) 고칠 거리를 뽑습니다. 고침과 2주 뒤 검증은 아침 자가 개선 작업이 맡고, 기록은 docs/개선기록.md 에 남습니다.</p>'
        b += '<dl class="kv">' + ''.join(f'<dt>{E(k)}</dt><dd>{E(str(v))}</dd>' for k, v in (sc.get('fresh') or {}).items()) + f'<dt>화면 수</dt><dd>{sc.get("pages", {}).get("n")}</dd><dt>깨진 내부 연결</dt><dd>{sc.get("pages", {}).get("broken_links")}</dd><dt>활용신청 대기</dt><dd>{sc.get("need_apply", 0)}건</dd></dl>'
        b += '<table class="t"><tr><th>중요도</th><th>갈래</th><th>내용</th><th>고칠 방향</th></tr>' + ''.join(f'<tr><td class="{"bad" if t["level"] == "높음" else "wait"}">{E(t["level"])}</td><td>{E(t["kind"])}</td><td class="mini">{E(t["what"])}</td><td class="mini">{E(t["hint"])}</td></tr>' for t in sc['todo']) + '</table>'
        if sc.get('apply_top'):
            b += '<h3>활용신청 먼저 할 것(위에서부터)</h3><p class="mini">공공데이터포털에 로그인한 채로 이름을 누르면 신청 화면이 열립니다. 「활용신청」 → 목적 「웹 사이트 개발」 → 신청. 승인되면 다음 날 아침 수집부터 자동으로 들어옵니다.</p>'
            b += '<table class="t"><tr><th>연동창구</th><th>풀리는 것</th></tr>' + ''.join(f'<tr><td><a href="https://www.data.go.kr/data/{E(k)}/openapi.do" target="_blank" rel="noopener">{E(t)}</a> <span class="mini">{E(k)}</span></td><td class="mini">{E(why)}</td></tr>' for k, t, w, why in sc['apply_top'] if k.isdigit()) + '</table>'
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
        b += f'<p><a class="btn prime" href="/map/?u={urllib.parse.quote(u)}">지도에서 보기</a></p>'
        b += '<h2>동물농장 — 무엇을 얼마나 키우나</h2>'
        if a:
            b += f'<table class="t"><tr><th>축종</th><th class="num">농가</th><th class="num">마릿수</th><th class="num">{YEARS[0]}년 대비 농가</th></tr>'
            for k, h, n, w in a[:10]:
                s = next(x for x in LS['species'] if x['k'] == k); r = s['d'][u]['y']
                i0 = next((i for i, v in enumerate(r) if v and v[0] > 0), None)
                ch = f'{(h / r[i0][0] - 1) * 100:+.0f}%' if i0 is not None and i0 < len(r) - 1 and r[i0][0] >= 10 else '–'
                b += f'<tr><td><a href="/map/?sp={urllib.parse.quote(k)}&u={urllib.parse.quote(u)}">{E(k)}</a></td><td class="num">{h:,}호</td><td class="num">{n:,}{E(w)}</td><td class="num">{ch}</td></tr>'
            b += f'</table><p class="mini">가축위생방역지원본부 사육규모 현황, {last}년 1월 기준.</p>'
        else: b += '<p>이 시군의 가축 사육 기록이 없습니다.</p>'
        b += '<h2>어장 — 양식 면허</h2>'
        if e:
            b += f'<p>양식 면허 <b>{e["n"]:,}건</b>, 면허 면적 <b>{man(e["ha"])}㏊</b>. 마을어장(어촌계) {e["v"][0]}곳 · {man(e["v"][1])}㏊' + (f', 정치망 {e["j"]}곳' if e['j'] else '') + '.</p>'
            if e['top']: b += '<table class="t"><tr><th>품종</th><th class="num">면허</th><th class="num">면적</th></tr>' + ''.join(f'<tr><td><a href="/map/?mode=sea&sp={urllib.parse.quote(t[0])}&u={urllib.parse.quote(u)}">{E(t[0])}</a></td><td class="num">{t[1]:,}건</td><td class="num">{man(t[2])}㏊</td></tr>' for t in e['top']) + '</table><p class="mini">국립해양조사원 어장정보도 2025. 지도를 확대하면 면허 구역이 하나씩 보입니다.</p>'
        else: b += '<p>이 시군에는 어장 면허 기록이 없습니다.</p>'
        wc = [x for x in WPN.get('coops', []) if x.get('u') == u]
        if wc:
            b += f'<h2>어장 — 수협 위판 실적({E(WPN["month"].replace("-", "년 "))}월)</h2>'
            for wcc in wc[:3]:
                b += f'<h3>{E(wcc["name"].replace("수산업협동조합", "수협"))} <small class="mini">{man(wcc["amt"])}원</small></h3><table class="t"><tr><th>어종(상태)</th><th class="num">위판 금액</th><th class="num">원/㎏</th></tr>' + ''.join(f'<tr><td>{E(x[0])}</td><td class="num">{man(x[1])}원</td><td class="num">{format(x[2], ",") if x[2] else "–"}</td></tr>' for x in wcc['top']) + '</table>'
            b += '<p class="mini">해양수산부 일자별 위탁판매 현황(수협 산지 위판). 조합 소재 시군 기준.</p>'
        o = ORIG.get('units', {}).get(u)
        if o:
            b += '<h2>농장 — 실제로 팔린 품목(도매시장 낙찰 금액)</h2><table class="t"><tr><th>품목</th><th>갈래</th><th class="num">금액(최근 ' + str(len(ORIG.get('months', []))) + '개월)</th></tr>' + ''.join(f'<tr><td>{E(x[0])}</td><td>{E(x[2])}</td><td class="num">{man(x[1])}원</td></tr>' for x in o['top']) + '</table><p class="mini">한국농수산식품유통공사 경매원천정보, 원산지 기준. 농협 수매 품목 제외.</p>'
        b += '<h2>농장 — 대표 판매 품목</h2>'
        if c:
            b += '<p>' + ', '.join(f'<a href="/map/?mode=crop&sp={urllib.parse.quote(i)}">{E(i)}</a>' for i in c['items']) + '</p>'
            b += '<table class="t"><tr><th>등록 명칭</th><th>갈래</th><th>등록일</th></tr>' + ''.join(f'<tr><td>{E(x["name"])}</td><td>{E(x["cat"])} · {E(x["kind"])}</td><td>{E(x["date"])}</td></tr>' for x in c['list']) + '</table><p class="mini">지리적표시 등록부(2024년 4월). 주력 품목의 실제 출하 금액(도매시장·공판장 경락 원자료의 산지 기준)이 쌓이는 대로 보탭니다. 등록 농가 수는 쓰지 않습니다.</p>'
        else: b += '<p>아직 지리적표시로 등록된 품목이 없습니다.</p>'
        b += '<h2>팔 곳 — 공판장·가축시장·위판장·도매시장</h2>'
        if pins: b += '<ul>' + ''.join(f'<li><a href="/map/?mode={"sea" if p["type"] == "위판장" else "crop" if p["type"] == "도매시장" else "ani"}&pin={p["id"]}">{E(p["name"])}</a> <span class="mini">{E(p["type"])}{"" if p.get("verified") else " · 위치 근사"}</span></li>' for p in pins) + '</ul>'
        else: b += '<p>이 시군 안에는 등록된 공판장·위판장·도매시장이 없습니다. 지도에서 이웃 시군의 시장을 보세요.</p>'
        ex = sorted(((k, sm) for k, sm in APISUM.items() if (sm.get('by_unit') or {}).get(u)), key=lambda x: -x[1]['by_unit'][u])
        if ex:
            b += '<h2>공공 자료로 본 이 시군 — 업체·시설·기록 수</h2><table class="t"><tr><th>자료</th><th class="num">이 시군</th><th class="num">전국</th></tr>' + ''.join(f'<tr><td>{E(re.sub(r"^[^_]*_", "", sm.get("title", "")))}</td><td class="num">{sm["by_unit"][u]:,}</td><td class="num">{sm.get("n", 0):,}</td></tr>' for k, sm in ex[:25]) + '</table><p class="mini">공공데이터포털 연동창구를 매일 불러 주소·시군 항목으로 센 값. 개별 업체 이름은 싣지 않습니다. <a href="/data/">자료 대장 →</a></p>'
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


# ── 첫 화면: 오늘의 농축수산물 가격 예보판 (2026-10-28 컨셉 확정 — 박씨팜 = 농축수산물 가격 예보)
CROPS2 = J('cropsignal.json', {}); FC = J('forecast.json', {}); RISK2 = J('risk.json', {})
def home_page():
    DIRW = {'오름 쪽': ('오름', 'up'), '내림 쪽': ('내림', 'dn'), '보합': ('보합', 'flat')}
    def badge(d): w, c = DIRW.get(d, (d or '보합', 'flat')); return f'<span class="fx {c}">{E(w)}</span>'
    def won(v): return f'{v:,}원' if isinstance(v, (int, float)) and v else ''
    today = (FC.get('at') or stamp())[:10]
    b = f'<p class="crumb">{E(today)} 아침 기준 · 매일 갱신</p><h1 class="title">농축수산물 가격 예보</h1>'
    b += '<p class="lead">축산·수산·농산 품목이 앞으로 오를지 내릴지를 근거와 함께 매일 아침 알려 드립니다. 지난 예보는 실제 값으로 채점해 적중률까지 공개합니다. 박씨팜은 물건을 사고팔지 않는, 이해관계 없는 예보처입니다.</p>'
    # 경보
    al = list(FC.get('alerts') or [])
    for x in RISK2.get('species', []):
        if x.get('lv') in ('위험', '주의'): al.append({'level': '경보' if x['lv'] == '위험' else '주의', 'kind': '폐사 위험', 'title': f'{x.get("sp")} 고수온·폐사 {x["lv"]}', 'react': '공급이 줄 수 있음 — 수산 예보 참고'})
    if al:
        al.sort(key=lambda a: 0 if a.get('level') == '경보' else 1)
        b += '<h2>오늘의 경보</h2><ul class="alerts">' + ''.join(f'<li><span class="lv {"hi" if a.get("level") == "경보" else "mid"}">{E(a.get("level", ""))}</span><b>{E(a.get("kind", ""))}</b> {E(a.get("title", ""))}<div class="mini">{E(a.get("react", ""))}</div></li>' for a in al[:6]) + '</ul>'
    # 세 갈래 예보판
    dec = {d['id']: d for d in FC.get('decisions', [])}; mt = FC.get('micro_track') or {}
    def rate(k):
        t = mt.get(k) or {}
        return f'적중 {t["hit"]}/{t["n"]}({t["rate"]}%)' if t.get('n') else '채점 대기'
    # 축산
    ca = '<div class="fc-card"><div class="fc-h"><b>축산</b><span class="mini">앞으로 2주 · 경락가</span></div><table class="t fc">'
    for k, nm in (('hanwoo', '한우 거세'), ('pig', '돼지 탕박')):
        d = dec.get(k)
        if d:
            dr = '내림 쪽' if '내림' in d['act'] or '매도' in d['act'] else '오름 쪽' if '오름' in d['act'] or '미루' in d['act'] else '보합'
            ca += f'<tr><td>{E(nm)}</td><td>{badge(dr)}</td><td class="mini">{E(d["act"])}<br>{E((d.get("why") or [""])[0])}</td></tr>'
    for n in (next((s for s in FC.get('sectors', []) if s['sector'] == '축산'), {}).get('notes') or [])[:3]:
        ca += f'<tr><td>{E(n["item"])}</td><td>{badge(n["dir"])}</td><td class="mini">{E(n["text"][:70])} <span class="src">{E(n["src"][:30])}</span></td></tr>'
    d = dec.get('feed')
    if d: ca += f'<tr><td>배합사료(원가)</td><td>{badge("보합" if "관망" in d["act"] else "오름 쪽" if "선매" in d["act"] or "앞당" in d["act"] else "내림 쪽")}</td><td class="mini">{E(d["act"])} · {E(d["horizon"][:22])}</td></tr>'
    ca += '</table><p class="mini">근거: 축산물품질평가원 경락가 · 해외 선물 · 관측 기관 전망</p></div>'
    # 수산
    bi = [i for i in (BUYS.get('items') or []) if i['dir'] != '보합']; bi.sort(key=lambda i: -abs(i['score']))
    sa = f'<div class="fc-card"><div class="fc-h"><b>수산</b><span class="mini">다음 달 · 산지 위판가 · {E(rate("수산"))}</span></div><table class="t fc">'
    sa += ''.join(f'<tr><td>{E(i["item"])}</td><td>{badge(i["dir"])}</td><td class="mini">{won(i["wonkg"])}/㎏ · {E((i.get("why") or [""])[0])}</td></tr>' for i in bi[:8]) or '<tr><td colspan="3" class="mini">뚜렷한 방향이 없는 달입니다(전 품목 보합).</td></tr>'
    sa += f'</table><p class="mini">근거: 수협 산지 위판 · 창고 재고 · 폐사 위험 예보 · 보합 {sum(1 for i in BUYS.get("items") or [] if i["dir"] == "보합")}품목</p></div>'
    # 농산
    ci = [i for i in (CROPS2.get('items') or []) if i['dir'] != '보합']; ci.sort(key=lambda i: -abs(i['score']))
    na = f'<div class="fc-card"><div class="fc-h"><b>농산</b><span class="mini">앞으로 2주 · 도매시장가 · {E(rate("농산"))}</span></div><table class="t fc">'
    na += ''.join(f'<tr><td>{E(i["item"])}</td><td>{badge(i["dir"])}</td><td class="mini">{won(i["wonkg"])}/㎏ · {E((i.get("why") or [""])[0])}</td></tr>' for i in ci[:8]) or '<tr><td colspan="3" class="mini">뚜렷한 방향이 없는 주입니다(전 품목 보합).</td></tr>'
    na += f'</table><p class="mini">근거: 공영도매시장 26곳 정산 {E(str(CROPS2.get("ndays", 0)))}거래일 · 보합 {sum(1 for i in CROPS2.get("items") or [] if i["dir"] == "보합")}품목</p></div>'
    b += '<h2>품목별 예보</h2><div class="fc-grid">' + ca + sa + na + '</div>'
    b += '<p class="mini">「오름」이면 미리 사 두거나 출하를 늦추는 쪽, 「내림」이면 구매를 미루거나 출하를 서두르는 쪽으로 검토하세요. 품목마다 자세한 근거와 지난 적중 기록은 <a href="/signal/">근거·적중</a>에 있습니다.</p>'
    # 원가 압력
    secs = FC.get('sectors') or []
    if secs:
        b += '<h2>원가 압력 — 기름값·환율·원료가</h2><div class="grid3">' + ''.join(f'<div class="card"><h3>{E(x["sector"])} {badge((x.get("cost") or {}).get("dir"))}</h3><div class="big">{(x.get("cost") or {}).get("v", 0):+}<i>%</i></div><p>{E(" · ".join(((x.get("cost") or {}).get("why") or [])[:3]))}</p></div>' for x in secs) + '</div>'
        cm = FC.get('common') or []
        if cm: b += '<ul class="mini">' + ''.join(f'<li>{E(n["item"])}: {E(n["text"][:110])} <span class="src">({E(n["src"][:36])})</span></li>' for n in cm[:3]) + '</ul>'
    # 해외 선물·환율
    tl = FC.get('tiles') or []
    if tl:
        b += '<h2>세계 시세 — 선물·환율</h2><table class="t"><tr><th>지표</th><th class="num">최근</th><th class="num">1개월</th><th class="num">3개월</th><th>흐름</th></tr>' + ''.join(
            f'<tr><td>{E(t["name"])}</td><td class="num">{t["last"]:,}</td><td class="num">{t.get("c20", 0):+}%</td><td class="num">{t.get("c60", 0):+}%</td><td>{E(t.get("trend", ""))}</td></tr>' for t in tl[:13]) + '</table>'
    # 받아 보기
    b += '<h2>예보 받아 보기</h2><div class="grid2"><div class="card"><h3>유통·가공·급식 업체</h3><p>우리 회사가 사는 품목만 골라 매주 예보와 경보를 받는 구독을 준비하고 있습니다.</p><p style="margin-top:10px;"><a class="btn prime" href="/pro/">업체 등록·구독 신청</a></p></div><div class="card"><h3>농가·어가</h3><p>오늘 시세와 예보를 한 장에 담은 「시세 한 장」을 무료로 받아 보세요.</p><p style="margin-top:10px;"><a class="btn" href="/sheet/">시세 한 장 보기</a></p></div></div>'
    b += f'<p class="mini" style="margin-top:22px;">자료: {E(FC.get("basis", ""))}. 예보는 공개 자료로 만든 참고 정보이며 거래를 권하는 것이 아닙니다. 지도로 보려면 <a href="/map/">시군별 지도</a>.</p>'
    ld = {'@context': 'https://schema.org', '@type': 'WebSite', 'name': '박씨팜', 'url': BASE + '/', 'description': '농축수산물 가격 예보 — 축산·수산·농산 품목별 값 방향, 경보, 적중 기록'}
    write('/', shell('/', '박씨팜 — 농축수산물 가격 예보(축산·수산·농산) | 오늘 오를 품목·내릴 품목', '한우·돼지 경락가, 수협 위판가, 공영도매시장 값이 앞으로 오를지 내릴지를 근거와 적중률과 함께 매일 아침 예보합니다. 사료·기름값 원가 압력, 해외 선물·환율, 폐사 경보까지.', b, jsonld=ld), '1.0')

def misc():
    write('/404.html', shell('/404.html', '그런 화면이 없습니다 | 박씨팜', '없는 화면', '<h1 class="title">그런 화면이 없습니다</h1><p class="lead">주소가 바뀌었거나 잘못 적힌 것 같습니다. <a href="/">지도로 돌아가기</a> · <a href="/p/">시군별 보기</a></p>', noindex=True))
    # 사이트 지도
    pages = [('/map/', TODAY, '0.9')] + PAGES   # 첫 화면('/')은 home_page 가 PAGES 에 넣음
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
    inject_index(); home_page(); price_page(); buy_page(); gongu_page(); sheet_page(); calc_page(); partner_page(); pro_page(); about_page(); sigun_pages(); risk_page(); signal_page(); opps_page(); data_page(); console_page(); misc()
    print('글 화면', len(PAGES) + 1)
