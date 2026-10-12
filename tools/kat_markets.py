# 공영도매시장 코드 찾기 — katSale·katOrigin 은 정산일자(YYYY-MM-DD)와 도매시장코드가 둘 다 필수(공공데이터포털 15141809·15141810 명세)
# ① 표준코드 연동창구(katCode/wholesaleMarkets, 활용신청 필요)에서 받고, ② 막히면 코드 규칙(지역 2자리+일련)으로 후보를 한 번 훑어
#    자료가 나오는 코드만 tools/whsl_markets.json 에 기억(월요일마다 다시 훑음).
import os, json, datetime
from common import *
CACHE = os.path.join(ROOT, 'tools', 'whsl_markets.json')
def _items(raw):
    j = json.loads(raw); body = j.get('response', j).get('body', j.get('body', {}))
    it = body.get('items', []); it = it.get('item', []) if isinstance(it, dict) else it
    return (it if isinstance(it, list) else [it]), int(body.get('totalCount') or 0)
def query(url, key, iso, mkt, page=1, n=1000):
    return _items(get(url, {'serviceKey': key, 'pageNo': page, 'numOfRows': n, 'returnType': 'json', 'cond[trd_clcln_ymd::EQ]': iso, 'cond[whsl_mrkt_cd::EQ]': mkt}, timeout=25, retry=2))
def candidates():
    c = []
    for r in ('11', '21', '22', '23', '24', '25', '26', '29'): c += [f'{r}00{i:02d}' for i in range(1, 11)]
    for r in ('31', '32', '33', '34', '35', '36', '37', '38', '39'): c += [f'{r}{i:02d}01' for i in range(1, 26)]
    return c
def markets(key, url, iso):
    ca = jload(CACHE, {'codes': {}, 'at': ''})
    try:   # ① 표준코드
        it, _ = _items(get('https://apis.data.go.kr/B552845/katCode/wholesaleMarkets', {'serviceKey': key, 'pageNo': 1, 'numOfRows': 500, 'returnType': 'json'}, timeout=25, retry=1))
        got = {x['whsl_mrkt_cd']: x.get('whsl_mrkt_nm', '') for x in it if x.get('whsl_mrkt_cd')}
        if got: ca['codes'].update(got); ca['src'] = '표준코드'; ca['at'] = stamp(); jsave(CACHE, ca, indent=1); return ca['codes']
    except Exception as e: print('표준코드 못 받음', str(e)[:60])
    if ca['codes'] and not (now().weekday() == 0 and ca.get('src') != '표준코드' and ca.get('at', '')[:10] != now().date().isoformat()): return ca['codes']
    found = dict(ca['codes'])   # ② 후보 훑기
    for m in candidates():
        if m in found: continue
        try:
            it, tot = query(url, key, iso, m, n=1)
            if tot or it: found[m] = (it[0].get('whsl_mrkt_nm') if it else '') or ''; print('도매시장 코드', m, found[m])
        except Exception as e: print('후보 실패', m, str(e)[:50])
    ca.update({'codes': found, 'src': '후보 훑기', 'at': stamp()}); jsave(CACHE, ca, indent=1)
    return found
def fetch_day(key, url, iso, codes):
    rows = []
    for m in codes:
        page = 1
        while True:
            try: it, tot = query(url, key, iso, m, page)
            except Exception as e: print('실패', m, str(e)[:60]); break
            rows += it
            if len(it) < 1000 or page >= 300: break
            page += 1
    return rows
def last_weekday(back=1):
    d = now().date() - datetime.timedelta(days=back)
    while d.weekday() == 6: d -= datetime.timedelta(days=1)
    return d
