# 연동 가능한 모든 연동창구 한꺼번에: tools/api_specs.json(명세)을 읽어 열쇠 하나(DATA_GO_KR_KEY)로 부르고
#  - 원자료(앞쪽 일부)는 private/api/<id>.json (공개 안 함)
#  - 공개는 집계만: 전체 건수, 시군별 건수(주소·시군 항목이 있을 때), 항목 이름 → site/data/api/<id>.json
#  - 연동 대장(이름·상태·건수·마지막 시각) → site/data/apis.json  (콘솔·소개 화면에 표로 나옴)
# 날짜가 필요한 변수(…Ymd, …Dt, …De, 날짜 등)는 어제 날짜로 채움. 하루 열쇠 한도를 넘지 않도록 연동창구당 최대 쪽수 제한.
# 이미 전용 수집기가 있는 것(축평원 등급판정, 도매시장 정산·원천, 인허가 조회, 관측 최신값)은 건너뜀.
import sys, os, re, json, datetime, collections, xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
KEY = env('DATA_GO_KR_KEY')
FS_KEY = env('FOODSAFETY_KEY')
MF_KEY = env('MAFRA_KEY')  # 농식품 공공데이터포털 열쇠(도축실적·부분육 경락·가축질병 등). 없으면 견본 열쇠(5건)로 연결만 확인  # 식품안전나라 열쇠(축산물 영업 허가대장·동물용 의약품·어류 질병 등)
SPECS = jload(os.path.join(ROOT, 'tools', 'api_specs.json'), [])
OWN = ('openapi-data/service/user/grade', 'B552845/katSale', 'B552845/katOrigin', '1741000/', '1192136/dtRecent')
MAX_PAGES = int(env('API_MAX_PAGES', '20'))
UNITS = {g['properties']['u'] for g in jload(os.path.join(DATA, 'units.json'), {'objects': {'units': {'geometries': []}}})['objects']['units']['geometries']}
SIDO = {'서울': '서울', '부산': '부산', '대구': '대구', '인천': '인천', '광주': '광주', '대전': '대전', '울산': '울산', '세종': '세종', '경기': '경기', '강원': '강원', '충청북': '충북', '충북': '충북', '충청남': '충남', '충남': '충남', '전라북': '전북', '전북': '전북', '전라남': '전남', '전남': '전남', '경상북': '경북', '경북': '경북', '경상남': '경남', '경남': '경남', '제주': '제주'}
METRO = {'서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종'}
def to_unit(addr):
    p = (addr or '').replace('특별자치', '').replace('광역시', '').replace('특별시', '').split()
    if not p: return None
    sd = next((v for k, v in SIDO.items() if p[0].startswith(k)), None)
    if not sd: return None
    if sd in METRO: return sd + '|' + sd
    if len(p) > 1 and (sd + '|' + p[1]) in UNITS: return sd + '|' + p[1]
    return None
ADDR = re.compile(r'(addr|ADDR|Addr|adres|주소|LOTNO|ROAD_NM|sigun|SIGUN|sgg|SGG|ctpv|CTPV|area|AREA)')
DATEP = re.compile(r'(ymd|YMD|Ymd|dt$|Dt$|DT$|de$|De$|DE$|date|Date|DATE|yyyymmdd|baseDate)')
def items_of(raw):
    t = raw.lstrip()
    if t.startswith(b'{') or t.startswith(b'['):
        j = json.loads(raw)
        def find(o):
            if isinstance(o, list) and o and isinstance(o[0], dict): return o
            if isinstance(o, dict):
                for k in ('item', 'items', 'row', 'data', 'list'):
                    if k in o:
                        r = find(o[k])
                        if r is not None: return r if isinstance(r, list) else [r]
                for v in o.values():
                    r = find(v)
                    if r is not None: return r
            return None
        r = find(j); return r or [], j
    root = ET.fromstring(raw)
    rows = [{c.tag: (c.text or '').strip() for c in it} for it in root.iter('item')]
    if not rows: rows = [{c.tag: (c.text or '').strip() for c in it} for it in root.iter('row')]
    code = root.findtext('.//resultCode') or root.findtext('.//returnReasonCode') or ''
    return rows, {'code': code, 'msg': root.findtext('.//resultMsg') or root.findtext('.//returnAuthMsg') or ''}
reg = jload(os.path.join(DATA, 'apis.json'), {'items': {}})
day = (now().date() - datetime.timedelta(days=1)).strftime('%Y%m%d')
ok = fail = skip = 0
import time as _t
T0 = _t.time(); BUDGET = int(env('API_BUDGET_SEC', '1500'))   # 하루 25분 안에서 돌고, 남은 것은 다음 날 앞에서부터 이어 감
order = sorted(SPECS, key=lambda s: (reg['items'].get(s['id'], {}).get('at', '') or ''))   # 오래 안 부른 것부터
for s in order:
    if _t.time() - T0 > BUDGET: break
    sid = s['id']; spec = s.get('spec'); host = (spec or {}).get('host') or s.get('host') or ''
    ent = reg['items'].setdefault(sid, {})
    ent.update({'title': s['title'], 'dom': s['dom'], 'cat': s['cat'], 'host': host})
    if any(o in host for o in OWN): ent.update({'state': '전용 수집기'}); skip += 1; continue
    fs = re.search(r'foodsafetykorea\.go\.kr.*svc_no=(\w+)', s.get('external') or '')
    if fs and not (spec and spec.get('ops')):
        if not FS_KEY: ent.update({'state': '제공처 열쇠', 'link': s['external'], 'need': 'FOODSAFETY_KEY'}); skip += 1; continue
        try:
            rows = []; meta = None
            for page in range(MAX_PAGES):
                raw = get(f"http://openapi.foodsafetykorea.go.kr/api/{FS_KEY}/{fs.group(1)}/json/{page * 1000 + 1}/{page * 1000 + 1000}")
                got, meta = items_of(raw); rows += got
                if len(got) < 1000: break
            spec = None; s = dict(s, _rows=rows)
        except Exception as e:
            ent.update({'state': '실패', 'at': stamp(), 'msg': str(e)[:140]}); fail += 1; continue
    grids = (s.get('ext_hint') or {}).get('grids') or []
    if grids and 'mafra.go.kr' in (s.get('external') or '') and not (spec and spec.get('ops')):
        try:
            rows = []; meta = None; k = MF_KEY or 'sample'
            for page in range(MAX_PAGES if MF_KEY else 1):
                a = page * 1000 + 1; z = page * 1000 + (1000 if MF_KEY else 5)
                got, meta = items_of(get(f"http://211.237.50.150:7080/openapi/{k}/json/{grids[0]}/{a}/{z}")); rows += got
                if len(got) < 1000: break
            if not MF_KEY:
                ent.update({'state': '제공처 열쇠', 'link': s['external'], 'need': 'MAFRA_KEY', 'msg': f'견본 열쇠로 연결 확인 {len(rows)}건' if rows else '견본 열쇠 응답 없음', 'at': stamp()}); skip += 1; continue
            spec = None; s = dict(s, _rows=rows)
        except Exception as e:
            ent.update({'state': '실패' if MF_KEY else '제공처 열쇠', 'link': s.get('external'), 'at': stamp(), 'msg': str(e)[:140]})
            if MF_KEY: fail += 1
            else: skip += 1
            continue
    if (not spec or not spec.get('ops')) and s.get('external') and '_rows' not in s:
        ent.update({'state': '제공처 열쇠', 'link': s['external']}); skip += 1; continue
    if '_rows' not in s and (not spec or not spec.get('ops')):
        ent.update({'state': '명세 없음', 'urls': (s.get('plain') or {}).get('urls', [])[:3]}); skip += 1; continue
    if '_rows' not in s and not KEY: ent.update({'state': '열쇠 대기'}); skip += 1; continue
    try:
      if '_rows' in s: rows = s['_rows']; meta = None
      else:
        op = spec['ops'][0]; base = op.get('full') or (op['path'] if op['path'].startswith('http') else f"https://{host.rstrip('/')}{op['path']}")
        params = {'serviceKey': KEY, 'pageNo': 1, 'numOfRows': 1000}
        names = [p['name'] for p in op.get('params', []) if p.get('name')]
        if 'resultType' in names: params['resultType'] = 'json'
        if 'type' in names: params['type'] = 'json'
        if '_type' in names: params['_type'] = 'json'
        if 'returnType' in names: params['returnType'] = 'json'
        if 'dataType' in names: params['dataType'] = 'JSON'
        for p in op.get('params', []):
            if re.search(r'(re?tu?rn|result|data)_?type', p.get('name') or '', re.I) and str(p.get('sample', '')).lower() == 'json': params[p['name']] = 'json'
        if 'ServiceKey' in names: params['ServiceKey'] = params.pop('serviceKey')
        for p in op.get('params', []):
            n = p.get('name') or ''
            if p.get('req') and n not in params and DATEP.search(n): params[n] = day
            elif p.get('req') and n not in params and p.get('sample') and p['sample'] not in ('옵션', '필수'): params[n] = p['sample']
        rows = []; meta = None
        for page in range(1, MAX_PAGES + 1):
            params['pageNo'] = page
            got, meta = items_of(get(base, params, timeout=20, retry=1))
            rows += got
            if len(got) < 1000: break
      fields = sorted({k for r in rows[:200] for k in r.keys()})
      afield = next((f for f in fields if ADDR.search(f)), None)
      sdf = next((f for f in fields if re.search(r'(city|ctpv|ctprvn|sido|SIDO|CTPV)', f) and not re.search(r'(cd|Cd|CD|code)$', f)), None)
      sgf = next((f for f in fields if re.search(r'(citicoungu|sgg|signgu|sigungu|SGG|SIGNGU|sigun)', f, re.I) and not re.search(r'(cd|Cd|CD|code)$', f)), None)
      if sdf and sgf: cnt = collections.Counter(to_unit(f"{r.get(sdf, '')} {r.get(sgf, '')}") for r in rows)
      else: cnt = collections.Counter(to_unit(r.get(afield)) for r in rows) if afield else collections.Counter()
      cnt.pop(None, None)
      jsave(os.path.join(PRIVATE, 'api', sid + '.json'), {'at': stamp(), 'rows': rows[:5000]})
      jsave(os.path.join(DATA, 'api', sid + '.json'), {'at': stamp(), 'title': s['title'], 'n': len(rows), 'fields': fields, 'by_unit': dict(cnt.most_common())})
      ent.update({'state': '정상' if rows else '빈 응답', 'n': len(rows), 'at': stamp(), 'fields': len(fields), 'units': len(cnt), 'msg': (json.dumps(meta, ensure_ascii=False)[:120] if not rows else '')})
      ok += 1
    except Exception as e:
        ent.update({'state': '실패', 'at': stamp(), 'msg': str(e)[:140]}); fail += 1
reg['at'] = stamp(); reg['total'] = len(SPECS)
reg['summary'] = dict(collections.Counter(v.get('state', '?') for v in reg['items'].values()))
jsave(os.path.join(DATA, 'apis.json'), reg, indent=1)
status('apis', None if not KEY else (fail == 0), f'정상 {ok} · 실패 {fail} · 건너뜀 {skip} / {len(SPECS)}')
print('연동 대장', reg['summary'])
