# 미리보기 그림(og) 생성 — 시그니처 판(2026-10-29): 짙은 녹색 바탕 + 종합 지수 흐름선, 「박씨팜 — 농축수산물 가격 예측 시스템」, 구호 띠.
#   처음·물가 지수·품목별·경보·세계 요인·적중 기록·예측 기법·시세·위험·수급 기회·업체·지도 + 품목 예보 100장 + 시군별 161장. 선 아이콘·이모지 없음, 글자와 선만.
#   자료: site/data/cards.json(forecast_pages 가 씀), pindex.json. 올리기 작업(pages.yml)에서 글 화면 생성 뒤에 돌린다.
import json, os, sys, collections
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brand as BR
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'site'); OUT = os.path.join(SITE, 'og'); os.makedirs(os.path.join(OUT, 'p'), exist_ok=True)
F = lambda w, s: ImageFont.truetype(os.path.join(ROOT, 'tools', 'fonts', f'Pretendard-{w}.otf'), s)
INK = (30, 38, 33); MUTE = (104, 113, 106); MOSS = (44, 85, 48); DEEP = (23, 32, 25); MID = (30, 47, 34); LINE = (228, 232, 226)
BRICK = (168, 69, 44); BLUE = (47, 95, 138); WHITE = (255, 255, 255); SOFT = (214, 226, 212)
W, H = 1200, 630
J = lambda p, d=None: (json.load(open(os.path.join(SITE, 'data', p), encoding='utf-8')) if os.path.exists(os.path.join(SITE, 'data', p)) else (d if d is not None else {}))
CARDS = J('cards.json'); PX = J('pindex.json')

def seal(d, x, y, s=44, fg=WHITE, bg=MOSS):
    d.rounded_rectangle([x, y, x + s, y + s], radius=s * 0.23, fill=bg)
    w = max(2, int(s * 0.06))
    d.line([x + s * 0.19, y + s * 0.77, x + s * 0.81, y + s * 0.77], fill=fg, width=w)
    d.line([x + s * 0.5, y + s * 0.77, x + s * 0.5, y + s * 0.45], fill=fg, width=w)
    d.polygon([(x + s * 0.5, y + s * 0.5), (x + s * 0.27, y + s * 0.3), (x + s * 0.5, y + s * 0.36)], fill=fg)
    d.polygon([(x + s * 0.45, y + s * 0.45), (x + s * 0.75, y + s * 0.22), (x + s * 0.5, y + s * 0.3)], fill=fg)

def gradient(im):
    """왼쪽 위 짙은 녹색 → 오른쪽 아래 이끼색"""
    px = im.load()
    for x in range(0, W, 4):
        t = x / W
        col = tuple(int(DEEP[i] + (MOSS[i] - DEEP[i]) * (0.15 + 0.85 * t)) for i in range(3))
        for xx in range(x, min(W, x + 4)):
            for y in range(H): px[xx, y] = col

_bg = None
def base():
    """공통 바탕: 그라데이션 + 종합 지수 흐름선(없으면 잔잔한 파도) + 아래 구호 띠"""
    global _bg
    if _bg is None:
        im = Image.new('RGB', (W, H), DEEP); gradient(im)
        ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        vals = [x[1] for x in ((PX.get('total') or {}).get('daily') or [])[-60:]]
        if len(vals) < 4: vals = [100 + 6 * __import__('math').sin(i / 4.0) + 3 * __import__('math').sin(i / 1.7) for i in range(48)]
        lo, hi = min(vals), max(vals); rng = (hi - lo) or 1
        pts = [(W * i / (len(vals) - 1), 520 - 230 * (v - lo) / rng) for i, v in enumerate(vals)]
        d.polygon(pts + [(W, 580), (0, 580)], fill=(255, 255, 255, 22))
        d.line(pts, fill=(255, 255, 255, 120), width=3, joint='curve')
        im.paste(ov, (0, 0), ov)
        _bg = im
    return _bg.copy()

def wrap(d, text, font, maxw):
    """글자 폭 기준 줄바꿈(어절 단위)"""
    out, cur = [], ''
    for w in text.split(' '):
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=font) <= maxw: cur = t
        else:
            if cur: out.append(cur)
            cur = w
    if cur: out.append(cur)
    return out

def card(path, title, lines, kicker=None, badge=None, badge_col=None, big=None, big_sub=None, tag=None, foot=None):
    """시그니처 판 한 장. title 큰 제목, lines [(글, 색)], badge 오른쪽 위 표(예: 내림), big 오른쪽 큰 숫자"""
    im = base(); d = ImageDraw.Draw(im)
    seal(d, 64, 56, 46, fg=WHITE, bg=(255, 255, 255, 0) and MOSS)
    d.text((124, 58), BR.NAME, font=F('Bold', 34), fill=WHITE)
    d.text((124 + d.textlength(BR.NAME, font=F('Bold', 34)) + 18, 70), BR.SYSTEM, font=F('Medium', 21), fill=SOFT)
    if tag: d.text((W - 64, 66), tag, font=F('Medium', 22), fill=SOFT, anchor='ra')
    if kicker: d.text((64, 150), kicker, font=F('Medium', 24), fill=SOFT)
    y = 186 if kicker else 160
    tf = F('ExtraBold', 76 if len(title) <= 11 else 62 if len(title) <= 16 else 50)
    maxw = W - 128 - (300 if (badge or big) else 0)
    tl = wrap(d, title, tf, maxw)[:2]
    for ln in tl: d.text((64, y), ln, font=tf, fill=WHITE); y += tf.size + 10
    y += 14
    for ln, col in lines[:3]:
        f = F('Medium', 27)
        for sub in wrap(d, ln, f, maxw)[:1]: d.text((64, y), sub, font=f, fill=col or SOFT); y += 40
    if badge:
        bf = F('ExtraBold', 44); bw = d.textlength(badge, font=bf) + 56
        x0 = W - 64 - bw; d.rounded_rectangle([x0, 160, W - 64, 236], radius=18, fill=badge_col or MOSS)
        d.text((x0 + bw / 2, 198), badge, font=bf, fill=WHITE, anchor='mm')
    if big:
        d.text((W - 64, 262 if badge else 180), big, font=F('ExtraBold', 64), fill=WHITE, anchor='ra')
        if big_sub: d.text((W - 64, 338 if badge else 256), big_sub, font=F('Medium', 22), fill=SOFT, anchor='ra')
    # 아래 구호 띠
    d.rectangle([0, 556, W, H], fill=(255, 255, 255))
    d.text((64, 574), BR.SLOGAN, font=F('ExtraBold', 28), fill=INK)
    d.text((W - 64, 580), foot or (BR.URL_SHORT + ' · ' + ' · '.join(BR.PROMISE)), font=F('Medium', 19), fill=MUTE, anchor='ra')
    d.rectangle([0, H - 8, W, H], fill=MOSS)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, optimize=True)

def man(n):
    if n >= 10000: return f'{n / 10000:.1f}만'.replace('.0만', '만')
    return f'{n:,.0f}'

cnt = CARDS.get('counts') or {}; idx = CARDS.get('index') or {}; wd = CARDS.get('world') or {}; rate = CARDS.get('rate') or {}
today = CARDS.get('at', '')
def itxt(k):
    v = idx.get(k)
    return f'{k} {v[0]:.1f} {v[1]}' + (f'({v[2]:+}%/20일)' if v and v[2] is not None else '') if v else None
n = 0
# 처음
card(os.path.join(OUT, 'home.png'), BR.SLOGAN, [(f'{today} 아침 예보 — 품목 {len(CARDS.get("items") or [])}개 가운데 오름 {cnt.get("오름", 0)} · 내림 {cnt.get("내림", 0)} · 보합 {cnt.get("보합", 0)}', WHITE), ('한우·돼지 경락가 · 수협 위판가 · 공영도매시장 값 · 세계 요인 · 물가 지수', None), ('근거와 적중 기록까지 매일 아침 공개 — 사고팔지 않는 예보', None)], kicker='오늘의 농축수산물 가격 예보'); n += 1
# 물가 지수
card(os.path.join(OUT, 'index.png'), '농축수산물 물가 지수', [(' · '.join(x for x in (itxt('종합'), itxt('축산')) if x) or '갈래·종합·원가 압력 지수', WHITE), (' · '.join(x for x in (itxt('수산'), itxt('농산')) if x) or '', None), ('5일선·20일선·기울기·±2σ 띠·교차로 경향을 계량', None)], kicker='주식 차트처럼 읽는 경향 분석', big=(f'{idx["종합"][0]:.1f}' if idx.get('종합') else None), big_sub=(('종합 · ' + idx['종합'][1]) if idx.get('종합') else None)); n += 1
# 품목별
gp = CARDS.get('gap') or {}
card(os.path.join(OUT, 'gap.png'), '갭 기회 — 해외·국내 값 차이', [(' · '.join(f'{h[0].split(" ↔ ")[0]} {h[2]:+}%' for h in (gp.get('hot') or [])[:3]) or f'오늘 갭 없음 — 짝 {gp.get("n", 0)}개 감시', WHITE), ('원산지 현지 시세 × 환율 ↔ 국산 경락가·위판가·도매가', None), ('띠를 벗어난 순간을 잡고, 되돌아왔는지 채점', None)], kicker='수입으로 바꿀까, 국산을 담을까'); n += 1
sp = CARDS.get('source') or {}
card(os.path.join(OUT, 'source.png'), '원산지 거래 정보', [(' · '.join(f'{h[0]}({"·".join(h[2])})' for h in (sp.get('hot') or [])[:3]) or '국내가 부족할 때 어디서 들여오나', WHITE), ('부족 신호 → 원산지 후보 · 오늘 상태 · 현지 시세 · 수입 단가 · 요건', None), ('수요가 모이면 등록 수입업체 견적 — 박씨팜은 거래에 끼지 않음', None)], kicker='국내가 부족할 때 어디서 들여오나'); n += 1
card(os.path.join(OUT, 'f.png'), '품목별 가격 예보', [(f'축산 · 수산 · 농산 {len(CARDS.get("items") or [])}개 품목 — 방향 · 세기 · 근거 · 값 흐름', WHITE), ('싸게 거래된 곳 · 대체 품목 · 지난 예보의 결과까지', None), ('매일 아침 자동 갱신', None)], kicker='오를 품목, 내릴 품목'); n += 1
card(os.path.join(OUT, 'alerts.png'), '오늘의 경보', [(f'경보·주의 {CARDS.get("alerts", 0)}건 — 해외 시세 급변 · 폐사 위험 · 가축 더위 · 세계 요인 · 물가 지수 교차', WHITE), ('경보마다 「미리 할 일」을 적습니다', None)], kicker='먼저 알아야 할 것'); n += 1
card(os.path.join(OUT, 'world.png'), '세계·원산지 요인 감시', [(f'요인 {wd.get("n", 0)}개 감시 — 오늘 켜진 요인 {wd.get("active", 0)}건(경보 {wd.get("alarm", 0)})', WHITE), ('기후·해양 · 질병·방역 · 지정학·에너지 · 정책 · 세계 상품 · 원가·경기', None), ('수입 품목 73개 × 원산지 57개 나라 행렬로 국내 품목 점수에 반영', None)], kicker='브라질 닭·페루 어분·엘니뇨·환율까지'); n += 1
r1 = rate.get('수산') or [0, 0, 0]; r2 = rate.get('농산') or [0, 0, 0]
card(os.path.join(OUT, 'track.png'), '적중 기록 — 숨기지 않고 공개', [(f'수산 {r1[1]}/{r1[0]}건' + (f'({r1[2]}%)' if r1[0] else '') + ' · 농산 ' + (f'{r2[1]}/{r2[0]}건({r2[2]}%)' if r2[0] else '첫 채점 대기') + ' · 축산 기록 중', WHITE), ('모든 예보는 그날 기록해 두고 실제 값으로 자동 채점합니다', None), ('틀린 예보도 지우지 않습니다 — 적중 기록이 곧 신용', None)], kicker='채점되는 예보'); n += 1
card(os.path.join(OUT, 'method.png'), '박씨팜 예측 기법', [('거미집 · 저장 이론 · 아밍턴 · 비대칭 전가 · 엘니뇨 수확량 · 브라이어 채점', WHITE), ('검증된 이론과 실증을 우리가 가진 공개 자료에 맞게 조립한 틀', None), ('모든 판단은 기록·채점되어 기준이 스스로 고쳐집니다', None)], kicker='왜 이렇게 예측하나'); n += 1
card(os.path.join(OUT, 'price.png'), '오늘 시세', [('소·돼지 등급별 경락가 · 공판장별 경매 · 수협 위판 · 공영도매시장 정산', WHITE), ('값만 보지 말고 예보와 같이', None)], kicker='경락가·위판가·도매가'); n += 1
card(os.path.join(OUT, 'risk.png'), '수급 위험 예보', [('7일 바다 수온 × 품종별 한계 수온 × 양식 면허 면적 — 폐사 위험', WHITE), ('기온·습도 예보 × 사육 두수 — 가축 더위 위험', None), ('공급이 줄기 전에 미리', None)], kicker='고수온·더위'); n += 1
card(os.path.join(OUT, 'opps.png'), '수급 기회', [('같은 어종, 조합마다 다른 위판 값 — 싸게 사는 산지', WHITE), ('공급 넘침 · 공급 빠듯 · 자연산 대 양식 값 차이', None)], kicker='어디서 사면 더 싼가'); n += 1
card(os.path.join(OUT, 'sheet.png'), '시세 한 장', [('오늘 시세와 예보를 한 장에 — 농가·어가 무료', WHITE), ('인쇄해서 벽에 붙이는 아침 한 장', None)], kicker='농가·어가를 위한'); n += 1
card(os.path.join(OUT, 'pro.png'), '업체 등록 · 데이터 구독', [('우리 회사가 사는 품목만 골라 매주 예보와 경보를 받는 구독', WHITE), ('급식·식자재 유통 · 수산 가공 · 외식·마트 구매 · 축산 유통·사료 · 기관', None), ('박씨팜은 물건을 사고팔지 않습니다', None)], kicker='매주 사는 결정을 하는 분께'); n += 1
card(os.path.join(OUT, 'map.png'), '시군별 사육·양식·대표 품목 지도', [('가축 35개 축종 · 양식 면허 구역 11,486곳 · 지리적표시 204건', WHITE), ('공판장·가축시장·수협 위판장·공영도매시장 위치와 경락가', None), ('개별 농가·어가 위치는 싣지 않습니다', None)], kicker='예보의 바탕'); n += 1
card(os.path.join(OUT, 'buy.png'), '옆집은 얼마에 사나', [('사료 · 종묘 · 비료 · 자재 구입가 시세판', WHITE), ('익명 제보 → 시군별 중위값 → 내 가격 성적표', None)], kicker='구입가'); n += 1
card(os.path.join(OUT, 'gongu.png'), '사료·자재 공동구매 모집판', [('같은 시군 농가끼리 모아서 싸게 — 모집과 연결만', WHITE), ('배합사료 · 양식 사료 · 비료 · 포장 박스·스티로폼·그물망', None)], kicker='수요를 모읍니다'); n += 1
card(os.path.join(OUT, 'data.png'), '자료 대장', [('공개 자료 625건 — 무엇을 어디서 언제 받는지 모두 적어 둡니다', WHITE), ('연동 상태 · 갱신 주기 · 열쇠 유무', None)], kicker='투명한 자료'); n += 1
# 품목 예보 카드
DIRC = {'오름': BRICK, '내림': BLUE, '보합': (104, 113, 106)}
for it in CARDS.get('items') or []:
    w = it.get('w') or '보합'; price = it.get('price')
    lines = [(it.get('horizon', ''), WHITE)]
    if it.get('why'): lines.append((it['why'][:60], None))
    h = it.get('hist') or [0, 0]
    lines.append((f'지난 예보 {h[0]}건 중 {h[1]}건 적중' if h[0] else '근거 · 값 흐름 · 싸게 거래된 곳 · 지난 예보 결과', None))
    card(os.path.join(OUT, it['url'].strip('/') + '.png'), f'{it["item"]} 가격 예보', lines, kicker=f'{it["sector"]} · {today} 아침 예보', badge=w, badge_col=DIRC.get(w),
         big=(f'{price:,.0f}원' if isinstance(price, (int, float)) and price else None), big_sub=(it.get('unit') + ' · 지금') if price else None, tag='신호 세기 ' + '●' * int(it.get('strength') or 0) + '○' * (5 - int(it.get('strength') or 0))); n += 1
# 시군별
LS, AQ, CR = J('livestock.json', {'species': []}), J('aqua.json', {'units': {}}), J('crops.json', {'units': {}})
ani = collections.defaultdict(list)
for s in LS.get('species', []):
    for u, r in s['d'].items():
        y = r['y'][-1]
        if y and y[1] > 0: ani[u].append((s['k'], y[1], s['w']))
try: units = [g['properties']['u'] for g in J('units.json')['objects']['units']['geometries']]
except Exception: units = []
for u in units:
    sd, sg = u.split('|'); name = sd if sd == sg else sd + ' ' + sg
    a = sorted(ani.get(u, []), key=lambda x: -x[1])[:3]; e = AQ['units'].get(u); c = CR['units'].get(u)
    lines = []
    if a: lines.append(('동물농장  ' + ' · '.join(f'{k} {man(v)}{w}' for k, v, w in a), WHITE))
    if e: lines.append(('어장  양식 면허 ' + f'{e["n"]:,}건' + (' · ' + ', '.join(t[0] for t in e['top'][:3]) if e['top'] else ''), None))
    if c: lines.append(('농장  ' + ', '.join(c['items'][:4]), None))
    if not lines: lines.append(('시군별 사육·양식·대표 품목 기록 정리', None))
    card(os.path.join(OUT, 'p', f'{sd}_{sg}.png'), name, lines, kicker='시군별 사육·양식·대표 품목', tag='시군별'); n += 1
print('미리보기 그림', n)
