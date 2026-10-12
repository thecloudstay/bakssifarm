# 자가 점검(자가 발전 고리 ①재기·②찾기) — 매일 아침 작업 끝에 돈다. 개인정보 없이 합계 숫자만.
#  재기: 수집기 상태·자료 신선도, 화면 수, 깨진 내부 연결, 빈 칸 비율, 연동창구 상태, 신호 적중률, (방문 숫자는 분석 열쇠가 붙으면)
#  찾기: 고칠 거리 목록(우선순위) → private/metrics/날짜.json, 그리고 콘솔 「자가 점검」 칸(site/data/selfcheck.json)
# 고치기·검증은 매일 아침 예약 작업(docs/자가개선_RUNBOOK.md)이 이 목록을 읽고 한다.
import sys, os, re, json, glob, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
T = now(); today = T.date()
st = jload(os.path.join(DATA, 'status.json'), {}); cols = st.get('collectors', {})
m = {'date': today.isoformat(), 'at': stamp(), 'collectors': {}, 'fresh': {}, 'pages': {}, 'apis': {}, 'signal': {}, 'todo': []}
def todo(level, kind, what, hint=''):
    m['todo'].append({'level': level, 'kind': kind, 'what': what, 'hint': hint})
# 1) 수집기
for k, v in cols.items():
    if k == 'selfcheck': continue   # 자기 자신의 앞 결과는 세지 않음
    at = v.get('at') or ''
    try: age = (T.replace(tzinfo=None) - datetime.datetime.strptime(at, '%Y-%m-%d %H:%M')).total_seconds() / 3600
    except Exception: age = None
    m['collectors'][k] = {'ok': v.get('ok'), 'age_h': round(age, 1) if age is not None else None, 'msg': (v.get('msg') or '')[:120]}
    if v.get('ok') is False and k == 'apis':   # 403(활용신청 전)은 아래 「활용신청 필요」로 따로 셈 — 진짜 실패만
        nf = sum(1 for x in jload(os.path.join(DATA, 'apis.json'), {'items': {}})['items'].values() if x.get('state') == '실패' and '403' not in (x.get('msg') or ''))
        if nf: todo('보통', '수집 실패', f'연동창구 {nf}곳 응답 실패(403 제외)', '끝점·변수 확인, 해외 실행기에서 막힌 것인지 구분')
        continue
    if v.get('ok') is False: todo('높음', '수집 실패', f'{k}: {(v.get("msg") or "")[:100]}', '원인 확인 후 수집기 고침(끝점·변수·쪽 넘김)')
    if age is not None and age > 50 and k not in ('trade', 'license', 'wipan'): todo('보통', '오래된 자료', f'{k} 마지막 실행 {round(age)}시간 전', '작업 흐름이 멈췄는지 확인')
# 2) 자료 신선도·빈 자료
pr = jload(os.path.join(DATA, 'price', 'latest.json'), {})
rows = sum(len(s.get('rows', [])) for s in pr.get('ekape', []))
m['fresh']['경락가 날짜'] = pr.get('date'); m['fresh']['경락가 줄'] = rows
if pr and rows == 0: todo('높음', '빈 자료', '축평원 등급별 경락가 표가 비어 있음', '경매일 찾기·응답 칸 이름 확인')
wh = jload(os.path.join(DATA, 'price', 'wholesale.json'), {})
m['fresh']['도매시장 품목'] = len(wh.get('items', []))
if wh and not wh.get('items'): todo('높음', '빈 자료', '공영도매시장 정산 자료가 0건', '요청 변수·날짜 형식 진단(tools/probe.py)')
wp = jload(os.path.join(DATA, 'wipan.json'), {}); m['fresh']['위판 달'] = wp.get('month')
if wp.get('month'):
    lag = (today.year * 12 + today.month) - (int(wp['month'][:4]) * 12 + int(wp['month'][5:7]))
    if lag > 2: todo('보통', '오래된 자료', f'위판 자료가 {wp["month"]} 그대로', '파일데이터 갱신 여부 확인')
bs = jload(os.path.join(DATA, 'buysignal.json'), {}); sc = bs.get('score') or {}
m['signal'] = {'n': sc.get('n', 0), 'hit': sc.get('hit', 0), 'rate': round(sc['hit'] / sc['n'] * 100) if sc.get('n') else None}
if sc.get('n', 0) >= 10 and m['signal']['rate'] < 50: todo('보통', '신호 적중률', f'구매 신호 적중률 {m["signal"]["rate"]}%', '근거별 기여를 따져 기준 조정(2주 검증)')
# 3) 연동창구
ap = jload(os.path.join(DATA, 'apis.json'), {'items': {}})
c = collections.Counter(v.get('state') for v in ap['items'].values()); m['apis'] = dict(c)
need = [[k, v['title']] for k, v in ap['items'].items() if v.get('state') == '활용신청 필요' or '403' in (v.get('msg') or '')]
if need: todo('낮음', '활용신청 필요', f'공공데이터포털 활용신청이 안 된 연동창구 {len(need)}건', '대표가 할 일 목록으로 정리(콘솔 「자가 점검」에 표시)')
m['apis_need_apply'] = need[:300]
# 활용신청 우선순위 — 막힌 다른 수집을 풀어 주거나 유통업체가 돈 내고 볼 값·수급 자료부터(대표가 위에서부터 눌러 신청)
PRI = [(r'표준코드', 10, '도매시장 정산·원천 수집의 코드 목록을 풀어 줌'), (r'경락|경매|정산|도매시장|위판|공판장', 8, '값 자료(구매 신호·수급 기회의 근거)'),
       (r'가격|시세|등락|추이', 8, '값 자료(구매 신호·수급 기회의 근거)'), (r'수급|관측|예측|출하|재고|생산량', 7, '수급 예보의 근거'),
       (r'이력|도축|도계|등급', 6, '축산 물량·등급 흐름'), (r'수입|수출|검역', 5, '수입 물량·단가'), (r'질병|방역|구제역|인플루엔자|돼지열병|폐사|적조|수온', 5, '위험 예보의 근거'),
       (r'부화|종축|동물병원|사료|도축업', 4, '업체 지도 층')]
def pri(t):
    if re.search(r'잔류농약|위판장 정보|위판장 현황', t): return 2, ''
    for rx, w, why in PRI:
        if re.search(rx, t): return w, why
    return 1, ''
m['apply_top'] = sorted(([k, t, *pri(t)] for k, t in need), key=lambda x: -x[2])[:25]
# 4) 화면: 수, 깨진 내부 연결, 빈 칸
pages = glob.glob(os.path.join(SITE, '**', 'index.html'), recursive=True) + glob.glob(os.path.join(SITE, '*.html'))
m['pages']['n'] = len(pages)
broken = collections.Counter(); empty = 0
for p in pages:
    h = open(p, encoding='utf-8', errors='replace').read()
    for href in re.findall(r'href="(/bakssifarm/[^"#?]*)"', h):
        path = href[len('/bakssifarm/'):]
        f = os.path.join(SITE, path)
        if not (os.path.exists(f) or os.path.exists(os.path.join(f, 'index.html'))): broken[href] += 1
    if '열쇠가 붙으면' in h or '연동 전' in h: empty += 1
m['pages']['broken_links'] = len(broken); m['pages']['waiting_pages'] = empty
for href, n in broken.most_common(5): todo('높음', '깨진 연결', f'{href} ({n}곳에서 연결)', '대상 화면을 만들거나 연결을 고침')
# 5) 방문(분석 열쇠가 붙으면 채움)
m['traffic'] = st.get('traffic') or None
if not m['traffic']: todo('낮음', '측정 공백', '방문 숫자 없음(구글 분석·서치어드바이저 미연결)', '대표 키 입력 후 자동으로 채워짐')
order = {'높음': 0, '보통': 1, '낮음': 2}; m['todo'].sort(key=lambda x: order[x['level']])
jsave(os.path.join(PRIVATE, 'metrics', today.isoformat() + '.json'), m, indent=1)
jsave(os.path.join(DATA, 'selfcheck.json'), {k: m[k] for k in ('date', 'at', 'fresh', 'pages', 'apis', 'signal', 'todo')} | {'need_apply': len(need), 'apply_top': m['apply_top']})
status('selfcheck', not any(t['level'] == '높음' for t in m['todo']), f'고칠 거리 {len(m["todo"])}건(높음 {sum(1 for t in m["todo"] if t["level"] == "높음")})')
print('자가 점검', len(m['todo']), [t['what'][:40] for t in m['todo'][:5]])
