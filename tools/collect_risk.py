# 수급 위험 예보 — 앞으로 7일 수온·기온·습도 예보로 양식 폐사·가축 더위(추위) 피해 위험을 시군·품종별로 매기고,
# 피해가 나면 움직일 공급·값(위판 시세·재고)을 함께 붙인다. 열쇠 불필요(오픈메테오 공개 예보).
#  · 바다: 시군별 양식 면허 구역 가운데의 바다 표면 수온(시간별 → 하루 최고·최저) × 품종별 한계 수온
#  · 육지: 시군 중심의 하루 최고·최저 기온과 평균 습도 → 가축 더위지수(온습도지수) × 축종별 사육 두수
#  · 매일 예보를 private/risk/날짜.json 으로 쌓아 두었다가 실제 위판 값·폐사 신고와 맞춰 보는 자료로 씀(예보 기록 자체가 자산)
# 결과: site/data/risk.json, 그리고 경고 이상은 site/data/signals.json 에 「예보」로 덧붙임
import sys, os, json, datetime, collections, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
PTS = jload(os.path.join(ROOT, 'tools', 'risk_points.json'), {'land': {}, 'sea': {}})
AQ = jload(os.path.join(DATA, 'aqua.json'), {'species': []}); LS = jload(os.path.join(DATA, 'livestock.json'), {'species': []})
WP = jload(os.path.join(DATA, 'wipan.json'), {}); SST = jload(os.path.join(DATA, 'seastock.json'), {})
# 품종별 참고 한계 수온(℃): (고수온 주의, 고수온 위험, 저수온 주의, 저수온 위험) — 국립수산과학원 고수온·저수온 특보 기준과 품종별 적정 수온 자료를 박씨팜이 정리한 참고값
SEA_TH = {'조피볼락': (25, 27, 5, 3), '넙치': (26, 28, 7, 5), '참돔': (27, 29, 10, 8), '방어': (26, 28, 11, 9), '숭어': (28, 30, 4, 2), '농어': (27, 29, 6, 4), '볼락': (25, 27, 6, 4),
          '어류': (26, 28, 7, 4), '전복': (25, 27, 8, 5), '멍게': (24, 26, None, None), '미더덕': (25, 27, None, None), '해삼': (25, 28, None, None), '가리비': (23, 25, None, None),
          '굴': (26, 28, None, None), '홍합': (25, 27, None, None), '피조개': (26, 28, None, None), '키조개': (26, 28, None, None), '새우': (30, 32, 12, 10), '성게': (24, 26, None, None)}
OFFICIAL = '국립수산과학원 특보: 고수온 예비특보 25℃, 주의보 28℃, 경보 28℃ 3일 이상 · 저수온 주의보 4℃, 경보 4℃ 3일 이상'
WP_NAME = {'조피볼락': '조피볼락(활어)', '넙치': '넙치(활어)', '참돔': '참돔(활어)', '방어': '방어(활어)', '숭어': '숭어(활어)', '농어': '농어(활어)', '전복': '전복(활어)', '멍게': '우렁쉥이(활어)',
           '굴': '굴(활어)', '홍합': '홍합(활어)', '가리비': '가리비(활어)', '해삼': '해삼(활어)', '새우': '기타새우류(활어)', '볼락': '볼락(활어)'}
# 가축 더위지수 단계(국립축산과학원 가축 더위지수 안내 바탕): 72 주의 · 79 경고 · 89 위험
THI_ST = [(89, '위험'), (79, '경고'), (72, '주의')]
LS_GROUP = {'소': ['한우', '젖소', '육우'], '돼지': ['일반돼지', '종돈', '흑돼지'], '닭': ['육계', '산란계', '토종닭', '백세미', '육용종계', '산란종계', '산란중추', '토종종계'], '오리': ['육용오리', '종오리', '산란오리', '일반오리']}
LV = {'': 0, '주의': 1, '경고': 2, '위험': 3}
def chunks(xs, n):
    for i in range(0, len(xs), n): yield xs[i:i + n]
def om(base, params):
    j = json.loads(get(base, params, headers={'User-Agent': 'bakssifarm/1.0'}))
    return j if isinstance(j, list) else [j]
today = now().date()
out = {'at': stamp(), 'official': OFFICIAL, 'source': '오픈메테오 공개 예보(바다 표면 수온·기온·습도, 7일) × 국립해양조사원 어장정보도 · 가축위생방역지원본부 사육 규모 · 해양수산부 위판·재고', 'sea': {}, 'land': {}}
try:
    # ── 바다
    keys = [u for u in PTS['sea']]
    for ks in chunks(keys, 40):
        res = om('https://marine-api.open-meteo.com/v1/marine', {'latitude': ','.join(str(PTS['sea'][u][0]) for u in ks), 'longitude': ','.join(str(PTS['sea'][u][1]) for u in ks),
                 'hourly': 'sea_surface_temperature', 'timezone': 'Asia/Seoul', 'forecast_days': 7, 'past_days': 2})
        for u, r in zip(ks, res):
            h = r.get('hourly') or {}; t = h.get('time') or []; v = h.get('sea_surface_temperature') or []
            day = collections.defaultdict(list)
            for a, b in zip(t, v):
                if b is not None: day[a[:10]].append(b)
            if not day: continue
            ds = sorted(day); mx = [round(max(day[d]), 1) for d in ds]; mn = [round(min(day[d]), 1) for d in ds]
            out['sea'][u] = {'days': [d[5:] for d in ds], 'max': mx, 'min': mn}
    fut = lambda d: d >= today.strftime('%m-%d')
    for u, s in out['sea'].items():
        idx = [i for i, d in enumerate(s['days']) if fut(d)]
        hi = max(s['max'][i] for i in idx) if idx else None; lo = min(s['min'][i] for i in idx) if idx else None
        sp = [(x['k'], x['units'][u]) for x in AQ['species'] if u in x['units'] and x['k'] in SEA_TH]
        risks = []
        for k, (n, ha) in sp:
            th = SEA_TH[k]; lv = ''; why = ''
            hd = sum(1 for i in idx if s['max'][i] >= th[1]); hw = sum(1 for i in idx if s['max'][i] >= th[0])
            ld = sum(1 for i in idx if th[3] is not None and s['min'][i] <= th[3]); lw = sum(1 for i in idx if th[2] is not None and s['min'][i] <= th[2])
            # 위험은 한계 수온을 이틀 이상 넘을 때(특보 「경보」가 사흘 지속을 보는 것과 같은 뜻), 주의는 하루라도 주의 수온에 닿을 때
            if hd >= 2: lv, why = '위험', f'{th[1]}℃ 이상 {hd}일(최고 {hi}℃)'
            elif hw >= 1: lv, why = '주의', f'{th[0]}℃ 이상 {hw}일(최고 {hi}℃)'
            if ld >= 2: lv, why = '위험', f'{th[3]}℃ 이하 {ld}일(최저 {lo}℃)'
            elif lw >= 1 and LV[lv] < 1: lv, why = '주의', f'{th[2]}℃ 이하 {lw}일(최저 {lo}℃)'
            day1 = next((s['days'][i] for i in idx if (th[1] and s['max'][i] >= th[0]) or (th[2] is not None and s['min'][i] <= th[2])), None)
            risks.append({'sp': k, 'lv': lv, 'why': why, 'n': n, 'ha': ha, 'from': day1})
        s.update({'hi': hi, 'lo': lo, 'risks': sorted(risks, key=lambda r: (-LV[r['lv']], -r['ha'])),
                  'lv': max((r['lv'] for r in risks), key=lambda x: LV[x], default=''),
                  'official': '경보 수준' if hi is not None and hi >= 28 else '주의보 수준' if hi is not None and hi >= 25 else '저수온 주의보 수준' if lo is not None and lo <= 4 else ''})
    # ── 육지
    keys = list(PTS['land'])
    heads = {u: {g: 0 for g in LS_GROUP} for u in keys}
    for sp in LS['species']:
        g = next((g for g, ks in LS_GROUP.items() if sp['k'] in ks), None)
        if not g: continue
        for u, r in sp['d'].items():
            y = r['y'][-1] if r.get('y') else None
            if u in heads and y: heads[u][g] += y[1] or 0
    for ks in chunks(keys, 50):
        res = om('https://api.open-meteo.com/v1/forecast', {'latitude': ','.join(str(PTS['land'][u][0]) for u in ks), 'longitude': ','.join(str(PTS['land'][u][1]) for u in ks),
                 'daily': 'temperature_2m_max,temperature_2m_min,relative_humidity_2m_min', 'timezone': 'Asia/Seoul', 'forecast_days': 7})
        for u, r in zip(ks, res):
            d = r.get('daily') or {}; tx = d.get('temperature_2m_max') or []; tn = d.get('temperature_2m_min') or []; rh = d.get('relative_humidity_2m_min') or []   # 낮 최고 기온 때는 습도가 가장 낮으므로 최저 습도와 짝지음
            if not tx: continue
            thi = [round((1.8 * a + 32) - (0.55 - 0.0055 * (h or 60)) * (1.8 * a - 26), 1) if a is not None else None for a, h in zip(tx, rh)]
            mt = max((x for x in thi if x is not None), default=None); mn = min((x for x in tn if x is not None), default=None)
            lv = next((n for t, n in THI_ST if mt is not None and mt >= t), '')
            cold = '경고' if mn is not None and mn <= -15 else '주의' if mn is not None and mn <= -10 else ''
            out['land'][u] = {'days': [x[5:] for x in d.get('time', [])], 'tmax': tx, 'tmin': tn, 'rh': rh, 'thi': thi, 'thi_max': mt, 'tmin_min': mn,
                              'lv': lv if LV[lv] >= LV[cold] else cold, 'kind': '더위' if lv and LV[lv] >= LV[cold] else '추위' if cold else '', 'heads': heads.get(u, {})}
    # ── 묶음: 품종별 위험 해역·노출 면적, 축종별 노출 두수, 값 움직임 근거
    sp_sum = collections.defaultdict(lambda: {'units': [], 'ha': 0.0, 'lv': ''})
    for u, s in out['sea'].items():
        for r in s.get('risks', []):
            if r['lv']:
                x = sp_sum[r['sp']]; x['units'].append(u); x['ha'] += r['ha']
                if LV[r['lv']] > LV[x['lv']]: x['lv'] = r['lv']
    fishmap = {f['name']: f for f in WP.get('fish', [])}
    out['species'] = sorted([{'sp': k, 'lv': v['lv'], 'units': v['units'], 'ha': round(v['ha'], 1),
                              'price': ({'name': WP_NAME.get(k), 'wonkg': fishmap[WP_NAME[k]]['wonkg'], 'chg': fishmap[WP_NAME[k]].get('chg'), 'month': WP.get('month')} if WP_NAME.get(k) in fishmap else None)}
                             for k, v in sp_sum.items()], key=lambda x: (-LV[x['lv']], -x['ha']))
    ls_sum = {g: {'주의': 0, '경고': 0, '위험': 0} for g in LS_GROUP}
    for u, l in out['land'].items():
        if l['lv']:
            for g, n in l['heads'].items():
                if n: ls_sum[g][l['lv']] += n
    out['livestock'] = ls_sum
    out['stock'] = [i for i in (SST.get('center') or {}).get('items', [])[:8]]
    out['summary'] = {'sea_units': sum(1 for s in out['sea'].values() if s.get('lv')), 'sea_danger': sum(1 for s in out['sea'].values() if s.get('lv') == '위험'),
                      'land_units': sum(1 for l in out['land'].values() if l.get('lv')), 'land_danger': sum(1 for l in out['land'].values() if l.get('lv') in ('경고', '위험'))}
    jsave(os.path.join(DATA, 'risk.json'), out)
    jsave(os.path.join(PRIVATE, 'risk', today.isoformat() + '.json'), {'at': out['at'], 'sea': {u: {k: s.get(k) for k in ('days', 'max', 'min', 'lv')} for u, s in out['sea'].items()},
                                                                       'land': {u: {k: l.get(k) for k in ('days', 'tmax', 'tmin', 'thi', 'lv')} for u, l in out['land'].items()}})
    # 이상 신호에 「예보」 덧붙이기(경고·위험만, 같은 날 다시 돌면 바꿔 끼움)
    sg = jload(os.path.join(DATA, 'signals.json'), {'items': []}); items = [i for i in sg.get('items', []) if i.get('src') != 'risk']
    for u, s in out['sea'].items():
        top = [r for r in s.get('risks', []) if r['lv'] == '위험']
        if top: items.append({'date': today.isoformat(), 'level': '경고', 'kind': '예보·수온', 'area': u, 'src': 'risk',
                              'title': f'{u.replace("|", " ")} {", ".join(r["sp"] for r in top[:3])} 폐사 위험(7일 예보)', 'body': f'{top[0]["why"]}. 양식 면허 {sum(r["n"] for r in top)}건.'})
    for u, l in out['land'].items():
        if l['lv'] in ('경고', '위험'):
            h = l['heads']; items.append({'date': today.isoformat(), 'level': '경고' if l['lv'] == '경고' else '위험', 'kind': '예보·' + l['kind'], 'area': u, 'src': 'risk',
                                          'title': f'{u.replace("|", " ")} 가축 {l["kind"]} {l["lv"]}(7일 예보)', 'body': (f'더위지수 최고 {l["thi_max"]}' if l['kind'] == '더위' else f'최저 {l["tmin_min"]}℃') + f'. 소 {h.get("소", 0):,} · 돼지 {h.get("돼지", 0):,} · 닭 {h.get("닭", 0):,}'})
    sg['items'] = items; jsave(os.path.join(DATA, 'signals.json'), sg)
    status('risk', True, f'바다 {len(out["sea"])}곳 · 육지 {len(out["land"])}곳 · 위험 해역 {out["summary"]["sea_units"]} · 가축 경고 {out["summary"]["land_danger"]}')
    print('수급 위험 예보', out['summary'])
except Exception as e:
    status('risk', False, str(e)[:200]); print('실패', e)
