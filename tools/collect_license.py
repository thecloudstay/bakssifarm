# 행정안전부 지방행정 인허가(공공데이터포털 조회서비스) — 가축사육업·사료제조업·도축업·부화업·종축업·동물병원·동물약국
# 열쇠: DATA_GO_KR_KEY. 하루 1만 건 자동승인. 한 번에 1,000행씩 받아 전부 모음.
# 결과: 사업장(공장·도축장·병원 등)은 핀으로 공개(site/data/biz/*.json), 가축사육업(농가)은 시군·읍면동 집계만 공개하고 리 단위는 private/ 에만 둠.
import sys, os, re, json, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
KEY = env('DATA_GO_KR_KEY')
SERVICES = [
    # (이름, 호스트 경로, 공개 핀 여부, 파일 이름)
    ('가축사육업', 'livestock_farming_v2', False, 'farm'),
    ('사료제조업', 'feed_manufacturers', True, 'feed'),
    ('도축업', 'slaughterhouses', True, 'slaughter'),
    ('부화업', 'hatcheries_v2', True, 'hatchery'),
    ('종축업', 'breeding_stock_businesses_v2', True, 'breeding'),
    ('동물병원', 'animal_hospitals', True, 'vet'),
    ('동물약국', 'animal_pharmacies', True, 'pharmacy'),
    ('가축인공수정소', 'artificial_insemination_centers', True, 'ai_center'),
    ('동물용의약품도매상', 'veterinary_drug_wholesalers', True, 'vet_drug'),
    ('동물용의료용구판매업', 'veterinary_medical_equipment_sales', True, 'vet_equip'),
    ('집유업', 'milk_collection', True, 'milk'),
    ('축산가공업', 'livestock_processing', True, 'processing'),
    ('식육포장처리업', 'meat_packers', True, 'packer'),
    ('축산판매업', 'livestock_retail', False, 'retail'),
    ('가축분뇨수집운반업', 'manure_collection_transport', True, 'manure_trans'),
    ('가축분뇨배출시설관리업', 'manure_facility_management', True, 'manure_fac'),
]
if not KEY:
    status('license', None, '열쇠 없음(DATA_GO_KR_KEY)'); print('열쇠 없음'); sys.exit(0)
try:
    from pyproj import Transformer
    TR = Transformer.from_crs('EPSG:5174', 'EPSG:4326', always_xy=True)   # 보정계수 없는 베셀 중부원점 → 위경도
except Exception:
    TR = None
SIDO = {'서울특별시': '서울', '부산광역시': '부산', '대구광역시': '대구', '인천광역시': '인천', '광주광역시': '광주', '대전광역시': '대전', '울산광역시': '울산', '세종특별자치시': '세종', '경기도': '경기', '강원특별자치도': '강원', '강원도': '강원', '충청북도': '충북', '충청남도': '충남', '전북특별자치도': '전북', '전라북도': '전북', '전라남도': '전남', '전남광주통합특별시': '전남', '경상북도': '경북', '경상남도': '경남', '제주특별자치도': '제주'}
METRO = {'서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종'}
def parse_addr(a):
    p = (a or '').split()
    if len(p) < 2 or p[0] not in SIDO: return None
    sd = SIDO[p[0]]; i = 1
    sg = p[1]
    if sd in METRO: u = sd + '|' + sd; i = 2 if (sg.endswith('구') or sg.endswith('군')) else 1
    else:
        if sg.endswith('시') and len(p) > 2 and p[2].endswith('구'): i = 3
        else: i = 2
        u = '대구|대구' if sg == '군위군' else sd + '|' + sg
    emd = p[i] if len(p) > i and re.search(r'(읍|면|동|가)$', p[i]) else ''
    ri = p[i + 1] if emd and len(p) > i + 1 and p[i + 1].endswith('리') else ''
    return u, emd, ri
def fetch_all(path):
    rows = []; page = 1
    while True:
        raw = get(f'https://apis.data.go.kr/1741000/{path}/' + ('info_v2' if path.endswith('_v2') else 'info'), {'serviceKey': KEY, 'pageNo': page, 'numOfRows': 1000, 'type': 'json'})
        j = json.loads(raw)
        body = j.get('response', j).get('body', {}) if isinstance(j, dict) else {}
        items = body.get('items', [])
        if isinstance(items, dict): items = items.get('item', [])
        if not items: break
        rows += items
        total = int(body.get('totalCount') or 0)
        if len(rows) >= total or len(items) < 1000: break
        page += 1
        if page > 400: break
    return rows
if env('ONLY_SCHEDULED') and now().weekday() != 0 and not env('FORCE_RUN'): print('월요일에만'); sys.exit(0)
today = now().date(); y1 = (today - datetime.timedelta(days=365)).strftime('%Y%m%d')
summary = []
for name, path, public, fn in SERVICES:
    try:
        rows = fetch_all(path)
        def is_open(r): return (r.get('SALS_STTS_CD') or '').strip() in ('1', '01') or '영업' in (r.get('SALS_STTS_NM') or '')
        alive = [r for r in rows if is_open(r)]
        by_u = collections.defaultdict(lambda: {'n': 0, 'in12': 0, 'out12': 0, 'emd': collections.Counter(), 'sp': collections.Counter()})
        ri_ct = collections.Counter()
        pins = []
        for r in rows:
            pa = parse_addr(r.get('LOTNO_ADDR') or r.get('ROAD_NM_ADDR'))
            if not pa: continue
            u, emd, ri = pa
            is_alive = is_open(r)
            if (r.get('LCPMT_YMD') or '') >= y1: by_u[u]['in12'] += 1
            if (r.get('CLSBIZ_YMD') or '') >= y1: by_u[u]['out12'] += 1
            if not is_alive: continue
            by_u[u]['n'] += 1
            if emd: by_u[u]['emd'][emd] += 1
            sp = r.get('PRMN_LSFBIZ_SPECS') or r.get('BZSTAT_SE_NM') or ''
            if sp: by_u[u]['sp'][sp] += 1
            if ri: ri_ct[(u, emd, ri, sp)] += 1
            if public:
                lat = lng = None
                if TR and r.get('CRD_INFO_X') and r.get('CRD_INFO_Y'):
                    try: lng, lat = TR.transform(float(r['CRD_INFO_X']), float(r['CRD_INFO_Y']))
                    except Exception: pass
                raw_xy = {} if lat else {'x': r.get('CRD_INFO_X'), 'y': r.get('CRD_INFO_Y')}   # 좌표 바꿈 모듈이 없는 곳(국내 실행기)에서는 원좌표를 남겨 두고 올리기 단계에서 바꿈
                pins.append({**raw_xy, 'name': r.get('BPLC_NM'), 'addr': r.get('ROAD_NM_ADDR') or r.get('LOTNO_ADDR'), 'u': u, 'tel': r.get('TELNO'), 'kind': sp, 'lat': round(lat, 5) if lat else None, 'lng': round(lng, 5) if lng else None, 'since': r.get('LCPMT_YMD')})
        pub = {u: {'n': v['n'], 'in12': v['in12'], 'out12': v['out12'], 'emd': dict(v['emd'].most_common()), 'sp': dict(v['sp'].most_common(8))} for u, v in by_u.items()}
        out = {'at': stamp(), 'name': name, 'total': len(rows), 'alive': len(alive), 'units': pub, 'source': '행정안전부 지방행정 인허가 데이터개방(공공데이터포털), 매일 갱신'}
        if public: out['pins'] = pins
        jsave(os.path.join(DATA, 'biz', fn + '.json'), out)
        if not public:
            jsave(os.path.join(PRIVATE, 'license', fn + '_ri.json'), {'at': stamp(), 'rows': [[u, e, ri, sp, c] for (u, e, ri, sp), c in ri_ct.items()]})
        summary.append(f'{name} {len(alive):,}/{len(rows):,}')
    except Exception as e:
        summary.append(f'{name} 실패 {str(e)[:60]}')
idx = {'at': stamp(), 'layers': [{'k': fn, 'name': name, 'public': public} for name, path, public, fn in SERVICES if os.path.exists(os.path.join(DATA, 'biz', fn + '.json'))]}
jsave(os.path.join(DATA, 'biz', 'index.json'), idx, indent=1)
ok = not any('실패' in s for s in summary)
status('license', ok if summary else None, ' · '.join(summary)[:300])
print('\n'.join(summary))
