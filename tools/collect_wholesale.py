# 공영도매시장 정산 경락가(한국농수산식품유통공사 katSale/trades) — 전날 품목별 평균가·물량, 도매시장별 값
# 열쇠: DATA_GO_KR_KEY. 결과 site/data/price/wholesale.json (농산·수산 함께, 금액 큰 품목 순)
import sys, os, json, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
KEY = env('DATA_GO_KR_KEY')
if not KEY:
    status('wholesale', None, '열쇠 없음(DATA_GO_KR_KEY)'); print('열쇠 없음'); sys.exit(0)
URL = 'https://apis.data.go.kr/B552845/katSale/trades'
from kat_markets import markets, fetch_day, last_weekday
def fetch(ymd):
    iso = f'{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}'
    codes = markets(KEY, URL, iso)
    return fetch_day(KEY, URL, iso, codes) if codes else []
def f(x):
    try: return float(x or 0)
    except ValueError: return 0.0
HD = os.path.join(PRIVATE, 'wholesale'); os.makedirs(HD, exist_ok=True)   # 날짜별 품목 값(구매 신호의 근거) — 품목: [원/㎏, ㎏, 금액]
def agg(rows):
    items = collections.defaultdict(lambda: {'amt': 0, 'kg': 0, 'kamt': 0, 'grp': '', 'mk': collections.defaultdict(lambda: [0, 0, 0])})
    for r in rows:
        name = (r.get('gds_mclsf_nm') or '').strip()
        if not name: continue
        amt = f(r.get('totprc')); un = (r.get('unit_nm') or '')
        kg = f(r.get('unit_tot_qty')) if ('kg' in un.lower() or '㎏' in un) else 0   # ㎏ 단위 거래만 ㎏당 값에 씀(개·속·단은 금액에만)
        e = items[name]; e['amt'] += amt; e['grp'] = r.get('gds_lclsf_nm') or e['grp']
        if kg > 0: e['kg'] += kg; e['kamt'] += amt
        m = e['mk'][r.get('whsl_mrkt_nm') or '']; m[0] += amt
        if kg > 0: m[1] += kg; m[2] += amt
    return items
def day_file(d, items):
    jsave(os.path.join(HD, d.isoformat() + '.json'), {k: [round(e['kamt'] / e['kg']) if e['kg'] else None, round(e['kg']), round(e['amt'])] for k, e in items.items()})
d = last_weekday(1)
try:
    rows = fetch(d.strftime('%Y%m%d'))
    for _ in range(4):   # 휴장일이면 앞 거래일로
        if rows: break
        d = last_weekday((now().date() - d).days + 1); rows = fetch(d.strftime('%Y%m%d'))
    items = agg(rows)
    if rows: day_file(d, items)
    out = []
    for name, e in sorted(items.items(), key=lambda x: -x[1]['amt'])[:80]:
        mk = sorted(([k, round(v[2] / v[1]) if v[1] else None, round(v[0])] for k, v in e['mk'].items() if k), key=lambda x: -(x[2]))
        out.append({'item': name, 'grp': e['grp'], 'amt': round(e['amt']), 'kg': round(e['kg']), 'won_kg': round(e['kamt'] / e['kg']) if e['kg'] else None, 'markets': mk[:12]})
    jsave(os.path.join(DATA, 'price', 'wholesale.json'), {'at': stamp(), 'date': d.isoformat(), 'items': out, 'source': '한국농수산식품유통공사 전국 공영도매시장 정산정보'}, indent=1)
    # 지난 거래일 채우기(한 번에 5일, 30거래일까지) — 값 흐름 신호에 씀
    have = {x[:10] for x in os.listdir(HD)}; filled = 0; back = d
    for _ in range(45):
        if filled >= int(env('WH_BACKFILL') or (12 if len(have) < 10 else 5)) or len(have) >= 30: break
        back = last_weekday((now().date() - back).days + 1)
        if back.isoformat() in have: continue
        r2 = fetch(back.strftime('%Y%m%d'))
        if r2: day_file(back, agg(r2)); have.add(back.isoformat())
        filled += 1
    status('wholesale', True, f'{d.isoformat()} {len(rows):,}건 · {len(out)}품목 · 쌓인 거래일 {len(have)}')
    print('도매시장', d, len(rows), '쌓인 날', len(have))
except Exception as e:
    status('wholesale', False, str(e)[:200]); print('실패', e)
