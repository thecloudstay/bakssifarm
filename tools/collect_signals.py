# 이상 신호 모으기: 고수온·저수온(해루낚 실측 수온, 열쇠 불필요) · 경락가 급등락(축평원 이력) · 가축전염병(재난안전데이터 열쇠 있을 때)
# 결과: site/data/signals.json = {at, items:[{date, level, kind, title, body, area, src}]}
import sys, os, json, datetime, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
items = []
today = now().date()
# 1) 수온 — 해루낚이 매시간 올리는 국립해양조사원 조위관측소 실측(수온 tw)
try:
    obs = json.loads(get('https://haerunak.com/data/obs.json'))
    # 2026-10-21 해루낚이 매시간 파일을 새로 올리는 틈에 받으면 관측소가 0곳으로 옴(10월 14·21일) → 1분 간격으로 두 번 더 받아 봄
    import time
    for _ in range(2):
        if obs.get('s'): break
        time.sleep(60); obs = json.loads(get('https://haerunak.com/data/obs.json'))
    sts = {s['code']: s for s in json.loads(get('https://haerunak.com/data/tide-stations.json'))['stations']}
    units = json.load(open(os.path.join(DATA, 'units.json'), encoding='utf-8'))
    # 시군 중심(경계 상자 가운데)으로 가장 가까운 시군 찾기
    import math
    def centers():
        out = []
        for g in units['objects']['units']['geometries']:
            arcs = g['arcs']; xs = []; ys = []
            def walk(a):
                for x in a:
                    if isinstance(x, list): walk(x)
                    else:
                        idx = x if x >= 0 else ~x
                        for p in decoded[idx]: xs.append(p[0]); ys.append(p[1])
            walk(arcs); out.append((g['properties']['u'], (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2))
        return out
    sc = units['transform']['scale']; tr = units['transform']['translate']; decoded = []
    for arc in units['arcs']:
        x = y = 0; pts = []
        for d in arc: x += d[0]; y += d[1]; pts.append((x * sc[0] + tr[0], y * sc[1] + tr[1]))
        decoded.append(pts)
    CT = centers()
    def nearest(lo, la): return min(CT, key=lambda c: (c[1] - lo) ** 2 + (c[2] - la) ** 2)[0]
    def unit_for(st):
        nm = st['name']
        for u, _, _ in CT:
            sg = u.split('|')[1]
            if sg == nm or sg.rstrip('시군') == nm or (u.split('|')[0] == nm and u.split('|')[0] == sg): return u
        return nearest(st['lo'], st['la'])
    for code, r in obs.get('s', {}).items():
        tw = r.get('tw'); st = sts.get(code)
        if tw is None or tw <= 0.5 or not st: continue   # 0℃는 결측으로 봄
        u = unit_for(st)
        if tw >= 28: items.append({'date': today.isoformat(), 'level': '경보' if tw >= 30 else '주의', 'kind': '고수온', 'title': f'{st["name"]} 앞바다 수온 {tw}℃', 'body': '고수온 주의 기준(28℃) 이상. 양식장은 사료 줄이기·산소 공급·출하 앞당기기 검토, 폐사 늘면 위판 가격이 흔들립니다.', 'area': u, 'src': '국립해양조사원 조위관측소 실측(해루낚 보관) ' + str(r.get('at', ''))})
        elif tw <= 4: items.append({'date': today.isoformat(), 'level': '주의', 'kind': '저수온', 'title': f'{st["name"]} 앞바다 수온 {tw}℃', 'body': '저수온 주의 기준(4℃) 이하. 넙치·돔류 양식장은 가온·먹이 조절, 폐사 대비.', 'area': u, 'src': '국립해양조사원 조위관측소 실측(해루낚 보관) ' + str(r.get('at', ''))})
    if not obs.get('s'): print('수온 원본 형식 확인:', type(obs).__name__, list(obs)[:10] if isinstance(obs, dict) else len(obs), str(obs)[:300])   # 관측소 0곳이면 원본 모양을 기록에 남김
    status('signals_sea', True if obs.get('s') else False, f'관측소 {len(obs.get("s", {}))}곳 · 수온 신호 {sum(1 for i in items if i["kind"] in ("고수온", "저수온"))}건')
except Exception as e:
    status('signals_sea', False, str(e)[:160])
# 2) 경락가 급등락 — 최근 거래일 대비 중위값(직전 5거래일)에서 ±5% 넘게 벗어나면
try:
    hd = os.path.join(DATA, 'price', 'history')
    files = sorted(os.listdir(hd)) if os.path.isdir(hd) else []
    if len(files) >= 3:
        hist = [jload(os.path.join(hd, f)) for f in files[-6:]]
        last = hist[-1]; prev = hist[:-1]
        for sec in last.get('ekape', []):
            for r in sec['rows']:
                # 2026-10-20 두수가 적은 등급(예: 4두)은 한두 마리 값에 휘둘려 헛경보가 난다 → 20두 미만은 건너뜀
                if (r.get('n') or 0) < 20: continue
                ps = [x['p'] for h in prev for s2 in h.get('ekape', []) if s2['title'] == sec['title'] for x in s2['rows'] if x['g'] == r['g']]
                if len(ps) < 2: continue
                m = statistics.median(ps); ch = r['p'] / m - 1
                if abs(ch) >= 0.05:
                    items.append({'date': last.get('date', today.isoformat()), 'level': '경보' if abs(ch) >= 0.1 else '주의', 'kind': '가격 급등' if ch > 0 else '가격 급락', 'title': f'{sec["title"]} {r["g"]} {r["p"]:,}원/㎏ ({ch * 100:+.1f}%)', 'body': f'직전 {len(ps)}거래일 중위값 {m:,.0f}원 대비({r.get("n")}두). 출하 시점을 다시 보세요.', 'area': '전국', 'src': '축산물품질평가원 등급별 경락가'})
        status('signals_price', True, f'{len(files)}일치 비교')
    else:
        status('signals_price', None, '경락가 이력 3일 미만')
except Exception as e:
    status('signals_price', False, str(e)[:160])
# 3) 가축전염병 — 재난안전데이터 공유플랫폼 열쇠(SAFETYDATA_KEY)가 있을 때. 끝점은 열쇠 발급 뒤 명세 확인해 채움
if env('SAFETYDATA_KEY'): status('signals_disease', None, '끝점 확인 필요(행정안전부 가축전염병발생통계 15150280)')
else: status('signals_disease', None, '열쇠 없음(SAFETYDATA_KEY)')
items.sort(key=lambda i: (i['level'] != '경보', i['kind']))
jsave(os.path.join(DATA, 'signals.json'), {'at': stamp(), 'items': items[:30]}, indent=1)
print('이상 신호', len(items))
