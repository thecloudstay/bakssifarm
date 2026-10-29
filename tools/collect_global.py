# 세계 공개 연동창구 수집(2026-10-29) — 한국 바깥 정부·통계청·국제기구·대학이 여는 열쇠 없는 창구에서 원산지 시세·세계 상품값·재난·주산지 날씨를 날마다 받는다.
#   대장: tools/global_apis.json. 결과: site/data/global.json(계열·재난·날씨·상태) + private/global/cepea.json(세페아 일별 누적).
#   계열(series) 하나 = {name, unit, src, country, freq, last, date, chg{w1,w4,m3,y1}, points[[날짜, 값]…]} — collect_world 가 'global' 감지 규칙과 원산지 '재난'·'날씨' 갈래로 읽는다.
#   어느 창구가 막혀도 나머지는 받고, 막힌 창구는 어제 값(이전 global.json)을 그대로 두고 stale 표시.
import sys, os, re, io, csv, json, math, time, zipfile, datetime, statistics, collections, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
HERE = os.path.dirname(os.path.abspath(__file__))
REG = jload(os.path.join(HERE, 'global_apis.json'), {'sources': []})
OLD = jload(os.path.join(DATA, 'global.json'), {}) or {}
TODAY = now().date(); TS = TODAY.isoformat(); T0 = time.time(); BUDGET = 600
MSG = []; SER = {}; ST = {}
UA = {'User-Agent': 'Mozilla/5.0 (compatible; bakssifarm-global/1.0; +https://thecloudstay.github.io/bakssifarm/)', 'Accept': 'application/json,text/csv,text/xml,*/*'}
def over(): return time.time() - T0 > BUDGET
def fetch(url, params=None, timeout=60, data=None, headers=None):
    if params: url += ('&' if '?' in url else '?') + urllib.parse.urlencode(params, doseq=True)
    h = dict(UA); h.update(headers or {})
    req = urllib.request.Request(url, headers=h, data=data, method='POST' if data is not None else 'GET')
    with urllib.request.urlopen(req, timeout=timeout) as r: return r.read()
def chg(points, back):
    """points 오름차순 [(날짜, 값)], back 개 전 대비 %"""
    if len(points) <= back or not points[-1 - back][1]: return None
    return round((points[-1][1] / points[-1 - back][1] - 1) * 100, 1)
def series(sid, name, unit, src, country, freq, points, steps):
    """steps = {'w1': 1, 'w4': 4, 'm3': 13, 'y1': 52} 처럼 창 이름 → 몇 점 전"""
    pts = sorted((d, float(v)) for d, v in points if v is not None and not (isinstance(v, float) and math.isnan(v)))
    if not pts: raise ValueError('빈 계열')
    SER[sid] = {'name': name, 'unit': unit, 'src': src, 'country': country, 'freq': freq, 'last': pts[-1][1], 'date': pts[-1][0], 'chg': {k: chg(pts, n) for k, n in steps.items()}, 'points': [[d, round(v, 4)] for d, v in pts[-80:]]}
    return SER[sid]
def keep_old(sid):
    o = (OLD.get('series') or {}).get(sid)
    if o: SER[sid] = dict(o, stale=True)
def run(key, fn):
    if over(): ST[key] = '시간 예산 초과'; return
    try:
        fn(); ST[key] = '정상'
    except Exception as e:
        ST[key] = '실패 ' + str(e)[:120]; MSG.append(f'{key} {str(e)[:80]}')

# ── 노르웨이 통계청: 연어 수출 주간 ㎏당 값(신선) ─────────────────
def ssb():
    q = {"query": [{"code": "VareGrupper2", "selection": {"filter": "item", "values": ["01"]}}, {"code": "ContentsCode", "selection": {"filter": "item", "values": ["Kilopris", "Vekt"]}}, {"code": "Tid", "selection": {"filter": "top", "values": ["60"]}}], "response": {"format": "json-stat2"}}
    j = json.loads(fetch('https://data.ssb.no/api/v0/en/table/03024/', data=json.dumps(q).encode(), headers={'Content-Type': 'application/json'}))
    dims = j['id']; size = j['size']; val = j['value']
    tid = j['dimension']['Tid']['category']['index']; cc = j['dimension']['ContentsCode']['category']['index']
    def at(ic, it):   # 차원 순서 id 대로 평탄 색인
        idx = {'VareGrupper2': 0, 'ContentsCode': ic, 'Tid': it}; k = 0
        for d, s in zip(dims, size): k = k * s + idx[d]
        return val[k]
    def wk2date(w):   # 2026U43 → 그 주 금요일 날짜
        y, n = int(w[:4]), int(w[-2:]); return datetime.date.fromisocalendar(y, n, 5).isoformat()
    pts = [(wk2date(w), at(cc['Kilopris'], i)) for w, i in sorted(tid.items(), key=lambda x: x[1])]
    vol = [(wk2date(w), at(cc['Vekt'], i)) for w, i in sorted(tid.items(), key=lambda x: x[1])]
    s = series('no_salmon_fresh', '노르웨이 신선 연어 수출가', '크로네/㎏', '노르웨이 통계청 03024', '노르웨이', '주', pts, {'w1': 1, 'w4': 4, 'm3': 13, 'y1': 52})
    s['vol'] = [[d, v] for d, v in vol[-80:] if v is not None]
run('ssb_salmon', ssb)

# ── 유럽연합 농식품 창구: 돼지고기 S등급·닭고기 주간 ─────────────
def eu_prices(kind, params):
    d0 = (TODAY - datetime.timedelta(days=400)).strftime('%d/%m/%Y'); d1 = TODAY.strftime('%d/%m/%Y')
    j = json.loads(fetch(f'https://www.ec.europa.eu/agrifood/api/{kind}/prices', dict(params, beginDate=d0, endDate=d1), timeout=90))
    return j
def num(s):
    m = re.search(r'-?\d[\d,]*\.?\d*', str(s).replace(',', ''))
    try: return float(m.group(0).replace(',', '')) if m else None
    except ValueError: return None
def eu_pig():
    j = eu_prices('pigmeat', {'memberStateCodes': 'DE,ES,NL,FR,BE,IT,AT'})   # 유로 쓰는 나라만(폴란드·덴마크는 자국 통화라 섞으면 안 됨)
    by = collections.defaultdict(dict)
    for r in j:
        if r.get('pigClass') == 'S' and '100' in str(r.get('unit', '')) and str(r.get('price', '')).strip().startswith('€'):
            d = datetime.datetime.strptime(r['endDate'], '%d/%m/%Y').date().isoformat(); v = num(r.get('price'))
            if v: by[d][r.get('memberStateCode')] = v
    pts = [(d, statistics.median(v.values())) for d, v in by.items() if len(v) >= 3]   # 그 주 3개국 넘게 있을 때만, 중앙값(구성 변화에 덜 흔들림)
    series('eu_pig_s', '유럽연합 돼지고기 S등급 도축장 값(유로권 중앙값)', '유로/100㎏', '유럽연합 집행위 농식품 창구', '유럽연합', '주', pts, {'w1': 1, 'w4': 4, 'm3': 13, 'y1': 52})
run('eu_pig', eu_pig)
def eu_poultry():
    j = eu_prices('poultry', {'memberStateCodes': 'DE,FR,ES,NL,IT,BE'})   # 유로권만
    by = collections.defaultdict(dict)
    for r in j:
        pn = str(r.get('productName', '')).lower()
        if ('broiler' in pn or 'whole' in pn) and 'selling' in str(r.get('priceType', '')).lower() and str(r.get('price', '')).strip().startswith('€'):
            d = datetime.datetime.strptime(r['endDate'], '%d/%m/%Y').date().isoformat(); v = num(r.get('price'))
            if v: by[d][r.get('memberStateCode')] = v
    pts = [(d, statistics.median(v.values())) for d, v in by.items() if len(v) >= 3]
    series('eu_broiler', '유럽연합 통닭(육계 65%) 판매가(유로권 중앙값)', '유로/100㎏', '유럽연합 집행위 농식품 창구', '유럽연합', '주', pts, {'w1': 1, 'w4': 4, 'm3': 13, 'y1': 52})
run('eu_poultry', eu_poultry)

# ── 미국 농무부 의무보고: 쇠고기 박스육 초이스 도매값(주간) ───────
def usda_beef():
    d0 = (TODAY - datetime.timedelta(days=400)).strftime('%m/%d/%Y'); d1 = TODAY.strftime('%m/%d/%Y')
    j = json.loads(fetch('https://mpr.datamart.ams.usda.gov/services/v1.1/reports/2461/Weekly%20Average%20Cutout%20Values', {'q': f'report_date={d0}:{d1}'}, timeout=120))
    pts = []
    for r in j.get('results', []):
        d = r.get('report_date'); v = num(r.get('choice_600_900_simple_avg'))
        if d and v: pts.append((datetime.datetime.strptime(d, '%m/%d/%Y').date().isoformat(), v))
    if not pts: raise ValueError('초이스 값 열을 못 찾음: ' + ','.join(list((j.get('results') or [{}])[0].keys())[:12]))
    series('us_beef_choice', '미국 쇠고기 박스육 초이스 도매값(주간)', '달러/100파운드', '미국 농무부 의무보고 LM_XB459', '미국', '주', pts, {'w1': 1, 'w4': 4, 'm3': 13, 'y1': 52})
run('usda_beef', usda_beef)
def usda_section(rid, section, days=120):
    d0 = (TODAY - datetime.timedelta(days=days)).strftime('%m/%d/%Y'); d1 = TODAY.strftime('%m/%d/%Y')
    j = json.loads(fetch(f'https://mpr.datamart.ams.usda.gov/services/v1.1/reports/{rid}/{urllib.parse.quote(section)}', {'q': f'report_date={d0}:{d1}'}, timeout=120))
    return j.get('results') or []
def pick_key(rows, pats):
    """행 묶음에서 값이 숫자인 열 가운데 이름이 패턴에 맞는 첫 열(열 이름을 모를 때)"""
    keys = collections.Counter()
    for r in rows[:30]:
        for k, v in r.items():
            if num(v) is not None and any(re.search(p, k.lower()) for p in pats): keys[k] += 1
    return keys.most_common(1)[0][0] if keys else None
def usda_hog():
    rows = usda_section(2511, 'Barrows/Gilts')
    k = pick_key(rows, [r'wtd.*avg.*price|avg.*net.*price|net_price|weighted_avg'])
    if not k: raise ValueError('생돈 값 열 못 찾음: ' + ','.join(list((rows or [{}])[0].keys())[:14]))
    by = {}
    for r in rows:
        d = r.get('report_date') or r.get('for_date_begin'); v = num(r.get(k))
        if d and v: by.setdefault(datetime.datetime.strptime(d, '%m/%d/%Y').date().isoformat(), []).append(v)
    series('us_hog_net', '미국 생돈 도축 전일 평균 순가격(암퇘지 제외)', '달러/100파운드', '미국 농무부 의무보고 LM_HG201 ' + k, '미국', '일', [(d, statistics.mean(v)) for d, v in by.items()], {'w1': 5, 'w4': 20, 'm3': 60, 'y1': 250})
run('usda_hog', usda_hog)
def usda_cattle():
    rows = usda_section(2466, 'Detail')
    k = pick_key(rows, [r'wtd.*avg.*price|weighted_avg_price|avg_price'])
    if not k: raise ValueError('생우 값 열 못 찾음: ' + ','.join(list((rows or [{}])[0].keys())[:14]))
    by = {}
    for r in rows:
        txt = json.dumps(r).lower()
        if 'live' not in txt or 'steer' not in txt: continue   # 생체 거세우만
        d = r.get('report_date'); v = num(r.get(k))
        if d and v: by.setdefault(datetime.datetime.strptime(d, '%m/%d/%Y').date().isoformat(), []).append(v)
    if not by: raise ValueError('생체 거세우 행 없음(열 ' + k + ')')
    series('us_steer_live', '미국 5개 지역 거세우 생체 가중평균 값', '달러/100파운드', '미국 농무부 의무보고 LM_CT100 ' + k, '미국', '일', [(d, statistics.mean(v)) for d, v in by.items()], {'w1': 5, 'w4': 20, 'm3': 60, 'y1': 250})
run('usda_cattle', usda_cattle)

# ── 브라질 세페아: 비육우·육계·돼지·옥수수·대두 지표(일별, 누적 저장) ──
CEP_P = os.path.join(PRIVATE, 'global', 'cepea.json'); os.makedirs(os.path.dirname(CEP_P), exist_ok=True)
CEP = jload(CEP_P, {})
CEP_MAP = {'boi': ('br_cattle', '브라질 비육우(상파울루) 지표', '헤알/아로바'), 'frango': ('br_chicken', '브라질 육계(냉장 도매) 지표', '헤알/㎏'), 'suíno': ('br_hog', '브라질 생돈 지표', '헤알/㎏'), 'suino': ('br_hog', '브라질 생돈 지표', '헤알/㎏'),
           'milho': ('br_corn', '브라질 옥수수(캄피나스) 지표', '헤알/60㎏'), 'soja': ('br_soy', '브라질 대두(파라나과) 지표', '헤알/60㎏')}
def cepea():
    t = fetch('https://www.cepea.esalq.usp.br/br/widgetproduto.js.php', {'fonte': 'arial', 'tamanho': '10', 'largura': '400px', 'corfundo': 'dbd6b2', 'cortexto': '333333', 'corlinha': 'ede7bf', 'id_indicador[]': ['2', '130', '129', '77', '92', '53', '54', '181', '12', '91']}, timeout=60).decode('utf-8', 'replace')
    rows = []
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S):
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.S)
        if len(cells) == 3: rows.append(cells)
    got = 0
    for a, b, c in rows:
        a, b, c = (re.sub('<[^>]+>', '', x).strip() for x in (a, b, c))
        m = re.match(r'(\d{2})/(\d{2})/(\d{4})', a)
        if not m: continue
        d = f'{m.group(3)}-{m.group(2)}-{m.group(1)}'
        v = c.replace('R$', '').replace('.', '').replace(',', '.').strip(); v = num(v)
        key = next((k for k in CEP_MAP if k in b.lower()), None)
        if not key or v is None: continue
        sid = CEP_MAP[key][0]; CEP.setdefault(sid, {})[d] = v; got += 1
    if not got: raise ValueError('표에서 지표를 못 읽음 (' + str(len(rows)) + '줄) ' + re.sub(r'\s+', ' ', re.sub('<[^>]+>', '|', t))[-300:])
    jsave(CEP_P, CEP)
    for key, (sid, nm, unit) in CEP_MAP.items():
        if sid in SER or sid not in CEP: continue
        pts = sorted(CEP[sid].items())
        series(sid, nm, unit, '상파울루대 세페아 지표', '브라질', '일', pts, {'w1': 5, 'w4': 20, 'm3': 60, 'y1': 250})
run('cepea', cepea)

# ── 유엔 식량농업기구 식량가격지수(월별) ─────────────────────────
def fao():
    mons = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    cands = [mons[(TODAY.month - 1 - k) % 12] for k in range(3)]
    txt = None
    for m in cands:
        try: txt = fetch(f'https://www.fao.org/fileadmin/templates/worldfood/Reports_and_docs/Food_price_indices_data_{m}.csv', timeout=60).decode('utf-8', 'replace'); break
        except Exception: continue
    if txt is None:
        h = fetch('https://www.fao.org/worldfoodsituation/foodpricesindex/en/', timeout=60).decode('utf-8', 'replace')
        m = re.search(r'(/fileadmin/templates/worldfood/Reports_and_docs/Food_price_indices_data[^"\']*\.csv)', h)
        if not m: raise ValueError('지수 파일 주소를 못 찾음')
        txt = fetch('https://www.fao.org' + m.group(1), timeout=60).decode('utf-8', 'replace')
    allrows = list(csv.reader(io.StringIO(txt)))
    rows = []
    for r in allrows:
        if not r or not r[0].strip(): continue
        a = r[0].strip(); m = re.match(r'(\d{4})-(\d{2})', a) or re.match(r'(\d{4})(\d{2})$', a)
        if m: rows.append([f'{m.group(1)}-{m.group(2)}'] + r[1:]); continue
        try: d = datetime.datetime.strptime(a, '%b-%Y'); rows.append([d.strftime('%Y-%m')] + r[1:]); continue
        except ValueError: pass
        try: d = datetime.datetime.strptime(a, '%Y-%m-%d'); rows.append([d.strftime('%Y-%m')] + r[1:])
        except ValueError: pass
    MSG.append('식량농업기구 꼬리 행 ' + json.dumps(allrows[-4:], ensure_ascii=False)[:300])
    cols = {'food': 1, 'meat': 2, 'dairy': 3, 'cereals': 4, 'oils': 5, 'sugar': 6}
    names = {'food': '세계 식량가격지수', 'meat': '세계 육류가격지수', 'dairy': '세계 유제품가격지수', 'cereals': '세계 곡물가격지수', 'oils': '세계 식물성유지가격지수', 'sugar': '세계 설탕가격지수'}
    for k, i in cols.items():
        pts = []
        for r in rows:
            try: pts.append((r[0] + '-01', float(r[i])))
            except (ValueError, IndexError): pass
        series('fao_fpi_' + k, names[k], '2014~16년=100', '유엔 식량농업기구', '세계', '월', pts, {'w1': 1, 'w4': 3, 'm3': 6, 'y1': 12})
run('fao_fpi', fao)

# ── 세계은행 상품값 월별(요소·인산이암모늄·대두박·어분·옥수수·밀·팜유·원유) ──
def wb():
    import openpyxl
    url = 'https://thedocs.worldbank.org/en/doc/18675f1d1639c7a34d463f59263ba0a2-0050012025/related/CMO-Historical-Data-Monthly.xlsx'
    try:
        h = fetch('https://www.worldbank.org/en/research/commodity-markets', timeout=60).decode('utf-8', 'replace')
        m = re.search(r'https://thedocs\.worldbank\.org/[^"\s]+?CMO-Historical-Data-Monthly\.xlsx', h)
        if m: url = m.group(0)
        else: MSG.append('세계은행 안내 화면에서 월별 파일 주소 못 찾음 — 예전 주소 사용')
    except Exception as e: MSG.append('세계은행 안내 화면 ' + str(e)[:40])
    b = fetch(url, timeout=120)
    wbk = openpyxl.load_workbook(io.BytesIO(b), read_only=True, data_only=True)
    ws = wbk['Monthly Prices'] if 'Monthly Prices' in wbk.sheetnames else wbk[wbk.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(rows[:12]) if r and sum(1 for c in r if isinstance(c, str)) > 10)
    head = [str(c or '').strip() for c in rows[hi]]
    want = {'wb_urea': ('Urea', '요소(비료) 세계값', '달러/톤'), 'wb_dap': ('DAP', '인산이암모늄(비료) 세계값', '달러/톤'), 'wb_soymeal': ('Soybean meal', '대두박 세계값', '달러/톤'), 'wb_fishmeal': ('Fish meal', '어분 세계값', '달러/톤'),
            'wb_maize': ('Maize', '옥수수 세계값', '달러/톤'), 'wb_wheat': ('Wheat, US HRW', '밀(미국 경질) 세계값', '달러/톤'), 'wb_palm': ('Palm oil', '팜유 세계값', '달러/톤'), 'wb_crude': ('Crude oil, average', '원유 평균값', '달러/배럴'), 'wb_beef': ('Beef', '쇠고기(호주 수출) 세계값', '달러/㎏'), 'wb_chicken': ('Chicken', '닭고기(미국) 세계값', '달러/㎏'), 'wb_shrimp': ('Shrimps', '새우(멕시코) 세계값', '달러/㎏')}
    for sid, (col, nm, unit) in want.items():
        ci = next((i for i, h in enumerate(head) if h.lower().startswith(col.lower())), None)
        if ci is None: MSG.append(f'세계은행 열 없음 {col}'); continue
        pts = []
        for r in rows[hi + 1:]:
            if not r or not r[0]: continue
            m = re.match(r'(\d{4})M(\d{2})', str(r[0]))
            if not m: continue
            v = r[ci]
            if isinstance(v, (int, float)): pts.append((f'{m.group(1)}-{m.group(2)}-01', float(v)))
        if pts: series(sid, nm, unit, '세계은행 상품 시장 월별 값표', '세계', '월', pts, {'w1': 1, 'w4': 3, 'm3': 6, 'y1': 12})
run('wb_pink', wb)

# ── 세계 재난 경보(유엔·유럽연합): 원산지 나라 재난 ───────────────
EN2KO = {c['en']: c['ko'] for c in (jload(os.path.join(HERE, 'origin_risks.json'), {}).get('countries') or [])}
EN2KO.update({'United States of America': '미국', 'Russian Federation': '러시아', 'Viet Nam': '베트남', 'Korea, Republic of': '한국', 'Republic of Korea': '한국', 'South Korea': '한국', 'Taiwan, Province of China': '대만', 'Iran': '이란', 'Türkiye': '튀르키예', 'Turkey': '튀르키예', 'Bolivia': '볼리비아', 'South Africa': '남아공', 'United Kingdom': '영국', 'Falkland Islands': '포클랜드'})
GD = []
def gdacs():
    t = fetch('https://www.gdacs.org/xml/rss.xml', timeout=90).decode('utf-8', 'replace')
    TYPE = {'EQ': '지진', 'TC': '태풍·허리케인', 'FL': '홍수', 'DR': '가뭄', 'WF': '산불', 'VO': '화산'}
    for it in re.findall(r'<item>(.*?)</item>', t, re.S):
        def tag(n):
            m = re.search(rf'<{n}[^>]*>(.*?)</{n}>', it, re.S); return re.sub(r'<!\[CDATA\[|\]\]>', '', m.group(1)).strip() if m else ''
        et = tag('gdacs:eventtype'); lv = tag('gdacs:alertlevel'); cn = tag('gdacs:country'); ttl = tag('title'); dt_ = tag('gdacs:fromdate') or tag('pubDate')
        if lv not in ('Orange', 'Red'): continue
        try: d = datetime.datetime.strptime(dt_[:25].strip(), '%a, %d %b %Y %H:%M:%S').date()
        except Exception:
            try: d = datetime.datetime.fromisoformat(dt_[:19]).date()
            except Exception: d = TODAY
        if (TODAY - d).days > 14: continue
        kos = sorted({EN2KO[c.strip()] for c in re.split(r'[,;]', cn) if c.strip() in EN2KO})
        GD.append({'type': TYPE.get(et, et), 'level': 2 if lv == 'Red' else 1, 'country': cn, 'ko': kos, 'title': ttl[:120], 'date': d.isoformat(), 'sev': tag('gdacs:severity')[:80]})
    GD.sort(key=lambda x: (-x['level'], x['date']), reverse=False)
run('gdacs', gdacs)

# ── 미국 항공우주국 농업 기상: 원산지 주산지 18곳 30일 기온·강수 대 평년 ──
PTS = [('브라질', '마투그로수(대두·옥수수·면화)', -15.6, -56.1, '대두박|옥수수'), ('브라질', '파라나(육계·대두)', -25.4, -51.5, '닭고기|대두박'), ('브라질', '히우그란지두술(쌀·대두·돼지)', -30.0, -53.0, '돼지고기|대두박'),
       ('아르헨티나', '팜파스(대두·옥수수·밀)', -34.0, -61.0, '대두박|옥수수|밀'), ('미국', '아이오와(옥수수·대두·돼지)', 42.0, -93.5, '옥수수|대두박|돼지고기'), ('미국', '캔자스(밀·소)', 38.5, -98.0, '밀|쇠고기'), ('미국', '텍사스 팬핸들(비육우)', 35.2, -101.8, '쇠고기'),
       ('호주', '뉴사우스웨일스(밀·소)', -32.0, 148.0, '밀|쇠고기'), ('우크라이나', '중부 흑토(밀·옥수수·해바라기)', 49.0, 32.0, '밀|옥수수'), ('베트남', '메콩 삼각주(새우·쌀·과일)', 10.0, 105.8, '새우|용과|망고'), ('태국', '중부 평원(닭·새우·쌀)', 14.5, 100.5, '닭고기|새우'),
       ('필리핀', '민다나오(바나나·파인애플)', 7.5, 125.0, '바나나|파인애플'), ('에콰도르', '과야스(새우·바나나)', -2.2, -79.9, '새우|바나나'), ('칠레', '중부(포도·체리)', -33.5, -70.7, '포도|체리'), ('인도', '펀자브(밀·쌀)', 30.9, 75.8, '밀'),
       ('중국', '산둥(마늘·양파·채소)', 36.7, 117.0, '마늘|양파|당근|고추'), ('중국', '동북 3성(옥수수·콩)', 43.9, 125.3, '옥수수|대두'), ('인도네시아', '수마트라(팜유·커피)', -0.5, 101.4, '팜유')]
WX = []
def nasa():
    d1 = TODAY - datetime.timedelta(days=3); d0 = d1 - datetime.timedelta(days=29)
    for ko, name, lat, lon, items in PTS:
        if over(): break
        try:
            j = json.loads(fetch('https://power.larc.nasa.gov/api/temporal/daily/point', {'parameters': 'T2M,PRECTOTCORR', 'community': 'AG', 'longitude': lon, 'latitude': lat, 'start': d0.strftime('%Y%m%d'), 'end': d1.strftime('%Y%m%d'), 'format': 'JSON'}, timeout=60))
            c = json.loads(fetch('https://power.larc.nasa.gov/api/temporal/climatology/point', {'parameters': 'T2M,PRECTOTCORR', 'community': 'AG', 'longitude': lon, 'latitude': lat, 'format': 'JSON'}, timeout=60))
            P = j['properties']['parameter']; C = c['properties']['parameter']
            t = [v for v in P['T2M'].values() if v is not None and v > -900]; p = [v for v in P['PRECTOTCORR'].values() if v is not None and v > -900]
            if len(t) < 15: raise ValueError('일수 부족')
            MON = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
            mk = MON[d1.month - 1]; ct = C['T2M'].get(mk); cp = C['PRECTOTCORR'].get(mk)
            ta = round(statistics.mean(t) - ct, 1) if ct is not None else None
            pm = statistics.mean(p)   # 30일 일평균 강수(㎜/일)
            pr = round(pm / cp, 2) if (cp and cp >= 1.0) else None   # 평년 일평균이 1㎜/일 아래인 건기엔 비율을 쓰지 않음(0으로 나눠 폭주)
            lv = 0; why = []
            if ta is not None and ta >= 4.0: lv = 2; why.append(f'30일 기온 평년보다 {ta:+.1f}℃(폭염)')
            elif ta is not None and ta >= 2.5: lv = 1; why.append(f'30일 기온 평년보다 {ta:+.1f}℃')
            if pr is not None and pr <= 0.25: lv = max(lv, 2); why.append(f'30일 강수 평년의 {int(pr * 100)}%(가뭄)')
            elif pr is not None and pr <= 0.45: lv = max(lv, 1); why.append(f'30일 강수 평년의 {int(pr * 100)}%(건조)')
            elif pr is not None and pr >= 3.0: lv = max(lv, 2); why.append(f'30일 강수 평년의 {pr:.1f}배(홍수)')
            elif pr is not None and pr >= 2.0: lv = max(lv, 1); why.append(f'30일 강수 평년의 {pr:.1f}배(다우)')
            elif pr is None and pm >= 6.0: lv = max(lv, 1); why.append(f'건기인데 30일 일평균 {pm:.1f}㎜(이례적 비)')
            lv = min(lv, 1)   # 2026-10-29 검증 전: 위성 기상 판정은 「주의」까지만(경보는 몇 주 기록 뒤 문턱을 맞춘 다음)
            WX.append({'ko': ko, 'name': name, 'lat': lat, 'lon': lon, 'items': items, 't_anom': ta, 'p_ratio': pr, 'p_mm': round(pm, 1), 'level': lv, 'why': ' · '.join(why) or '평년 안', 'to': d1.isoformat()})
        except Exception as e:
            MSG.append(f'날씨 {name} {str(e)[:50]}')
    if not WX: raise ValueError('한 곳도 못 받음')
run('nasa_power', nasa)

# ── 막힌 창구는 어제 값 유지 ────────────────────────────────────
for sid in (OLD.get('series') or {}):
    if sid not in SER: keep_old(sid)
if not GD and OLD.get('gdacs') and ST.get('gdacs', '').startswith('실패'): GD = [dict(x, stale=True) for x in OLD['gdacs']]
if not WX and OLD.get('weather') and ST.get('nasa_power', '').startswith('실패'): WX = [dict(x, stale=True) for x in OLD['weather']]
reg_status = {}
for s in REG.get('sources', []):
    k = s['id']; st = ST.get({'ssb_salmon': 'ssb_salmon', 'eu_agrifood': 'eu_pig', 'usda_mpr': 'usda_beef', 'cepea': 'cepea', 'fao_fpi': 'fao_fpi', 'wb_pink': 'wb_pink', 'gdacs': 'gdacs', 'nasa_power': 'nasa_power'}.get(k, ''), None)
    if k == 'usda_mpr': st = ' · '.join(f'{n} {ST.get(n, "")}' for n in ('usda_beef', 'usda_hog', 'usda_cattle'))
    reg_status[k] = st
out = {'at': stamp(), 'date': TS, 'series': SER, 'gdacs': GD[:40], 'weather': WX, 'status': ST, 'reg_status': reg_status, 'n_series': len(SER), 'n_fresh': sum(1 for v in SER.values() if not v.get('stale')), 'msgs': MSG[:20], 'elapsed_sec': round(time.time() - T0)}
jsave(os.path.join(DATA, 'global.json'), out)
ok = sum(1 for v in ST.values() if v == '정상'); bad = [k for k, v in ST.items() if v != '정상']
os.makedirs(os.path.join(HERE, '_debug'), exist_ok=True)
jsave(os.path.join(HERE, '_debug', 'global_debug.json'), {'at': out['at'], 'elapsed': out['elapsed_sec'], 'status': ST, 'msgs': MSG, 'series': {k: {'last': v['last'], 'date': v['date'], 'chg': v['chg'], 'n': len(v['points']), 'stale': v.get('stale', False)} for k, v in SER.items()}, 'gdacs': GD[:15], 'weather': WX})
status('global', ok >= max(3, len(ST) // 2), f'창구 {ok}/{len(ST)} 정상 · 계열 {len(SER)}(새 값 {out["n_fresh"]}) · 재난 {len(GD)} · 주산지 날씨 {len(WX)}' + (f' · 막힘 {", ".join(bad)}' if bad else '') + f' · {out["elapsed_sec"]}초')
print('세계 창구', ST, '계열', list(SER)[:20], '재난', len(GD), '날씨', [(w['ko'], w['level']) for w in WX], out['elapsed_sec'], '초')
