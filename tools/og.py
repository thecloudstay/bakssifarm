# 미리보기 그림(og) 생성: 처음·경락가·공동구매·데이터·시군별 161장. 흰 바탕, 선 아이콘 없음, 글자만.
import json, os, collections
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'site'); OUT = os.path.join(SITE, 'og'); os.makedirs(os.path.join(OUT, 'p'), exist_ok=True)
F = lambda w, s: ImageFont.truetype(os.path.join(ROOT, 'tools', 'fonts', f'Pretendard-{w}.otf'), s)
INK = (30, 38, 33); MUTE = (104, 113, 106); MOSS = (44, 85, 48); LINE = (228, 232, 226)
def seal(d, x, y, s=44):
    d.rounded_rectangle([x, y, x + s, y + s], radius=s * 0.23, fill=MOSS)
    w = s * 0.06
    d.line([x + s * 0.19, y + s * 0.77, x + s * 0.81, y + s * 0.77], fill='white', width=int(w))
    d.line([x + s * 0.5, y + s * 0.77, x + s * 0.5, y + s * 0.45], fill='white', width=int(w))
    d.polygon([(x + s * 0.5, y + s * 0.5), (x + s * 0.27, y + s * 0.3), (x + s * 0.5, y + s * 0.36)], fill='white')
    d.polygon([(x + s * 0.5, y + s * 0.45), (x + s * 0.75, y + s * 0.22), (x + s * 0.5, y + s * 0.3)], fill='white')
def card(path, title, lines, kicker='박씨네', tag=None):
    im = Image.new('RGB', (1200, 630), 'white'); d = ImageDraw.Draw(im)
    seal(d, 72, 64); d.text((130, 66), kicker, font=F('Bold', 34), fill=INK)
    if tag: d.text((1128, 72), tag, font=F('Medium', 24), fill=MUTE, anchor='ra')
    y = 190; tf = F('ExtraBold', 70 if len(title) <= 14 else 56)
    d.text((72, y), title, font=tf, fill=INK); y += (tf.size + 26)
    for ln, col in lines:
        f = F('Medium', 30); d.text((72, y), ln, font=f, fill=col or MUTE); y += 46
    d.rectangle([0, 614, 1200, 630], fill=MOSS)
    d.line([72, 560, 1128, 560], fill=LINE, width=2)
    d.text((72, 574), 'bakssine.netlify.app · 전국 시군 집계 · 개별 농가 위치는 싣지 않습니다', font=F('Medium', 20), fill=MUTE)
    im.save(path, optimize=True)
J = lambda p: json.load(open(os.path.join(SITE, 'data', p), encoding='utf-8'))
LS, AQ, CR, PL, MK = J('livestock.json'), J('aqua.json'), J('crops.json'), J('places.json'), J('markets.json')
def man(n):
    if n >= 10000: return f'{n / 10000:.1f}만'.replace('.0만', '만')
    return f'{n:,.0f}'
card(os.path.join(OUT, 'home.png'), '농장·어장·동물농장 한 지도', [('가축 35개 축종 · 2018~2026년 시군별 사육 현황', None), ('양식 면허 구역 11,486곳 · 수협 위판장 63', None), ('지리적표시 대표 품목 204건 · 공영도매시장 32', None), ('공판장·가축시장 위치와 경락가 조회, 공동구매 모집판', MOSS)])
card(os.path.join(OUT, 'price.png'), '경락가 조회', [('소·돼지 등급별 경락가 · 공판장별 경매', None), ('농산물 도매시장 경락가 · 수협 위판 시세', None), ('내 품목 가격 알림', MOSS)])
card(os.path.join(OUT, 'gongu.png'), '사료·자재 공동구매 모집판', [('같은 시군 농가끼리 모아서 싸게', None), ('배합사료 · 양식 사료 · 비료 · 농자재', None), ('박씨네는 판매자가 아닙니다 — 모집과 연결만', MOSS)])
card(os.path.join(OUT, 'pro.png'), '데이터 상품과 업체 등록', [('리별 사료 수요 지도 · 진입·이탈 지수', None), ('공판장별 가격차 · 양식 면허 만료 달력', None), ('사료·도축·운송·수의 업체 지역 등록', MOSS)])
ani = collections.defaultdict(list)
for s in LS['species']:
    for u, r in s['d'].items():
        y = r['y'][-1]
        if y and y[1] > 0: ani[u].append((s['k'], y[1], s['w']))
units = [g['properties']['u'] for g in J('units.json')['objects']['units']['geometries']]
n = 0
for u in units:
    sd, sg = u.split('|'); name = sd if sd == sg else sd + ' ' + sg
    a = sorted(ani.get(u, []), key=lambda x: -x[1])[:3]; e = AQ['units'].get(u); c = CR['units'].get(u)
    lines = []
    if a: lines.append(('동물농장  ' + ' · '.join(f'{k} {man(v)}{w}' for k, v, w in a), None))
    if e: lines.append(('어장  양식 면허 ' + f'{e["n"]:,}건' + (' · ' + ', '.join(t[0] for t in e['top'][:3]) if e['top'] else ''), None))
    if c: lines.append(('농장  ' + ', '.join(c['items'][:4]), None))
    if not lines: lines.append(('시군별 사육·양식·대표 품목 기록 정리', None))
    lines.append(('지도에서 보기 → 공판장·위판장·도매시장과 경락가', MOSS))
    card(os.path.join(OUT, 'p', f'{sd}_{sg}.png'), name, lines, tag='시군별'); n += 1
print('미리보기 그림', n + 4)
