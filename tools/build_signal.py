# 구매 신호(시험판) — 유통·가공·급식 업체용 「사 둘까, 미룰까」 품목별 값 방향 신호와 그 적중 기록
# 근거(열쇠 없이 지금 쓸 수 있는 것부터): 수협 위판 값의 달 안 흐름·앞달 대비, 수협 물류센터·조합창고 재고 증감, 7일 폐사 위험 예보
# 예측은 달마다 private/forecast/<자료 달>.json 으로 남기고, 다음 달 위판 값이 들어오면 자동으로 채점해 공개한다(적중 기록이 곧 상품의 신용).
# 경락가(축평원)·도매시장 정산이 열쇠로 들어오면 축산·농산 품목을 같은 틀로 붙인다.
import sys, os, re, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
WP = jload(os.path.join(DATA, 'wipan.json'), {}); SS = jload(os.path.join(DATA, 'seastock.json'), {}); RK = jload(os.path.join(DATA, 'risk.json'), {})
FD = os.path.join(PRIVATE, 'forecast'); os.makedirs(FD, exist_ok=True)
ALIAS = {'우렁쉥이': '멍게', '살오징어': '오징어', '피뿔고둥': '소라', '참굴': '굴', '흰베도라치': '실치', '민대구': '대구', '코다리': '명태', '명태포': '명태', '오징어포': '오징어'}
def base(n):
    n = re.sub(r'\(.*?\)', '', n or '').strip()
    n = re.sub(r'^기타', '', n); n = re.sub(r'류$', '', n)
    n = ALIAS.get(n, n)
    return n.strip()
if not WP.get('fish'):
    print('위판 자료 없음'); sys.exit(0)
month = WP['month']
# 위판 값: 기본 이름으로 묶음
g = collections.defaultdict(lambda: {'amt': 0, 'kg': 0, 'names': [], 'daily': collections.defaultdict(list), 'prev_amt': 0, 'prev_kg': 0})
for f in WP['fish']:
    b = base(f['name'])
    if not b or '해면' in b or b in ('기타',): continue
    x = g[b]; x['amt'] += f['amt']; x['kg'] += f['kg']; x['names'].append(f['name'])
    if len(x['names']) == 1:   # 달 안 흐름은 가장 많이 팔린 상태(활어·선어·냉동 중 하나)로만 — 상태가 섞이면 값이 튐
        for d, v in f.get('daily', []): x['daily'][d].append(v)
    if f.get('prev'): x['prev_amt'] += f['prev'] * f['kg']; x['prev_kg'] += f['kg']
stock = collections.defaultdict(list)
for k in ('center', 'coop'):
    for it in (SS.get(k) or {}).get('items', []):
        if it[3] is not None and it[1] >= 5000 and abs(it[3]) <= 300: stock[base(it[0])].append((k, it[3], it[2]))   # 달 초 재고가 아주 적으면 % 가 튀므로 뺌
risk = {base(s['sp']): s['lv'] for s in RK.get('species', [])}
items = []
for b, x in sorted(g.items(), key=lambda kv: -kv[1]['amt'])[:40]:
    if x['kg'] <= 0: continue
    wonkg = round(x['amt'] / x['kg'])
    ds = sorted(x['daily']); vals = [sum(x['daily'][d]) / len(x['daily'][d]) for d in ds]
    h = len(vals) // 2; trend = round((sum(vals[h:]) / len(vals[h:]) / (sum(vals[:h]) / len(vals[:h])) - 1) * 100, 1) if h >= 3 else None
    mom = round((wonkg / (x['prev_amt'] / x['prev_kg']) - 1) * 100, 1) if x['prev_kg'] else None
    st = stock.get(b, []); stc = round(sum(c for _, c, _ in st) / len(st), 1) if st else None
    sc = 0.0; why = []
    if stc is not None:
        if stc <= -15: sc += 1; why.append(f'창고 재고 {stc:+}%(물량 빠듯)')
        elif stc >= 15: sc -= 1; why.append(f'창고 재고 {stc:+}%(물량 쌓임)')
    if trend is not None:
        if trend >= 5: sc += 0.5; why.append(f'달 후반 값 {trend:+}%')
        elif trend <= -5: sc -= 0.5; why.append(f'달 후반 값 {trend:+}%')
    if mom is not None:
        if mom >= 10: sc += 0.5; why.append(f'앞달 대비 {mom:+}%')
        elif mom <= -10: sc -= 0.5; why.append(f'앞달 대비 {mom:+}%')
    rl = risk.get(b)
    if rl == '위험': sc += 1; why.append('폐사 위험 예보(공급 줄 수 있음)')
    elif rl == '주의': sc += 0.5; why.append('고수온 주의 예보')
    d = '오름 쪽' if sc >= 1 else '내림 쪽' if sc <= -1 else '보합'
    act = {'오름 쪽': '지금 사 두기·재고 늘리기 검토', '내림 쪽': '구매 미루기·재고 줄이기 검토', '보합': '평소대로'}[d]
    items.append({'item': b, 'names': x['names'][:4], 'wonkg': wonkg, 'amt': x['amt'], 'trend': trend, 'mom': mom, 'stock': stc, 'risk': rl, 'score': sc, 'dir': d, 'act': act, 'why': why})
# 예측 기록(자료 달 기준 한 번) + 채점
fp = os.path.join(FD, month + '.json')
if not os.path.exists(fp):
    jsave(fp, {'made': stamp(), 'month': month, 'items': [{k: i[k] for k in ('item', 'wonkg', 'dir', 'score')} for i in items]})
score = {'months': [], 'n': 0, 'hit': 0}
for f in sorted(os.listdir(FD)):
    if not f.endswith('.json') or f[:7] >= month: continue
    old = jload(os.path.join(FD, f), {}); cur = {i['item']: i['wonkg'] for i in items}
    n = hit = 0; rows = []
    for i in old.get('items', []):
        if i['item'] not in cur or not i['wonkg']: continue
        chg = (cur[i['item']] / i['wonkg'] - 1) * 100
        real = '오름 쪽' if chg >= 3 else '내림 쪽' if chg <= -3 else '보합'
        ok = real == i['dir'] or (i['dir'] == '보합' and abs(chg) < 5)
        n += 1; hit += ok; rows.append([i['item'], i['dir'], round(chg, 1), ok])
    if n: score['months'].append({'month': f[:7], 'to': month, 'n': n, 'hit': hit, 'rows': rows}); score['n'] += n; score['hit'] += hit
out = {'at': stamp(), 'month': month, 'horizon': '다음 달 수협 산지 위판 ㎏당 값', 'items': items, 'score': score,
       'basis': '수협 산지 위판(해양수산부 위탁판매 현황) · 수협 물류센터·조합창고 재고 · 7일 폐사 위험 예보'}
jsave(os.path.join(DATA, 'buysignal.json'), out)
c = collections.Counter(i['dir'] for i in items)
status('buysignal', True, f'{month} 기준 {len(items)}품목 · 오름 {c["오름 쪽"]} · 내림 {c["내림 쪽"]} · 채점 {score["n"]}건')
print('구매 신호', month, dict(c), score['n'])
