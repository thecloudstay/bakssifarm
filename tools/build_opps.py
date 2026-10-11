# 수급 기회 — 수요·공급이 어긋나는 곳을 찾아 유통·가공·급식 업체에 「여기서 사라 / 지금 사들여라 / 이걸로 바꿔라」로 추천
#  1) 산지 간 값 차이: 같은 어종인데 조합마다 ㎏당 값이 크게 다른 곳(싸게 사는 산지)
#  2) 공급 넘침: 창고 재고가 쌓이고 물량은 늘고 값은 내리는 품목(싸게 사들일·판촉할 기회)
#  3) 공급 빠듯: 재고가 줄고 값이 오르거나 폐사 위험이 있는 품목(미리 확보하거나 대체 품목으로)
#  4) 어족(자연산 어획): 어디서·무슨 어업으로 잡히고, 달 안·앞달 대비 물량이 어떻게 움직이나
#  5) 자연산과 양식 값 차이: 같은 어종의 자연산·양식 ㎏당 값 차이(대체 구매 기회)
# 결과: site/data/opps.json. 개별 거래처·농어가는 없음(조합 단위 공개 위판 집계만).
import sys, os, re, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
WP = jload(os.path.join(DATA, 'wipan.json'), {}); SS = jload(os.path.join(DATA, 'seastock.json'), {}); RK = jload(os.path.join(DATA, 'risk.json'), {})
if not WP.get('fish'): print('위판 자료 없음'); sys.exit(0)
ALIAS = {'우렁쉥이': '멍게', '살오징어': '오징어', '피뿔고둥': '소라', '참굴': '굴', '흰베도라치': '실치', '민대구': '대구', '코다리': '명태', '명태포': '명태', '오징어포': '오징어'}
def base(n):
    n = re.sub(r'\(.*?\)', '', n or '').strip(); n = re.sub(r'^기타', '', n); n = re.sub(r'류$', '', n)
    return ALIAS.get(n, n).strip()
SUB = {'방어': ['부시리', '참치'], '오징어': ['갑오징어', '한치', '화살꼴뚜기'], '갈치': ['삼치', '병어'], '고등어': ['전갱이', '삼치', '꽁치'], '넙치': ['조피볼락', '참돔', '숭어'],
       '조피볼락': ['넙치', '참돔', '숭어'], '참돔': ['감성돔', '넙치'], '꽃게': ['민꽃게', '대게'], '멸치': ['까나리'], '전복': ['소라', '키조개'], '문어': ['낙지', '주꾸미'],
       '명태': ['대구', '가자미'], '대구': ['명태', '가자미'], '민어': ['농어', '참돔'], '병어': ['덕대', '갈치'], '굴': ['홍합', '가리비'], '멍게': ['미더덕']}
cname = lambda c: c.replace('수산업협동조합', '수협')
coop_u = {c['name']: c.get('u') for c in WP.get('coops', [])}
def trend(series):
    v = [x[1] for x in series if x[1]]; h = len(v) // 2
    return round((sum(v[h:]) / len(v[h:]) / (sum(v[:h]) / len(v[:h])) - 1) * 100, 1) if h >= 3 and sum(v[:h]) > 0 else None
stock = collections.defaultdict(list)
for k in ('center', 'coop'):
    for it in (SS.get(k) or {}).get('items', []):
        if it[3] is not None and it[1] >= 5000 and abs(it[3]) <= 300: stock[base(it[0])].append(it[3])
risk = {base(s['sp']): s['lv'] for s in RK.get('species', [])}
fish = sorted(WP['fish'], key=lambda f: -f['amt'])[:70]
# 1) 산지 간 값 차이
spread = []
for f in fish:
    avg = f.get('wonkg')
    if not avg: continue
    ok = [b for b in f.get('by', []) if len(b) > 3 and b[3] >= 3000 and b[1] and avg * 0.4 <= b[1] <= avg * 2.5]   # 평균의 40% 아래·2.5배 위는 규격·단위 차이로 보고 뺌
    if len(ok) < 3: continue
    cheap = sorted([b for b in ok if b[1] <= avg * 0.85], key=lambda b: b[1])
    if not cheap: continue
    hi = max(ok, key=lambda b: b[1])
    save = sum((avg - b[1]) * b[3] for b in cheap[:3])
    spread.append({'fish': f['name'], 'avg': avg, 'cheap': [[cname(b[0]), b[1], b[3], round((1 - b[1] / avg) * 100)] for b in cheap[:3]], 'high': [cname(hi[0]), hi[1]], 'save': round(save), 'coops': len(ok)})
spread.sort(key=lambda x: -x['save'])
# 2)·3) 공급 넘침·빠듯
glut, tight = [], []
seen = set()
for f in fish:
    b = base(f['name'])
    if b in seen or not b or '해면' in b: continue
    seen.add(b)
    pt = trend(f.get('daily', [])); kt = trend(f.get('daily_kg', [])); st = round(sum(stock[b]) / len(stock[b]), 1) if stock.get(b) else None
    why = []; g = t = 0
    if st is not None and st >= 15: g += 1; why.append(f'창고 재고 {st:+}%')
    if st is not None and st <= -15: t += 1; why.append(f'창고 재고 {st:+}%')
    if kt is not None and kt >= 20: g += 0.5; why.append(f'달 후반 위판 물량 {kt:+}%')
    if kt is not None and kt <= -20: t += 0.5; why.append(f'달 후반 위판 물량 {kt:+}%')
    if pt is not None and pt <= -5: g += 0.5; why.append(f'달 후반 값 {pt:+}%')
    if pt is not None and pt >= 5: t += 0.5; why.append(f'달 후반 값 {pt:+}%')
    if f.get('chg') is not None and f['chg'] >= 10: t += 0.5; why.append(f'앞달 대비 값 {f["chg"]:+}%')
    if f.get('chg') is not None and f['chg'] <= -10: g += 0.5; why.append(f'앞달 대비 값 {f["chg"]:+}%')
    if risk.get(b) in ('위험', '주의'): t += 1 if risk[b] == '위험' else 0.5; why.append(f'폐사 {risk[b]} 예보')
    row = {'item': b, 'name': f['name'], 'wonkg': f['wonkg'], 'amt': f['amt'], 'why': why, 'sub': [s for s in SUB.get(b, [])]}
    if pt is not None and pt > 5: g = 0      # 값이 오르는데 넘친다고 하지 않음
    if pt is not None and pt < -5: t = 0     # 값이 내리는데 빠듯하다고 하지 않음
    if g >= 1 and g > t: glut.append(dict(row, score=g, act='싸게 사들여 냉동·가공 재고로 두거나 판촉 품목으로'))
    elif t >= 1 and t > g:
        subs = []
        for s in row['sub']:
            sf = next((x for x in WP['fish'] if base(x['name']) == s), None)
            if sf: subs.append([s, sf['wonkg']])
        tight.append(dict(row, score=t, act='필요 물량 미리 확보, 또는 대체 품목으로', subs=subs))
glut.sort(key=lambda x: (-x['score'], -x['amt'])); tight.sort(key=lambda x: (-x['score'], -x['amt']))
# 4) 어족(자연산)
wild = []
for f in sorted(WP['fish'], key=lambda f: -(f.get('wild_kg') or 0))[:25]:
    if not f.get('wild_kg'): continue
    where = collections.Counter()
    for c, q in f.get('wild_where', []):
        u = coop_u.get(c); where[(u.split('|')[0] if u else cname(c))] += q
    wild.append({'name': f['name'], 'kg': f['wild_kg'], 'wonkg': round(f['wild_amt'] / f['wild_kg']) if f.get('wild_kg') else None, 'gear': f.get('gear', [])[:3],
                 'where': [[k, v] for k, v in where.most_common(4)], 'kg_trend': trend(f.get('daily_kg', [])), 'wild_chg': f.get('wild_chg')})
# 5) 자연산 대 양식
wf = []
FARMED = {'넙치', '조피볼락', '참돔', '숭어', '농어', '전복', '멍게', '굴', '홍합', '가리비', '뱀장어', '돌돔', '능성어', '강도다리', '가자미', '쥐치', '방어', '해삼', '새우', '꼬막', '감성돔', '볼락'}
for f in WP['fish']:
    if base(f['name']) not in FARMED: continue
    if (f.get('wild_kg') or 0) >= 3000 and (f.get('farm_kg') or 0) >= 3000:
        a = f['wild_amt'] / f['wild_kg']; b = f['farm_amt'] / f['farm_kg']
        if not (1 / 3 <= a / b <= 3): continue   # 세 배 넘게 벌어지면 규격·업종 기록 차이로 보고 뺌
        wf.append({'name': f['name'], 'wild': round(a), 'farm': round(b), 'gap': round((a / b - 1) * 100), 'wild_kg': f['wild_kg'], 'farm_kg': f['farm_kg']})
wf.sort(key=lambda x: -abs(x['gap']))
out = {'at': stamp(), 'month': WP['month'], 'spread': spread[:15], 'glut': glut[:12], 'tight': tight[:12], 'wild': wild, 'wildfarm': wf[:12],
       'basis': '해양수산부 일자별 위탁판매 현황(수협 산지 위판) · 수협 물류센터·조합창고 재고 · 7일 폐사 위험 예보'}
jsave(os.path.join(DATA, 'opps.json'), out)
status('opps', True, f'{WP["month"]} 산지 값 차이 {len(spread)} · 넘침 {len(glut)} · 빠듯 {len(tight)} · 자연산 {len(wild)}')
print('수급 기회', len(spread), len(glut), len(tight), len(wild), len(wf))
