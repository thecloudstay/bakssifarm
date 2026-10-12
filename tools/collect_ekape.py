# 축산물품질평가원 등급판정정보(공공데이터포털 15058822) — 소·돼지 등급별 경락가, 돈육 대표가격, 공판장별 가격
# 열쇠: 환경변수 DATA_GO_KR_KEY (일반 인증키, 디코딩 값). 하루 1,000건 한도 안에서 아침 1회 4~6건만 부름.
import sys, os, datetime, xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
BASE = 'http://data.ekape.or.kr/openapi-data/service/user/grade/'
ABATT = {'0513': '농협 음성', '0613': '관성', '0616': '농협 포크빌(부천)', '1005': '김해 축공', '0202': '부경 축공', '0201': '동원산업', '1201': '신흥산업', '0905': '농협 고령', '0714': '익산', '0809': '농협 나주', '1401': '삼호축산', '1101': '제주축협', '1015': '해드림(홍성)', '0717': '중앙 축산물도매시장(안성)'}
KEY = env('DATA_GO_KR_KEY')
keyflag('data_go_kr', KEY)
if not KEY:
    status('ekape_price', None, '열쇠 없음(DATA_GO_KR_KEY)'); print('열쇠 없음'); sys.exit(0)

def call(op, **params):
    params['serviceKey'] = KEY
    raw = get(BASE + op, params)
    root = ET.fromstring(raw)
    code = (root.findtext('.//resultCode') or '').strip()
    if code not in ('00', '0', ''): raise RuntimeError(op + ' ' + (root.findtext('.//resultMsg') or code))
    return [{c.tag: (c.text or '').strip() for c in it} for it in root.iter('item')]
def num(s):
    try: return int(float(s.replace(',', '')))
    except Exception: return None
def grade_rows(items, order):
    out = {}
    for it in items:
        g = it.get('gradeNm') or it.get('gradeCd'); amt = num(it.get('CTotAmt') or it.get('totAmt') or '')
        cnt = num(it.get('CTotCnt') or it.get('totCnt') or '')
        if g and amt: out[g] = {'g': g, 'p': amt, 'n': cnt, 'ab': {ABATT[k]: num(it.get('c_' + k + 'Amt')) for k in ABATT if num(it.get('c_' + k + 'Amt') or '')}}
    rows = [out[g] for g in order if g in out] + [out[g] for g in out if g not in order]
    return rows

def day(d): return d.strftime('%Y%m%d')
today = now().date(); d1 = today - datetime.timedelta(days=1); d2 = today - datetime.timedelta(days=2)
# 경매가 없는 날(주말·공휴일)은 비어 오므로, 자료가 있는 가장 가까운 날을 거꾸로 찾는다(최대 10일)
CQ = dict(breedCd='024001', sexCd='025003', qgradeYn='N', defectIncludeYn='Y')
def cattle(d): return grade_rows(call('auct/cattle', startYmd=day(d), endYmd=day(d), **CQ), ['1++', '1+', '1', '2', '3', '등외'])
def back(d):
    for _ in range(10):
        d -= datetime.timedelta(days=1)
        if d.weekday() < 5: return d
    return d
try:
    secs = []
    d1 = today; c1 = []
    for _ in range(10):
        d1 = back(d1); c1 = cattle(d1)
        if any(r['g'] in ('1++', '1+', '1', '2', '3') for r in c1): break
    d2 = d1; c0 = {}
    for _ in range(10):
        d2 = back(d2); c0 = {r['g']: r['p'] for r in cattle(d2)}
        if c0: break
    for r in c1: r['d'] = (r['p'] - c0[r['g']]) if r['g'] in c0 else None
    secs.append({'title': '한우 거세', 'rows': c1, 'date': d1.isoformat()})
    # 돼지 탕박, 등급별
    p1 = grade_rows(call('auct/pigGrade', startYmd=day(d1), endYmd=day(d1), skinYn='Y', egradeExceptYn='N'), ['1+', '1', '2', '등외'])
    p0 = {r['g']: r['p'] for r in grade_rows(call('auct/pigGrade', startYmd=day(d2), endYmd=day(d2), skinYn='Y', egradeExceptYn='N'), [])}
    for r in p1: r['d'] = (r['p'] - p0[r['g']]) if r['g'] in p0 else None
    secs.append({'title': '돼지 탕박', 'rows': p1, 'date': d1.isoformat()})
    # 돈육 대표가격
    rep = call('auct/pigRepresentativePrice', startYmd=day(d1 - datetime.timedelta(days=7)), endYmd=day(d1))
    rep = [{'date': it.get('sumYmd'), 'kind': it.get('sableGubn'), 'p': num(it.get('costAmt') or '')} for it in rep]
    out = {'at': stamp(), 'date': d1.isoformat(), 'ekape': secs, 'pigRep': rep[-6:], 'source': '축산물품질평가원 등급판정정보(공공데이터포털), 원/㎏, 결함 포함 가격'}
    jsave(os.path.join(DATA, 'price', 'latest.json'), out, indent=1)
    jsave(os.path.join(DATA, 'price', 'history', d1.isoformat() + '.json'), out)
    # 공판장별 한우 1+ 가격 → 지도 공판장 핀용
    ab = {}
    for r in c1:
        for name, amt in r['ab'].items(): ab.setdefault(name, {})[r['g']] = amt
    jsave(os.path.join(DATA, 'price', 'abattoir.json'), {'date': d1.isoformat(), 'cattle': ab})
    status('ekape_price', True, f'{d1.isoformat()} 한우 {len(c1)}등급 · 돼지 {len(p1)}등급')
    print('경락가', d1, len(c1), len(p1))
except Exception as e:
    status('ekape_price', False, str(e)[:200]); print('실패', e); sys.exit(0)
