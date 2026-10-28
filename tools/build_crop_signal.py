# 농산물 구매 신호·도매시장 간 값 차이 — 공영도매시장 정산(날짜별 품목 ㎏당 값·물량, private/wholesale)으로
#  1) 신호(거래일 10일 이상 쌓이면): 최근 5거래일 값·물량을 앞 15거래일과 비교 → 앞으로 2주 도매가가 오를 쪽/내릴 쪽
#     값 흐름 ±5% → ±0.5, 반입 물량 ±15%(줄면 오를 쪽) → ±0.5, 둘 다 같은 쪽이면 신호. 월요일마다 예측을 남기고 14일 뒤 자동 채점.
#  2) 도매시장 간 값 차이(하루치로 바로): 같은 품목인데 도매시장마다 ㎏당 값이 크게 다른 곳 → 유통업체 「여기서 사라」
# 결과: site/data/cropsignal.json
import sys, os, json, glob, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from world_lib import world_adjust
HD = os.path.join(PRIVATE, 'wholesale'); FD = os.path.join(PRIVATE, 'forecast'); os.makedirs(FD, exist_ok=True)
WH = jload(os.path.join(DATA, 'price', 'wholesale.json'), {})
days = sorted(glob.glob(os.path.join(HD, '*.json')))
hist = [(os.path.basename(p)[:10], jload(p, {})) for p in days]
# 반쪽 장날(토요일 등 일부 도매시장만 연 날)은 물량이 적어 「공급 줄어듦」으로 잘못 읽히므로 뺌 — 하루 거래 금액이 중앙값의 60% 아래면 제외
if hist:
    tots = sorted(sum((v[2] or 0) for v in d.values()) for _, d in hist); med = tots[len(tots) // 2]
    hist = [(k, d) for k, d in hist if sum((v[2] or 0) for v in d.values()) >= med * 0.6]
out = {'at': stamp(), 'date': WH.get('date'), 'ndays': len(hist), 'items': [], 'spread': [], 'score': {'n': 0, 'hit': 0, 'rows': []},
       'basis': '한국농수산식품유통공사 전국 공영도매시장 정산정보(26곳, 거래일마다)', 'horizon': '앞으로 2주 공영도매시장 ㎏당 값'}
def avg(vals): vals = [v for v in vals if v]; return sum(vals) / len(vals) if vals else None
# 1) 신호(온전한 거래일 10일 이상)
if len(hist) >= 10:
    recent, prior = hist[-5:], hist[-20:-5]
    tot = collections.Counter()
    for _, d in recent:
        for k, v in d.items(): tot[k] += v[2] or 0
    for k, _ in tot.most_common(50):
        pr = avg([d.get(k, [None])[0] for _, d in recent]); pp = avg([d.get(k, [None])[0] for _, d in prior])
        qr = avg([d.get(k, [0, 0])[1] for _, d in recent]); qp = avg([d.get(k, [0, 0])[1] for _, d in prior])
        if not pr or not pp or not qp or qr is None: continue
        pt = round((pr / pp - 1) * 100, 1); qt = round((qr / qp - 1) * 100, 1)
        sc = 0.0; why = []
        if pt >= 5: sc += 0.5; why.append(f'최근 5거래일 값 {pt:+}%')
        elif pt <= -5: sc -= 0.5; why.append(f'최근 5거래일 값 {pt:+}%')
        if qt <= -15: sc += 0.5; why.append(f'반입 물량 {qt:+}%(공급 줄어듦)')
        elif qt >= 15: sc -= 0.5; why.append(f'반입 물량 {qt:+}%(공급 늘어남)')
        wd, wwhy, wids = world_adjust('농산', k)   # 2026-10-28 세계 요인 — 갈래 상한 ±0.5
        if wd: sc += wd; why += wwhy
        dr = '오름 쪽' if sc >= 1 else '내림 쪽' if sc <= -1 else '보합'
        out['items'].append({'item': k, 'wonkg': round(pr), 'pt': pt, 'qt': qt, 'score': sc, 'dir': dr, 'why': why, 'world': wd,
                             'act': {'오름 쪽': '필요 물량 앞당겨 확보 검토', '내림 쪽': '구매 미루기·소량 나눠 사기 검토', '보합': '평소대로'}[dr]})
    today = now().date()
    fp = os.path.join(FD, f'crop-{today.isoformat()}.json')
    if today.weekday() == 0 and not os.path.exists(fp):
        jsave(fp, {'made': stamp(), 'items': [{k: i[k] for k in ('item', 'wonkg', 'dir')} for i in out['items']]})
    cur = {i['item']: i['wonkg'] for i in out['items']}
    for p in sorted(glob.glob(os.path.join(FD, 'crop-*.json'))):
        dd = datetime.date.fromisoformat(os.path.basename(p)[5:15])
        if (today - dd).days < 14: continue
        for i in jload(p, {}).get('items', []):
            if i['item'] not in cur or not i['wonkg']: continue
            chg = (cur[i['item']] / i['wonkg'] - 1) * 100
            real = '오름 쪽' if chg >= 3 else '내림 쪽' if chg <= -3 else '보합'
            ok = real == i['dir'] or (i['dir'] == '보합' and abs(chg) < 5)
            out['score']['n'] += 1; out['score']['hit'] += ok; out['score']['rows'].append([dd.isoformat(), i['item'], i['dir'], round(chg, 1), ok])
# 2) 도매시장 간 값 차이(물량 큰 곳만, 평균의 40~250% 안)
for it in WH.get('items', [])[:60]:
    avgp = it.get('won_kg'); mk = [m for m in it.get('markets', []) if m[1] and m[2] >= 5_000_000 and avgp and avgp * 0.4 <= m[1] <= avgp * 2.5]
    if not avgp or len(mk) < 3: continue
    cheap = sorted([m for m in mk if m[1] <= avgp * 0.85], key=lambda m: m[1])
    if not cheap: continue
    hi = max(mk, key=lambda m: m[1])
    out['spread'].append({'item': it['item'], 'avg': avgp, 'cheap': [[m[0], m[1], round((1 - m[1] / avgp) * 100)] for m in cheap[:3]], 'high': [hi[0], hi[1]], 'gap': round((hi[1] / cheap[0][1] - 1) * 100), 'n': len(mk)})
out['spread'].sort(key=lambda x: -x['gap'])
jsave(os.path.join(DATA, 'cropsignal.json'), out)
c = collections.Counter(i['dir'] for i in out['items'])
status('cropsignal', True, f'거래일 {len(hist)}일 · 신호 {len(out["items"])}품목(오름 {c["오름 쪽"]} · 내림 {c["내림 쪽"]}) · 도매시장 간 값 차이 {len(out["spread"])} · 채점 {out["score"]["n"]}')
print('농산물 신호', len(hist), dict(c), len(out['spread']))
