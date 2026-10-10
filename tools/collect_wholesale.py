# 공영도매시장 정산 경락가(한국농수산식품유통공사 katSale/trades) — 전날 품목별 평균가·물량, 도매시장별 값
# 열쇠: DATA_GO_KR_KEY. 결과 site/data/price/wholesale.json (농산·수산 함께, 금액 큰 품목 순)
import sys, os, json, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
KEY = env('DATA_GO_KR_KEY')
if not KEY:
    status('wholesale', None, '열쇠 없음(DATA_GO_KR_KEY)'); print('열쇠 없음'); sys.exit(0)
URL = 'https://apis.data.go.kr/B552845/katSale/trades'
def fetch(ymd):
    for style in ('cond', 'plain'):
        rows = []; page = 1
        while True:
            p = {'serviceKey': KEY, 'pageNo': page, 'numOfRows': 1000, 'returnType': 'json'}
            if style == 'cond': p['cond[trd_clcln_ymd::EQ]'] = ymd
            else: p['trd_clcln_ymd'] = ymd
            j = json.loads(get(URL, p)); body = j.get('response', j).get('body', j.get('body', {}))
            it = body.get('items', []); it = it.get('item', []) if isinstance(it, dict) else it
            if not it: break
            rows += it
            if len(it) < 1000 or page >= 200: break
            page += 1
        if rows: return rows
    return []
def f(x):
    try: return float(x or 0)
    except ValueError: return 0.0
d = now().date() - datetime.timedelta(days=1)
while d.weekday() == 6: d -= datetime.timedelta(days=1)
try:
    rows = fetch(d.strftime('%Y%m%d'))
    items = collections.defaultdict(lambda: {'amt': 0, 'kg': 0, 'grp': '', 'mk': collections.defaultdict(lambda: [0, 0])})
    for r in rows:
        name = (r.get('gds_mclsf_nm') or '').strip()
        if not name: continue
        amt = f(r.get('totprc')); q = f(r.get('unit_tot_qty')); uq = f(r.get('unit_qty')); un = (r.get('unit_nm') or '')
        kg = q if un in ('kg', '㎏', 'KG') else (q * uq if un in ('kg', '㎏') else 0)
        if 'kg' in un.lower() or '㎏' in un: kg = q
        e = items[name]; e['amt'] += amt; e['kg'] += kg; e['grp'] = r.get('gds_lclsf_nm') or e['grp']
        m = e['mk'][r.get('whsl_mrkt_nm') or '']; m[0] += amt; m[1] += kg
    out = []
    for name, e in sorted(items.items(), key=lambda x: -x[1]['amt'])[:80]:
        mk = sorted(([k, round(v[0] / v[1]) if v[1] else None, round(v[0])] for k, v in e['mk'].items() if k), key=lambda x: -(x[2]))
        out.append({'item': name, 'grp': e['grp'], 'amt': round(e['amt']), 'kg': round(e['kg']), 'won_kg': round(e['amt'] / e['kg']) if e['kg'] else None, 'markets': mk[:12]})
    jsave(os.path.join(DATA, 'price', 'wholesale.json'), {'at': stamp(), 'date': d.isoformat(), 'items': out, 'source': '한국농수산식품유통공사 전국 공영도매시장 정산정보'}, indent=1)
    status('wholesale', True, f'{d.isoformat()} {len(rows):,}건 · {len(out)}품목')
    print('도매시장', d, len(rows))
except Exception as e:
    status('wholesale', False, str(e)[:200]); print('실패', e)
