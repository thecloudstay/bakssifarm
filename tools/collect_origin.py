# 실제 출하 금액(팔린 돈) 기준 시군×품목 집계 — 한국농수산식품유통공사 「전국 공영도매시장 경매원천정보」(apis.data.go.kr/B552845/katOrigin/trades)
# 낙찰 한 건마다 원산지명(plor_nm)·총가격(totprc)·물량이 있음 → 원산지를 시군으로 바꿔 품목별 금액을 쌓는다.
# 열쇠: DATA_GO_KR_KEY. 전날 하루치를 받아 private/origin/월.json 에 누적, 최근 12개월 합을 site/data/origin.json 으로 공개(시군 집계만).
# 농협 수매로 빠지는 품목(쌀·보리·콩 등)은 제외. 원산지가 시도까지만 있거나 수입산이면 버린다.
import sys, os, re, json, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
KEY = env('DATA_GO_KR_KEY')
if not KEY:
    status('origin', None, '열쇠 없음(DATA_GO_KR_KEY)'); print('열쇠 없음'); sys.exit(0)
URL = 'https://apis.data.go.kr/B552845/katOrigin/trades'
EXCLUDE = re.compile(r'쌀|벼|보리|밀|콩|옥수수알|수매|가공')
SIDO = {'서울': '서울', '부산': '부산', '대구': '대구', '인천': '인천', '광주': '광주', '대전': '대전', '울산': '울산', '세종': '세종', '경기': '경기', '강원': '강원', '충북': '충북', '충청북': '충북', '충남': '충남', '충청남': '충남', '전북': '전북', '전라북': '전북', '전남': '전남', '전라남': '전남', '경북': '경북', '경상북': '경북', '경남': '경남', '경상남': '경남', '제주': '제주'}
METRO = {'서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종'}
UNITS = {g['properties']['u'] for g in json.load(open(os.path.join(DATA, 'units.json'), encoding='utf-8'))['objects']['units']['geometries']}
SG_BY_SHORT = collections.defaultdict(list)
for u in UNITS:
    sd, sg = u.split('|'); SG_BY_SHORT[re.sub(r'(시|군)$', '', sg)].append(u)
def to_unit(name):
    n = (name or '').replace('특별자치도', '').replace('특별자치시', '').replace('광역시', '').replace('특별시', '').replace('도 ', ' ').strip()
    if not n or '수입' in n or '외국' in n: return None
    parts = n.split()
    sd = None
    for k, v in SIDO.items():
        if parts and parts[0].startswith(k): sd = v; break
    if sd in METRO: return sd + '|' + sd
    rest = parts[1] if sd and len(parts) > 1 else (parts[0] if parts else '')
    if not rest: return None
    short = re.sub(r'(시|군|구)$', '', rest)
    if sd and (sd + '|' + rest) in UNITS: return sd + '|' + rest
    cands = [u for u in SG_BY_SHORT.get(short, []) if not sd or u.startswith(sd + '|')]
    return cands[0] if len(cands) == 1 else None
from kat_markets import markets, fetch_day as _fd
def fetch_day(ymd):
    iso = f'{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}'   # 명세: 정산일자 YYYY-MM-DD + 도매시장코드 필수(공공데이터포털 15141810)
    codes = markets(KEY, URL, iso)
    return _fd(KEY, URL, iso, codes) if codes else []
def add_day(day, rows):
    """하루치 낙찰을 그 달 파일에 쌓음. 이미 쌓인 날·0건인 날은 건너뜀(0건인 날은 다음 실행에서 다시 시도)."""
    ymd = day.strftime('%Y%m%d')
    mpath = os.path.join(PRIVATE, 'origin', day.strftime('%Y-%m') + '.json')
    month = jload(mpath, {'days': [], 'agg': {}})
    if not rows or ymd in month['days']: return 0
    agg = month['agg']; used = 0
    for r in rows:
        item = (r.get('gds_mclsf_nm') or r.get('corp_gds_item_nm') or '').strip()
        if not item or EXCLUDE.search(item) or EXCLUDE.search(r.get('gds_lclsf_nm') or ''): continue
        u = to_unit(r.get('plor_nm'))
        if not u: continue
        try: amt = float(r.get('totprc') or 0); qty = float(r.get('unit_tot_qty') or r.get('qty') or 0)
        except ValueError: continue
        k = u + '|' + item + '|' + (r.get('gds_lclsf_nm') or '')
        a = agg.setdefault(k, [0, 0, 0]); a[0] += amt; a[1] += qty; a[2] += 1; used += 1
    month['days'].append(ymd); jsave(mpath, month)
    return 1
def have_day(day):
    return day.strftime('%Y%m%d') in jload(os.path.join(PRIVATE, 'origin', day.strftime('%Y-%m') + '.json'), {'days': []}).get('days', [])
day = now().date() - datetime.timedelta(days=1)
ymd = day.strftime('%Y%m%d')
try:
    rows = fetch_day(ymd)
    add_day(day, rows)
    # 빠진 날 채우기 — 밤 실행 때 아직 정산이 안 올라왔거나 국내 실행기가 꺼져 있던 날(최근 7일, 일요일 제외, 한 번에 3일만 시도)
    filled = []; tried = 0
    for back in range(2, 9):
        if tried >= int(env('ORIGIN_BACKFILL') or 3): break
        d2 = now().date() - datetime.timedelta(days=back)
        if d2.weekday() == 6 or have_day(d2): continue
        tried += 1
        try:
            if add_day(d2, fetch_day(d2.strftime('%Y%m%d'))): filled.append(d2.strftime('%m-%d'))
        except Exception as e: print('빠진 날 실패', d2, str(e)[:60])
    # 최근 12개월 합 → 공개 집계(시군별 품목 순위, 시군 합)
    tot = collections.defaultdict(lambda: [0, 0, 0]); od = os.path.join(PRIVATE, 'origin')
    files = sorted(f for f in os.listdir(od) if f.endswith('.json'))[-12:]
    for f in files:
        for k, a in jload(os.path.join(od, f), {}).get('agg', {}).items():
            t = tot[k]; t[0] += a[0]; t[1] += a[1]; t[2] += a[2]
    units = collections.defaultdict(lambda: {'amt': 0, 'items': collections.Counter(), 'grp': {}})
    items = collections.Counter()
    for k, a in tot.items():
        q = k.split('|'); u, item, grp = q[0] + '|' + q[1], q[2], q[3] if len(q) > 3 else ''
        units[u]['amt'] += a[0]; units[u]['items'][item] += a[0]; units[u]['grp'][item] = grp; items[item] += a[0]
    pub = {u: {'amt': round(e['amt']), 'top': [[i, round(v), e['grp'].get(i, '')] for i, v in e['items'].most_common(8)]} for u, e in units.items()}
    jsave(os.path.join(DATA, 'origin.json'), {'at': stamp(), 'months': [f[:7] for f in files], 'days': sum(len(jload(os.path.join(od, f), {}).get('days', [])) for f in files),
          'units': pub, 'items': [[i, round(v)] for i, v in items.most_common(60)],
          'source': '한국농수산식품유통공사 전국 공영도매시장 경매원천정보(낙찰 건별 원산지·총가격). 원산지가 시군까지 적힌 낙찰만, 농협 수매 품목 제외'})
    status('origin', True, f'{ymd} 낙찰 {len(rows):,}건' + (f' · 빠진 날 채움 {", ".join(filled)}' if filled else '') + f' · 누적 {len(files)}개월')
    print('출하 금액', ymd, len(rows))
except Exception as e:
    status('origin', False, str(e)[:200]); print('실패', e)
