# 관세청 수출입 실적(공공데이터포털 「관세청_품목별 국가별 수출입실적」)으로 수입 단가(원/㎏) 만들기
# 열쇠: DATA_GO_KR_KEY. 월 단위. 끝점·항목 이름은 열쇠 발급 뒤 첫 호출에서 확인(아래 표기는 포털 명세 기준, 확인 필요)
import sys, os, re, json, datetime, xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
KEY = env('DATA_GO_KR_KEY')
# 매달 3일부터 그달 처음 성공할 때까지 한 번(국내 실행기가 3일에 꺼져 있어도 다음 실행에서 받음)
_prev = jload(os.path.join(DATA, 'trade.json'), {}) or {}
_done = str(_prev.get('at', ''))[:7] == now().strftime('%Y-%m') and any(re.match(r'\d{4}-\d{2}$', str(r.get('ym'))) for x in _prev.get('items') or [] for r in x.get('rows') or [])
if env('ONLY_SCHEDULED') and not env('FORCE_RUN') and (now().day < 3 or _done): print('이달 수입 단가는 이미 받았거나 3일 전'); sys.exit(0)
# 비교할 품목: (이름, HS 부호, 우리 쪽 비교 대상)
ITEMS = [('쇠고기(냉장·냉동)', '0201', '한우 경락가'), ('쇠고기 냉동', '0202', '한우 경락가'), ('돼지고기', '0203', '돼지 경락가'),
         ('옥수수(사료용)', '1005', '배합사료 구입가'), ('대두박', '2304', '배합사료 구입가'), ('어분', '2301', '양식 사료 구입가'),
         ('전복', '030781', '전복 위판가'), ('김', '121221', '김 위판가'), ('넙치', '030229', '넙치 위판가'), ('새우', '0306', '새우 위판가')]
if not KEY:
    status('trade', None, '열쇠 없음(DATA_GO_KR_KEY)'); print('열쇠 없음'); sys.exit(0)
URL = 'https://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList'
d = now().date().replace(day=1); months = [(d - datetime.timedelta(days=1)).replace(day=1)]
for _ in range(11): months.append((months[-1] - datetime.timedelta(days=1)).replace(day=1))
def ym(x): return x.strftime('%Y%m')
# 응답 모양(2026-10 진단, tools/_debug/probe.json): 국가 부호 「-」인 줄은 기간 「총계」 한 줄뿐이고,
# 달별 값은 「하위 관세 부호 × 나라」 줄(year='2026.08')로만 온다 → 달마다 나라·하위 부호 줄을 더해 단가를 낸다.
OLD = {x['name']: x for x in (jload(os.path.join(DATA, 'trade.json'), {}) or {}).get('items') or []}
def fetch_all(hs):
    items, page = [], 1
    while True:
        raw = get(URL, {'serviceKey': KEY, 'strtYymm': ym(months[-1]), 'endYymm': ym(months[0]), 'hsSgn': hs, 'numOfRows': 1000, 'pageNo': page})
        root = ET.fromstring(raw); got = list(root.iter('item')); items += got
        try: total = int(root.findtext('.//totalCount') or 0)
        except ValueError: total = 0
        if not got or len(items) >= total or page >= 20: return items
        page += 1
def monthly(items):
    acc = {}
    for it in items:
        g = lambda k: (it.findtext(k) or '').strip()
        y = g('year') or g('yymm')
        if not g('statCd') or g('statCd') == '-' or '총계' in y: continue   # 기간 합계 줄 빼고 나라별 줄만 더함
        m = re.match(r'(\d{4})\D?(\d{2})$', y)
        if not m: continue
        try: amt = float(g('impDlr') or 0); wgt = float(g('impWgt') or 0)
        except ValueError: continue
        a = acc.setdefault(f'{m.group(1)}-{m.group(2)}', [0.0, 0.0]); a[0] += amt; a[1] += wgt
    return [{'ym': k, 'usd_kg': round(a / w, 3), 'wgt_t': round(w / 1000, 1)} for k, (a, w) in sorted(acc.items()) if w > 0]
out = []; errs = []; kept = []
for name, hs, cmp_ in ITEMS:
    try:
        rows = monthly(fetch_all(hs))
    except Exception as e:
        rows = []; errs.append(f'{name} {str(e)[:50]}')
    if not rows:   # 못 받았거나 빈 응답이면 지난 달별 값(총계 줄 아닌 것)을 그대로 둠
        rows = [r for r in (OLD.get(name) or {}).get('rows') or [] if re.match(r'\d{4}-\d{2}$', str(r.get('ym')))]
        if rows: kept.append(name)
    out.append({'name': name, 'hs': hs, 'cmp': cmp_, 'rows': rows[-12:]})
jsave(os.path.join(DATA, 'trade.json'), {'at': stamp(), 'items': out, 'note': '관세청 수출입실적, 달러/㎏ 단가. 원화 환산은 화면에서 월평균 환율로', 'errors': errs}, indent=1)
last = max((x['rows'][-1]['ym'] for x in out if x['rows']), default='')
status('trade', not errs, f'{sum(1 for x in out if x["rows"])}/{len(out)}품목' + (f' · 최근 {last}' if last else '') + (' · 지난 값 유지 ' + ', '.join(kept) if kept else '') + (' · 실패 ' + ', '.join(errs) if errs else ''))
print('수출입', len(out), errs)
