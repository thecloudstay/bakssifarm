# 세계·국내 요인 감시(2026-10-28, 같은 날 2차 확장) — 값을 흔드는 바깥 요인을 열쇠 없는 공개 자료로 매일 재서
#   site/data/world.json (요인·단계·근거·영향 품목·품목별 원산지 노출) 과 private/world/날짜.json (기록) 으로 남긴다.
#   구매 신호(수산·농산)·축산 판단은 world_lib.world_adjust() 로 이 결과를 점수에 더한다(갈래별 상한).
# 층:
#   ① 주제 요인 36개(world_rules.json): 엘니뇨·수온·태풍·질병·지정학·정책·세계 상품·달력
#   ② 원산지 요인(origin_risks.json × import_matrix.json): 수입 품목 원산지 57개 나라마다 공급 충격·정치/무역·통화·엘니뇨 영향권 → 그 나라에서 오는 품목의 국내 경쟁·하류 품목
#   ③ 국내 주산지 날씨(crop_points.json): 32개 주산지 7일 예보로 서리·폭염·호우·강풍 → 산지 품목
#   ④ 국내 수요 달력: 설·추석·김장·복날·연말·가정의 달·휴가·개학
#   ⑤ 확인 메모(world_notes.json)
# 자료(모두 열쇠 없음): GDELT 세계 뉴스 흐름(5초 간격, 429 때 물러남) → 안 되면 구글 뉴스 RSS 로 대신, 미 해양대기청 엘니뇨 지수,
#   위성 수온 이상(여러 ERDDAP 거울 → 안 되면 오픈메테오 3년 같은 날짜 평균 대비), 미 연준 경제자료(국제통화기금 상품값·환율), 미 지질조사국, 합동태풍경보센터, 오픈메테오 7일 예보.
# 뉴스 흐름은 「그 이야기가 평소보다 많이 나온다」는 뜻이지 사실 확인이 아니다. 화면에도 그렇게 적는다.
import sys, os, re, io, csv, json, math, time, datetime, statistics, collections, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
HERE = os.path.dirname(os.path.abspath(__file__))
R = jload(os.path.join(HERE, 'world_rules.json'), {'rules': []})
IM = jload(os.path.join(HERE, 'import_matrix.json'), {'items': []})
OR = jload(os.path.join(HERE, 'origin_risks.json'), {'countries': []})
CP = jload(os.path.join(HERE, 'crop_points.json'), {'points': []})
NOTES = jload(os.path.join(HERE, 'world_notes.json'), {}).get('notes', [])
GL = jload(os.path.join(DATA, 'global.json'), {}) or {}   # 세계 공개 연동창구(collect_global.py) — 원산지 시세·세계 상품값·재난·주산지 날씨
GSER = GL.get('series') or {}
FC = jload(os.path.join(DATA, 'forecast.json'), {})
OLD = jload(os.path.join(DATA, 'world.json'), {})
OLD_EV = {e['id']: e for e in OLD.get('events') or []}
TODAY = now().date(); TS = TODAY.isoformat()
UA = {'User-Agent': 'Mozilla/5.0 (compatible; bakssifarm-world/1.1; +https://thecloudstay.github.io/bakssifarm/)'}
MSG = []; T0 = time.time()
BUDGET = int(os.environ.get('WORLD_BUDGET_SEC') or 1080)   # 전체 18분 안에 끝냄 — 넘으면 남은 뉴스 질의는 어제 값/건너뜀
def over(): return time.time() - T0 > BUDGET
OUT_LOG = os.path.join(PRIVATE, 'world'); os.makedirs(OUT_LOG, exist_ok=True)
CURSOR_P = os.path.join(OUT_LOG, 'cursor.json'); CUR = jload(CURSOR_P, {'tier2_pos': 0})

def fetch(url, params=None, timeout=30, retry=1):
    return get(url, params, timeout=timeout, retry=retry, headers=UA)

# ── 뉴스 흐름: GDELT(주) + 구글 뉴스 RSS(보조) ────────────────
GD_SLEEP = 5.2; gd_429 = 0; gd_off = False
_gd_cache = {}
def gdelt_raw(params, timeout=25):
    global gd_429, gd_off
    if gd_off or over(): return None
    for attempt in range(2):
        try:
            b = fetch('https://api.gdeltproject.org/api/v2/doc/doc', params, timeout=timeout, retry=1)
            time.sleep(GD_SLEEP)
            t = b.decode('utf-8', 'replace')
            if not t.strip().startswith('{'): raise ValueError('json 아님: ' + t[:40])
            gd_429 = 0; return json.loads(t)
        except Exception as e:
            s = str(e)
            if '429' in s:
                gd_429 += 1; time.sleep(20)
                if gd_429 >= 2: gd_off = True; MSG.append('GDELT 429 연속 — 오늘은 구글 뉴스로 대신'); return None
                continue
            MSG.append('gdelt ' + s[:60]); return None
    return None
def gnews(q):
    """구글 뉴스 RSS — 최근 7일 기사 수 대 그 앞 7일. (ratio, last7, prev7, titles)"""
    try:
        lang = 'ko' if re.search(r'[가-힣]', q) else 'en'
        q2 = re.sub(r'\s*sourcelang:\w+', '', q)
        url = 'https://news.google.com/rss/search?' + urllib.parse.urlencode({'q': q2 + ' when:14d', 'hl': 'ko' if lang == 'ko' else 'en-US', 'gl': 'KR' if lang == 'ko' else 'US', 'ceid': 'KR:ko' if lang == 'ko' else 'US:en'})
        t = fetch(url, timeout=25, retry=1).decode('utf-8', 'replace'); time.sleep(1.0)
        items = re.findall(r'<item>(.*?)</item>', t, re.S)
        n7 = n14 = 0; titles = []
        for it in items:
            m = re.search(r'<pubDate>(.*?)</pubDate>', it)
            try: d = datetime.datetime.strptime(m.group(1).strip()[:25], '%a, %d %b %Y %H:%M:%S').date() if m else None
            except Exception: d = None
            if not d: continue
            age = (TODAY - d).days
            if age <= 7: n7 += 1
            elif age <= 14: n14 += 1
            if age <= 7 and len(titles) < 3:
                tt = re.search(r'<title>(.*?)</title>', it, re.S); src = re.search(r'<source[^>]*>(.*?)</source>', it)
                lk = re.search(r'<link>(.*?)</link>', it)
                if tt: titles.append({'t': re.sub(r'\s+', ' ', re.sub(r'<!\[CDATA\[|\]\]>', '', tt.group(1))).strip()[:90], 'u': (lk.group(1).strip() if lk else ''), 'd': d.strftime('%Y%m%d'), 's': (src.group(1) if src else '')[:20]})
        ratio = round(n7 / max(n14, 1), 2) if (n7 or n14) else None
        return {'ratio': ratio, 'last7': n7, 'prev7': n14, 'titles': titles, 'src': '구글 뉴스'}
    except Exception as e:
        return {'ratio': None, 'err': str(e)[:60]}
def news(q, want_titles=False):
    """(z, ratio, titles, src, stale). GDELT 12주 비교가 기본, 막히면 구글 뉴스 2주 비교, 그것도 안 되면 어제 값."""
    if q in _gd_cache: return _gd_cache[q]
    res = {'z': None, 'ratio': None, 'titles': [], 'src': '', 'err': ''}
    j = gdelt_raw({'query': q, 'mode': 'timelinevol', 'timespan': '12w', 'format': 'json'})
    if j:
        vals = [float(x.get('value') or 0) for x in ((j.get('timeline') or [{}])[0].get('data') or [])]
        if len(vals) >= 21:
            last7 = vals[-7:]; base = vals[:-7]; m7 = statistics.mean(last7); mb = statistics.mean(base); sd = statistics.pstdev(base) or (mb * 0.5) or 1e-9
            res.update({'z': round((m7 - mb) / sd, 2), 'ratio': round(m7 / mb, 2) if mb > 0 else (9.9 if m7 > 0 else 1.0), 'src': 'GDELT 12주'})
    if res['ratio'] is None and not over():
        g = gnews(q)
        if g.get('ratio') is not None:
            r = g['ratio']; res.update({'ratio': r, 'z': round((r - 1) * 2, 2), 'last7': g['last7'], 'prev7': g['prev7'], 'src': f'구글 뉴스 2주({g["last7"]}/{g["prev7"]}건)', 'titles': g.get('titles') or []})
        else: res['err'] = g.get('err', '')
    _gd_cache[q] = res; return res
def news_titles(q, n=3):
    if over(): return []
    j = gdelt_raw({'query': q, 'mode': 'artlist', 'maxrecords': 8, 'sort': 'datedesc', 'format': 'json'})
    out, seen = [], set()
    for a in (j or {}).get('articles') or []:
        t = re.sub(r'\s+', ' ', a.get('title') or '').strip()
        if not t or t[:30] in seen: continue
        seen.add(t[:30]); out.append({'t': t[:90], 'u': a.get('url', ''), 'd': (a.get('seendate') or '')[:8], 's': a.get('domain', '')})
        if len(out) >= n: break
    if not out:
        g = gnews(q); out = g.get('titles') or []
    return out
def lv_from_news(g):
    """뉴스 흐름만으로는 「주의」(1)까지만 — 경보(2)는 측정값(엘니뇨 지수·수온·상품값·지진·태풍 경보·달력)이 있을 때만"""
    return min(1, _lv_news_raw(g))
def _lv_news_raw(g):
    z, r = g.get('z'), g.get('ratio')
    if z is None or r is None: return 0
    if g.get('src', '').startswith('구글'):   # 2주 비교는 거칠어서 기사 수 하한을 둠
        n7 = g.get('last7', 0)
        return 2 if r >= 3.0 and n7 >= 20 else 1 if r >= 1.8 and n7 >= 6 else 0
    if z >= 3 and r >= 2.0: return 2
    if z >= 1.5 and r >= 1.4: return 1
    return 0
def lv_from_pct(v, warn, alarm):
    if v is None: return 0
    return 2 if abs(v) >= alarm else 1 if abs(v) >= warn else 0

# ── 자료별 측정 ──────────────────────────────────────────────
def oni():
    try:
        t = fetch('https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt', timeout=30).decode('ascii', 'replace')
        rows = [l.split() for l in t.strip().splitlines()[1:] if len(l.split()) >= 4]
        vals = [(r[0], int(r[1]), float(r[3])) for r in rows]
        if not vals: return None
        last = vals[-1]; prev = vals[-2] if len(vals) > 1 else last
        return {'season': last[0], 'year': last[1], 'anom': last[2], 'prev': prev[2], 'phase': '엘니뇨' if last[2] >= 0.5 else '라니냐' if last[2] <= -0.5 else '중립', 'strong': abs(last[2]) >= 1.0, 'hist': [v[2] for v in vals[-8:]]}
    except Exception as e:
        MSG.append('oni ' + str(e)[:60]); return None

SST_PTS = [('서해 중부', 36.6, 125.6), ('서해 남부', 34.8, 125.6), ('남해 서부', 34.3, 127.3), ('남해 동부', 34.6, 128.3), ('동해 남부', 36.0, 129.9), ('동해 중부', 37.8, 129.3), ('제주 남쪽', 33.0, 126.5)]
def sst_anom():
    # ① 위성 수온 이상(산호초감시 5㎞) — ERDDAP 거울 몇 곳
    for host, ds in (('https://pae-paha.pacioos.hawaii.edu/erddap', 'dhw_5km'), ('https://coastwatch.noaa.gov/erddap', 'noaacrwsstanomalyDaily'), ('https://coastwatch.pfeg.noaa.gov/erddap', 'NOAA_DHW')):
        out = []
        for nm, la, lo in SST_PTS:
            try:
                u = f'{host}/griddap/{ds}.csv?CRW_SSTANOMALY%5B(last)%5D%5B({la}):({la})%5D%5B({lo}):({lo})%5D'
                t = fetch(u, timeout=30, retry=1).decode('utf-8', 'replace')
                rows = [r for r in csv.reader(io.StringIO(t)) if r and r[0][:2] == '20']
                if rows and rows[-1][-1] not in ('', 'NaN'): out.append({'name': nm, 'anom': round(float(rows[-1][-1]), 2), 'date': rows[-1][0][:10], 'src': '위성 수온 이상(산호초감시)'})
            except Exception as e:
                MSG.append(f'sst {host.split("//")[1][:22]} {nm} {str(e)[:30]}'); break
        if len(out) >= 4: return out
    # ② 오픈메테오 바다 예보/과거: 최근 7일 평균 대 지난 3년 같은 기간 평균(평년 대신 3년 평균 — 화면에 그렇게 적음)
    try:
        la = ','.join(str(p[1]) for p in SST_PTS); lo = ','.join(str(p[2]) for p in SST_PTS)
        def days(y):
            e = TODAY.replace(year=y); s = e - datetime.timedelta(days=7)
            j = json.loads(fetch('https://marine-api.open-meteo.com/v1/marine', {'latitude': la, 'longitude': lo, 'daily': 'sea_surface_temperature_max', 'start_date': s.isoformat(), 'end_date': (e - datetime.timedelta(days=1)).isoformat(), 'timezone': 'Asia/Seoul'}, timeout=40).decode())
            arr = j if isinstance(j, list) else [j]
            return [statistics.mean([v for v in (x.get('daily') or {}).get('sea_surface_temperature_max', []) if v is not None] or [float('nan')]) for x in arr]
        cur = days(TODAY.year); base = [days(TODAY.year - k) for k in (1, 2, 3)]
        out = []
        for i, (nm, _, _) in enumerate(SST_PTS):
            bs = [b[i] for b in base if i < len(b) and not math.isnan(b[i])]
            if i < len(cur) and not math.isnan(cur[i]) and bs: out.append({'name': nm, 'anom': round(cur[i] - statistics.mean(bs), 2), 'date': TS, 'src': '오픈메테오 3년 같은 기간 대비'})
        return out
    except Exception as e:
        MSG.append('sst 오픈메테오 ' + str(e)[:60]); return []

def fred(series_id):
    try:
        b = fetch('https://fred.stlouisfed.org/graph/fredgraph.csv', {'id': series_id}, timeout=30, retry=1).decode('utf-8', 'replace')
        out = []
        for row in csv.reader(io.StringIO(b)):
            if len(row) < 2 or not row[0][:2].isdigit(): continue
            try: out.append((row[0], float(row[1])))
            except ValueError: pass
        if len(out) < 4: return None
        last = out[-1][1]; m1 = out[-2][1]; m3 = out[-4][1] if len(out) > 3 else None; y1 = out[-13][1] if len(out) > 12 else None
        return {'id': series_id, 'date': out[-1][0][:7], 'last': last, 'c1': round((last / m1 - 1) * 100, 1) if m1 else None, 'c3': round((last / m3 - 1) * 100, 1) if m3 else None, 'c12': round((last / y1 - 1) * 100, 1) if y1 else None, 'n': len(out)}
    except Exception as e:
        MSG.append(f'fred {series_id} {str(e)[:40]}'); return None
def stale(ym, months=8):
    """연월 문자열이 지금보다 months 개월 넘게 오래됐으면 참(끊긴 지표를 2023년 값으로 쓰는 일 막기)"""
    try: y, m = int(ym[:4]), int(ym[5:7]); return (TODAY.year - y) * 12 + (TODAY.month - m) > months
    except Exception: return False
def oecd_series(key, flow='OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0', n=18):
    """경제협력개발기구 공개 통계(열쇠 없음) — 월별 [(연월, 값)] 최근 n개"""
    try:
        b = fetch(f'https://sdmx.oecd.org/public/rest/data/{flow}/{key}', {'lastNObservations': n, 'format': 'csvfile'}, timeout=40, retry=1).decode('utf-8', 'replace')
        rows = list(csv.reader(io.StringIO(b)))
        if not rows: return None
        hd = rows[0]; it = hd.index('TIME_PERIOD') if 'TIME_PERIOD' in hd else None; iv = hd.index('OBS_VALUE') if 'OBS_VALUE' in hd else None
        if it is None or iv is None: MSG.append('oecd 열 이름 다름 ' + ','.join(hd)[:60]); return None
        out = []
        for r in rows[1:]:
            try: out.append((r[it][:7], float(r[iv])))
            except (ValueError, IndexError): pass
        out.sort()
        return out or None
    except Exception as e:
        MSG.append(f'oecd {key[:24]} {str(e)[:40]}'); return None
def fred_daily(series_id, back=66):
    """일별 환율: 마지막 값과 3개월(66거래일) 전 대비 %"""
    try:
        b = fetch('https://fred.stlouisfed.org/graph/fredgraph.csv', {'id': series_id}, timeout=30, retry=1).decode('utf-8', 'replace')
        out = []
        for row in csv.reader(io.StringIO(b)):
            if len(row) < 2 or not row[0][:2].isdigit(): continue
            try: out.append((row[0], float(row[1])))
            except ValueError: pass
        if len(out) < back + 1: return None
        return {'id': series_id, 'date': out[-1][0], 'last': out[-1][1], 'c3': round((out[-1][1] / out[-1 - back][1] - 1) * 100, 1), 'c1': round((out[-1][1] / out[-23][1] - 1) * 100, 1)}
    except Exception as e:
        MSG.append(f'fx {series_id} {str(e)[:40]}'); return None
_fx_cache = {}
def fx_of(c):
    f = c.get('fx')
    if not f: return None
    if f['id'] not in _fx_cache: _fx_cache[f['id']] = fred_daily(f['id'])
    d = _fx_cache[f['id']]
    if not d: return None
    strong = -d['c3'] if f.get('per_usd') else d['c3']   # 그 나라 통화가 달러 대비 강해진 % (수입 단가 ↑ 쪽)
    return {'strong3': round(strong, 1), 'date': d['date'], 'id': f['id']}

def usgs(box, mmin):
    try:
        j = json.loads(fetch('https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson', timeout=30).decode('utf-8', 'replace'))
        out = []
        for f in j.get('features', []):
            lo, la = f['geometry']['coordinates'][:2]; m = f['properties'].get('mag') or 0
            if box[0] <= la <= box[1] and box[2] <= lo <= box[3] and m >= mmin:
                out.append({'mag': m, 'place': f['properties'].get('place', ''), 'time': datetime.datetime.utcfromtimestamp(f['properties']['time'] / 1000).strftime('%m-%d')})
        return sorted(out, key=lambda x: -x['mag'])
    except Exception as e:
        MSG.append('usgs ' + str(e)[:50]); return None
def jtwc():
    try:
        t = fetch('https://www.metoc.navy.mil/jtwc/rss/jtwc.rss', timeout=30, retry=1).decode('utf-8', 'replace')
        titles = re.findall(r'<title>(.*?)</title>', t, re.S)
        return [re.sub(r'\s+', ' ', x).strip() for x in titles if re.search(r'\b\d{2}W\b', x) or 'Western' in x or 'West Pacific' in x]
    except Exception as e:
        MSG.append('jtwc ' + str(e)[:50]); return None
def tile(key): return next((t for t in (FC.get('tiles') or []) if t.get('key') == key), None)

FROST_OCT = {'배추', '무', '풋고추', '홍고추', '꽈리고추', '깻잎', '상추', '시금치', '대파', '쪽파', '감귤', '단감', '떫은감', '오이', '호박', '가지', '토마토', '방울토마토', '파프리카', '멜론', '부추', '열무', '얼갈이배추', '청경채', '미나리'}
def crop_weather():
    """주산지 32곳 7일 예보 → 서리·폭염·호우·강풍 사건"""
    pts = CP.get('points') or []
    if not pts: return []
    try:
        j = json.loads(fetch('https://api.open-meteo.com/v1/forecast', {'latitude': ','.join(str(p['lat']) for p in pts), 'longitude': ','.join(str(p['lon']) for p in pts),
                                'daily': 'temperature_2m_min,temperature_2m_max,precipitation_sum,wind_gusts_10m_max', 'forecast_days': 7, 'timezone': 'Asia/Seoul'}, timeout=40).decode())
        arr = j if isinstance(j, list) else [j]
    except Exception as e:
        MSG.append('주산지 날씨 ' + str(e)[:60]); return []
    out = []; m = TODAY.month
    for p, x in zip(pts, arr):
        d = x.get('daily') or {}; tmin = d.get('temperature_2m_min') or []; tmax = d.get('temperature_2m_max') or []; pr = d.get('precipitation_sum') or []; gu = d.get('wind_gusts_10m_max') or []
        ev = []
        tm = min((v for v in tmin if v is not None), default=99)
        if m in (4, 5) and tm <= 1.0: ev.append(('서리', f'최저 {tm:.0f}℃(개화·정식기)', 2 if tm <= -1 else 1))
        elif m == 10 and tm <= 0.0 and any(c in FROST_OCT for c in p['crops']): ev.append(('서리', f'최저 {tm:.0f}℃(첫서리)', 1))
        hot = sum(1 for v in tmax if v is not None and v >= 33)
        if hot >= 2: ev.append(('폭염', f'33℃ 넘는 날 {hot}일', 2 if hot >= 4 else 1))
        p3 = max((sum(v for v in pr[i:i + 3] if v is not None) for i in range(max(1, len(pr) - 2))), default=0)
        if p3 >= 120: ev.append(('호우', f'3일 강수 {p3:.0f}㎜', 2 if p3 >= 200 else 1))
        g = max((v for v in gu if v is not None), default=0)
        if g >= 72: ev.append(('강풍', f'돌풍 {g:.0f}㎞/h', 2 if g >= 90 else 1))
        for kind, txt, lv in ev: out.append({'point': p['name'], 'kind': kind, 'text': txt, 'level': lv, 'crops': p['crops']})
    return out

def cal_state(kind):
    H = R.get('holidays') or {}; m, d = TODAY.month, TODAY.day
    if kind == 'holiday':
        best = None
        for nm, ds in H.items():
            for s in ds:
                dd = datetime.date.fromisoformat(s); k = (dd - TODAY).days
                if -21 <= k <= 45 and (best is None or abs(k) < abs(best[1])): best = (nm, k, s)
        if not best: return 0, '', None
        nm, k, s = best
        return ((2 if k <= 14 else 1), f'{nm}({s}) {k}일 전 — 명절 수요 구간', 'before') if k >= 0 else (1, f'{nm}({s}) {-k}일 지남 — 명절 뒤 되돌림 구간', 'after')
    if kind == 'kimjang':
        if (m == 10 and d >= 25) or m == 11: return (2 if m == 11 and d <= 20 else 1), '김장철 수요 구간', 'before'
        if m == 12 and d <= 20: return 1, '김장 뒤 되돌림 구간', 'after'
    if kind == 'summer' and ((m == 7 and d >= 10) or (m == 8 and d <= 20)): return 1, '여름 휴가철 횟감 수요', 'before'
    if kind == 'school' and ((m in (2, 8) and d >= 18) or (m in (3, 9) and d <= 10)): return 1, '개학 급식 수요', 'before'
    if kind == 'bokdays' and ((m == 7 and d >= 8) or (m == 8 and d <= 16)): return (2 if (m == 7 and d >= 12) or (m == 8 and d <= 12) else 1), '삼복(초복~말복) 보양식 수요', 'before'
    if kind == 'yearend' and m == 12 and d <= 26: return (2 if d >= 10 else 1), '연말 모임·선물 수요', 'before'
    if kind == 'may' and m == 5 and d <= 10: return 1, '가정의 달(어린이날·어버이날) 외식·선물 수요', 'before'
    return 0, '', None
EXTRA_CAL = [
    {'id': 'bokdays', 'cat': '수요·달력', 'name': '삼복 보양식 수요', 'kind': 'bokdays', 'why': '초복~말복 닭·오리·장어 수요 집중', 'react': '닭고기·오리 6월 말 선계약, 뱀장어 물량 확보',
     'affects_before': [{'sector': '축산', 'item': '닭|육계|오리', 'dir': '오름 쪽', 'w': 0.3}, {'sector': '수산', 'item': '뱀장어|붕장어|갯장어|전복|낙지|민어', 'dir': '오름 쪽', 'w': 0.25}]},
    {'id': 'yearend', 'cat': '수요·달력', 'name': '연말 모임·선물 수요', 'kind': 'yearend', 'why': '12월 회식·선물로 한우·삼겹·횟감·대게 수요', 'react': '11월 말까지 한우 선물 원물·횟감 확보',
     'affects_before': [{'sector': '축산', 'item': '한우|돼지', 'dir': '오름 쪽', 'w': 0.2}, {'sector': '수산', 'item': '방어|참돔|넙치|붉은대게|대게|굴|전복', 'dir': '오름 쪽', 'w': 0.2}]},
    {'id': 'may', 'cat': '수요·달력', 'name': '가정의 달 수요', 'kind': 'may', 'why': '어린이날·어버이날 외식·선물', 'react': '4월 말 한우·돼지 물량',
     'affects_before': [{'sector': '축산', 'item': '한우|돼지', 'dir': '오름 쪽', 'w': 0.15}, {'sector': '농산', 'item': '딸기|참외|수박|토마토', 'dir': '오름 쪽', 'w': 0.1}]},
]
EXTRA_NEWS = [   # 국내 정책·원가 요인(뉴스 흐름)
    {'id': 'kr_discount', 'cat': '정책', 'name': '정부 농축수산물 할인·물가 대책', 'q': '(농축산물 OR 수산물) (할인지원 OR 할인행사 OR 물가안정대책) sourcelang:korean', 'lag': '0~3주',
     'why': '정부 할인 행사는 해당 품목 소비를 끌어올리고, 물가 대책은 수입 확대·비축 방출로 값을 누름', 'react': '할인 대상 품목은 수요 증가, 대책 품목은 매입 미루기',
     'affects': [{'sector': '축산', 'item': '한우|돼지|계란', 'dir': '오름 쪽', 'w': 0.1, 'why': '할인 행사 수요'}, {'sector': '농산', 'item': '사과|배|배추|무|양파|마늘', 'dir': '내림 쪽', 'w': 0.1, 'why': '물가 대책(수입·방출)'}], 'src': '뉴스 흐름 · 농림축산식품부·해양수산부'},
    {'id': 'kr_energy', 'cat': '정책', 'name': '농사용 전기요금·면세유 인상', 'q': '(전기요금 OR 면세유) (농사용 OR 어업용 OR 양식장 OR 시설재배) 인상 sourcelang:korean', 'lag': '1~3개월',
     'why': '시설채소 난방·양식장 전기·어선 유류 원가', 'react': '겨울 시설채소·양식어 계약 단가 재검토',
     'affects': [{'sector': '농산', 'item': '오이|호박|가지|토마토|방울토마토|딸기|파프리카|풋고추|상추|깻잎', 'dir': '오름 쪽', 'w': 0.1}, {'sector': '수산', 'item': '넙치|조피볼락|뱀장어|새우|대하', 'dir': '오름 쪽', 'w': 0.1}], 'src': '뉴스 흐름'},
    {'id': 'kr_labor', 'cat': '정책', 'name': '외국인 계절근로자·인건비', 'q': '(계절근로자 OR 농촌 인력 OR 외국인 선원) (부족 OR 인건비 OR 임금) sourcelang:korean', 'lag': '1~3개월',
     'why': '수확기 인력 부족은 과채·엽채 출하 지연, 어선 선원 부족은 조업 축소', 'react': '수확기 집중 품목 선계약',
     'affects': [{'sector': '농산', 'item': '사과|배|배추|무|마늘|양파|고추|풋고추|홍고추|딸기|포도', 'dir': '오름 쪽', 'w': 0.1}, {'sector': '수산', 'item': '고등어|갈치|오징어|멸치', 'dir': '오름 쪽', 'w': 0.1}], 'src': '뉴스 흐름'},
    {'id': 'kr_herd', 'cat': '국내 수급', 'name': '사육두수·입식 급변(관측 보도)', 'q': '(사육두수 OR 입식 OR 산란계 마릿수 OR 모돈) (감소 OR 급감 OR 증가) 관측 sourcelang:korean', 'lag': '1~6개월',
     'why': '사육두수 감소 보도가 늘면 몇 달 뒤 출하 감소', 'react': '축산 장기 계약 검토',
     'affects': [{'sector': '축산', 'item': '한우|돼지|계란|닭', 'dir': '오름 쪽', 'w': 0.1}], 'src': '뉴스 흐름 · 한국농촌경제연구원 관측'},
    {'id': 'kr_fishing_ban', 'cat': '국내 수급', 'name': '금어기·휴어기·조업 통제', 'q': '(금어기 OR 휴어기 OR 조업 중단 OR 출항 통제) (어선 OR 어업 OR 수협) sourcelang:korean', 'lag': '0~4주',
     'why': '금어기 시작은 선어 공급 공백, 해제는 공급 몰림', 'react': '금어기 품목은 냉동 대체, 해제 뒤 매입',
     'affects': [{'sector': '수산', 'item': '꽃게|오징어|살오징어|고등어|갈치|참조기|대구|낙지|문어|전어', 'dir': '오름 쪽', 'w': 0.15}], 'src': '뉴스 흐름 · 해양수산부'},
]

# ── ① 주제 요인 ──────────────────────────────────────────────
events = []; ONI = None; SST = None; JT = None
def mk(r, typ): return {'id': r['id'], 'cat': r['cat'], 'name': r['name'], 'level': 0, 'value': '', 'text': '', 'why': r.get('why', ''), 'react': r.get('react', ''), 'lag': r.get('lag', ''), 'src': r.get('src', ''), 'affects': [], 'kind': typ, 'titles': []}
def finish(ev, aff, q=None):
    old = OLD_EV.get(ev['id']) or {}
    if ev.get('_news_failed') and old.get('level') is not None and old.get('kind') == ev['kind'] and 'news' in old:
        ev['level'] = old['level']; ev['text'] = (old.get('text') or '') + ' (어제 값 — 오늘 뉴스 자료 못 받음)'; ev['stale'] = True; ev['titles'] = old.get('titles') or []
    if ev['level'] and q and not ev.get('titles') and not ev.get('stale'): ev['titles'] = news_titles(q)
    if ev['level']: ev['affects'] = [dict(a, w=round(a['w'] * ev['level'], 2)) for a in (aff or [])]
    ev.pop('_news_failed', None)
    events.append(ev)
for r in R.get('rules', []):
    dt = r.get('detect') or {}; typ = dt.get('type', ''); ev = mk(r, typ); aff = r.get('affects') or []
    try:
        if typ == 'oni':
            ONI = ONI or oni()
            if ONI:
                ev.update({'level': 2 if ONI['strong'] else 1 if ONI['phase'] != '중립' else 0, 'value': f'{ONI["anom"]:+.1f}', 'text': f'{ONI["season"]} {ONI["year"]} 지수 {ONI["anom"]:+.1f} — {ONI["phase"]}' + (' 강함' if ONI['strong'] else '') + f' (앞 계절 {ONI["prev"]:+.1f})', 'hist': ONI['hist']})
                aff = r.get('affects_elnino' if ONI['phase'] == '엘니뇨' else 'affects_lanina' if ONI['phase'] == '라니냐' else 'affects') or []
            else: ev['text'] = '자료 못 받음'
        elif typ == 'sst':
            SST = SST if SST is not None else sst_anom()
            if SST:
                mean = statistics.mean(x['anom'] for x in SST); hi = max(SST, key=lambda x: x['anom']); lo = min(SST, key=lambda x: x['anom'])
                ev.update({'level': 2 if mean >= 1.5 or hi['anom'] >= 2.5 else 1 if mean >= 1.0 or hi['anom'] >= 1.8 or mean <= -1.0 else 0, 'value': f'{mean:+.1f}℃',
                           'text': f'7개 해역 평균 {mean:+.1f}℃ · 가장 높은 곳 {hi["name"]} {hi["anom"]:+.1f}℃ · 가장 낮은 곳 {lo["name"]} {lo["anom"]:+.1f}℃ ({SST[0]["src"]}, {SST[0]["date"]})', 'points': SST})
                aff = r.get('affects_hi') if mean >= 0 else r.get('affects_lo')
            else: ev['text'] = '자료 못 받음'
        elif typ == 'usgs':
            q = usgs(dt.get('box', [24, 46, 122, 146]), dt.get('warn', 6.0))
            if q is None: ev['text'] = '자료 못 받음'
            elif q: top = q[0]; ev.update({'level': 2 if top['mag'] >= dt.get('alarm', 7.0) else 1, 'value': f'규모 {top["mag"]}', 'text': f'최근 7일 규모 {dt.get("warn", 6.0)} 이상 {len(q)}건 — 가장 큰 것 규모 {top["mag"]} {top["place"]} ({top["time"]})'})
            else: ev['text'] = f'최근 7일 규모 {dt.get("warn", 6.0)} 이상 없음'
        elif typ in ('fred', 'fred+gdelt'):
            got = next((g for g in (fred(sid) for sid in dt.get('series', [])) if g), None)
            if got:
                v = got['c3'] if got['c3'] is not None else got['c1']
                ev.update({'level': lv_from_pct(v, dt.get('warn', 10), dt.get('alarm', 20)), 'value': f'{v:+.1f}%(3개월)', 'text': f'{got["date"]} 기준 {got["last"]:,.1f} · 1개월 {got["c1"]:+.1f}% · 3개월 {(got["c3"] or 0):+.1f}% · 1년 {(got["c12"] or 0):+.1f}%'})
                if v is not None and v < 0: aff = []
            else: ev['text'] = '자료 못 받음(지표 이름 확인 필요)'
            if typ == 'fred+gdelt' and dt.get('q'):
                g = news(dt['q']); ev['news'] = g
                if lv_from_news(g) > ev['level']: ev['level'] = lv_from_news(g); ev['text'] += f' · 뉴스 흐름 평소의 {g["ratio"]}배'
        elif typ == 'fred_multi':
            parts = []; worst = 0; direction = 0
            for k, sid in (dt.get('series') or {}).items():
                got = fred(sid)
                if not got: continue
                v = got['c3'] if got['c3'] is not None else got['c1']; nm = {'poultry': '닭고기', 'beef': '쇠고기', 'shrimp': '새우'}.get(k, k)
                parts.append(f'{nm} {v:+.1f}%'); l = lv_from_pct(v, dt.get('warn', 8), dt.get('alarm', 15))
                if l > worst or (l == worst and abs(v) > abs(direction)): worst, direction = l, v
            ev.update({'level': worst, 'value': ' · '.join(parts), 'text': '세계 값 3개월 변동 — ' + (' · '.join(parts) or '자료 못 받음')})
            aff = (r.get('affects_up') if direction > 0 else r.get('affects_down')) if worst else []
        elif typ == 'jtwc+gdelt':
            JT = JT if JT is not None else jtwc(); g = news(dt['q']); ev['news'] = g
            lv = 0
            if JT and 6 <= TODAY.month <= 11: lv = 2 if lv_from_news(g) >= 1 else 1   # 실제 태풍 경보가 있어야 켬, 한반도 뉴스까지 많으면 경보
            ev.update({'level': lv, 'value': f'서태평양 활동 {len(JT or [])}개', 'text': ('서태평양 태풍 경보 ' + ', '.join(JT[:3]) if JT else '서태평양 태풍 경보 없음' if JT is not None else '태풍 경보 자료 못 받음') + (f' · 한반도 태풍 뉴스 평소의 {g["ratio"]}배' if g.get('ratio') else '')})
        elif typ in ('tiles', 'tiles+gdelt'):
            vals = [(t['name'], t['c20'], t.get('c60')) for t in (tile(k) for k in dt.get('keys', [])) if t and t.get('c20') is not None]
            lv = 0; txt = []
            for nm, c20, c60 in vals:
                lv = max(lv, lv_from_pct(c20 if c20 > 0 else 0, dt.get('warn', 8), dt.get('alarm', 15))); txt.append(f'{nm} 1개월 {c20:+.1f}%' + (f'·3개월 {c60:+.1f}%' if c60 is not None else ''))
            if typ == 'tiles+gdelt' and dt.get('q'):
                g = news(dt['q']); ev['news'] = g
                if g.get('ratio'): txt.append(f'뉴스 흐름 평소의 {g["ratio"]}배'); lv = max(lv, lv_from_news(g))
            ev.update({'level': lv, 'value': ' · '.join(f'{c20:+.1f}%' for _, c20, _ in vals), 'text': ' · '.join(txt) or '자료 없음'})
        elif typ == 'gdelt':
            g = news(dt['q']); ev['news'] = g
            if g.get('ratio') is None: ev['_news_failed'] = True; ev['text'] = '뉴스 흐름 자료 못 받음 ' + g.get('err', '')
            else: ev.update({'level': lv_from_news(g), 'value': f'뉴스 {g["ratio"]}배', 'text': f'최근 7일 관련 기사가 평소의 {g["ratio"]}배 ({g["src"]})', 'titles': g.get('titles') or []})
        elif typ == 'fred_yoy':   # 전년 동월 대비 % — 경제협력개발기구 직접(열쇠 없음) 먼저, 미 연준 경유는 보조
            got = None
            if dt.get('oecd'):
                o = oecd_series(dt['oecd'])
                if o and not stale(o[-1][0]):
                    got = {'date': o[-1][0], 'c12': round(o[-1][1], 1), 'c3': round(o[-1][1] - o[-4][1], 1) if len(o) > 3 else None, 'src': '경제협력개발기구 직접'}
            if not got:
                f = next((g for g in (fred(sid) for sid in dt.get('series', [])) if g), None)
                if f and f.get('c12') is not None and not stale(f['date']): got = {'date': f['date'], 'c12': f['c12'], 'c3': f['c3'], 'src': '미 연준 경제자료 경유'}
                elif f: ev['text'] = f'자료가 오래됨({f["date"]}까지) — 점수 반영 안 함'
            if got:
                v = got['c12']; ev.update({'level': lv_from_pct(max(v, 0), dt.get('warn', 3), dt.get('alarm', 4.5)), 'value': f'{v:+.1f}%(전년 대비)', 'text': f'{got["date"]} 기준 전년 동월 대비 {v:+.1f}%' + (f' · 3개월 전 상승률 대비 {got["c3"]:+.1f}%p' if got.get('c3') is not None else '') + f' ({got["src"]})'})
                if v < 0: aff = []
            elif not ev.get('text'): ev['text'] = '자료 못 받음(지표 이름 확인 필요)'
        elif typ == 'fred_diff':   # 3개월 전 대비 %p(금리)
            got = None
            for sid in dt.get('series', []):
                try:
                    b2 = fetch('https://fred.stlouisfed.org/graph/fredgraph.csv', {'id': sid}, timeout=30, retry=1).decode('utf-8', 'replace')
                    rows = [(r[0], float(r[1])) for r in csv.reader(io.StringIO(b2)) if len(r) > 1 and r[0][:2].isdigit() and r[1] not in ('', '.')]
                    if len(rows) >= 4: got = {'date': rows[-1][0][:7], 'last': rows[-1][1], 'd3': round(rows[-1][1] - rows[-4][1], 2), 'd12': round(rows[-1][1] - rows[-13][1], 2) if len(rows) > 12 else None}; break
                except Exception as e: MSG.append(f'fred {sid} {str(e)[:40]}')
            if got:
                v = got['d3']; ev.update({'level': lv_from_pct(v, dt.get('warn', 0.5), dt.get('alarm', 1.0)), 'value': f'{got["last"]:.2f}% ({v:+.2f}%p/3개월)', 'text': f'{got["date"]} 기준 {got["last"]:.2f}% · 3개월 전 대비 {v:+.2f}%p' + (f' · 1년 전 대비 {got["d12"]:+.2f}%p' if got.get('d12') is not None else '')})
                aff = (r.get('affects_up') if v > 0 else r.get('affects_down')) if ev['level'] else []
            else: ev['text'] = '자료 못 받음(지표 이름 확인 필요)'
        elif typ == 'fred_level':   # 수준 지표(소비자심리): 기준 아래면 켬
            got = next((g for g in (fred(sid) for sid in dt.get('series', [])) if g), None)
            if got and stale(got['date']): ev['text'] = f'자료가 오래됨({got["date"]}까지) — 점수 반영 안 함'
            elif got:
                v = got['last']; nt = dt.get('neutral_text', '100 아래면 비관')
                ev.update({'level': 2 if v <= dt.get('alarm', 98) else 1 if v <= dt.get('warn', 99) else 0, 'value': f'{v:.1f}', 'text': f'{got["date"]} 기준 {v:.1f} ({nt})'})
            else: ev['text'] = '자료 못 받음(지표 이름 확인 필요)'
        elif typ == 'minwage':   # 최저임금 표: 그해 인상률, 1~4월에 켬
            tb = dt.get('table') or {}; y = str(TODAY.year); y0 = str(TODAY.year - 1)
            if y in tb and y0 in tb:
                pct = round((tb[y] / tb[y0] - 1) * 100, 1)
                on = TODAY.month <= 4
                ev.update({'level': (lv_from_pct(pct, dt.get('warn', 3), dt.get('alarm', 5)) if on else 0), 'value': f'{tb[y]:,}원({pct:+.1f}%)', 'text': f'{y}년 시급 {tb[y]:,}원, 전년 대비 {pct:+.1f}%' + ('' if on else ' — 연초(1~4월)에만 점수 반영')})
            else: ev['text'] = f'{y}년 결정액이 표에 없음 — 확인 메모로 추가'
        elif typ == 'global':   # 세계 공개 연동창구 계열(collect_global.py): 창(w1·w4·m3·y1) 변화율로 단계, 오르면 affects_up·내리면 affects_down
            g = GSER.get(dt.get('series') or '')
            if not g: ev['text'] = '자료 못 받음(세계 창구 ' + str(dt.get('series')) + ')'; aff = []
            else:
                win = dt.get('window', 'w4'); v = (g.get('chg') or {}).get(win)
                try: age = (TODAY - datetime.date.fromisoformat(g['date'][:10])).days
                except Exception: age = 0
                if age > {'일': 10, '주': 21, '월': 75}.get(g.get('freq'), 30): ev['text'] = f'{g["name"]} 자료가 오래됨({g["date"]}까지) — 점수 반영 안 함'; v = None; aff = []
                WN = {'w1': '1주', 'w4': '4주', 'm3': '3개월', 'y1': '1년'} if g.get('freq') in ('주', '월') else {'w1': '1주', 'w4': '1개월', 'm3': '3개월', 'y1': '1년'}
                if g.get('freq') == '월': WN = {'w1': '1개월', 'w4': '3개월', 'm3': '6개월', 'y1': '1년'}
                if v is None:
                    if not ev['text']: ev['text'] = f'{g["name"]} {g["last"]:,.2f} {g["unit"]} ({g["date"]}) — 비교할 지난 값이 아직 없음'
                    aff = []
                else:
                    ev.update({'level': lv_from_pct(abs(v), dt.get('warn', 8), dt.get('alarm', 15)), 'value': f'{v:+.1f}%({WN.get(win, win)})',
                               'text': f'{g["name"]} {g["last"]:,.2f} {g["unit"]} ({g["date"]}) · {WN.get(win, win)} {v:+.1f}%' + (' · 1년 ' + f'{g["chg"]["y1"]:+.1f}%' if (g.get('chg') or {}).get('y1') is not None else '') + (' (어제 값)' if g.get('stale') else ''), 'series': g['points'][-30:], 'unit': g.get('unit')})
                    aff = (r.get('affects_up') if v > 0 else r.get('affects_down')) or []
        elif typ == 'cal':
            lv, txt, ph = cal_state(dt.get('kind', '')); ev.update({'level': lv, 'text': txt or '해당 구간 아님'})
            aff = (r.get('affects_before') if ph == 'before' else r.get('affects_after') if ph == 'after' else []) or []
    except Exception as e:
        ev['text'] = '측정 실패 ' + str(e)[:60]; MSG.append(f'{r["id"]} {str(e)[:50]}')
    ev['affects_all'] = aff if aff else (r.get('affects') or r.get('affects_before') or r.get('affects_hi') or r.get('affects_up') or r.get('affects_elnino') or [])
    finish(ev, aff, dt.get('q'))
for r in EXTRA_CAL:
    ev = mk(dict(r, src='달력', lag=''), 'cal'); lv, txt, ph = cal_state(r['kind']); ev.update({'level': lv, 'text': txt or '해당 구간 아님'}); ev['affects_all'] = r['affects_before']
    finish(ev, r['affects_before'] if ph == 'before' else [])
for r in EXTRA_NEWS:
    ev = mk(r, 'gdelt'); g = news(r['q']); ev['news'] = g
    if g.get('ratio') is None: ev['_news_failed'] = True; ev['text'] = '뉴스 흐름 자료 못 받음'
    else: ev.update({'level': lv_from_news(g), 'value': f'뉴스 {g["ratio"]}배', 'text': f'최근 7일 관련 기사가 평소의 {g["ratio"]}배 ({g["src"]})', 'titles': g.get('titles') or []})
    ev['affects_all'] = r['affects']; finish(ev, r['affects'], r['q'])

# ── ② 원산지 요인 ────────────────────────────────────────────
by_country = collections.defaultdict(list)   # 나라 → [(수입품목, 비중)]
for it in IM.get('items', []):
    for c, s in it.get('origins', []): by_country[re.sub(r'\(.*?\)', '', c).strip()].append((it, s))
def country_affects(cko, base_w, dir_, why):
    """그 나라에서 오는 품목마다 국내 경쟁·하류 품목에 비중×전가×기본무게"""
    out = {}
    for it, s in by_country.get(cko, []):
        for role, key in (('경쟁', 'competes'), ('투입', 'inputs_for')):
            t = it.get(key)
            if not t: continue
            w = round(max(0.05, base_w * s * it.get('pt', 0.3)), 2)
            k = (t['sector'], t['item'])
            d = dir_ if not it.get('export') else ('내림 쪽' if dir_ == '오름 쪽' else '오름 쪽')   # 수출 품목은 수출처 충격이 국내 공급 과잉(값 내림)으로
            cand = {'sector': t['sector'], 'item': t['item'], 'dir': d, 'w': w, 'why': f'{cko} {why} → {it["name"]}(비중 {int(s * 100)}%) ' + ('수입 단가 ↑ → 국산 ' + ('↑' if d == '오름 쪽' else '↓') if role == '경쟁' else '원가 ↑ (시차 ' + it.get('lag', '') + ')')}
            if k not in out or out[k]['w'] < w: out[k] = cand
    return list(out.values())
CH = OR.get('channels') or {}; FXT = OR.get('fx_thresholds') or {'warn': 5, 'alarm': 10, 'w': 0.12}
countries = OR.get('countries') or []
t1 = [c for c in countries if c.get('tier', 2) == 1]; t2 = [c for c in countries if c.get('tier', 2) != 1]
pos = CUR.get('tier2_pos', 0) % max(1, len(t2)); rot = (t2[pos:] + t2[:pos])[:12]   # 2군은 하루 12개 나라씩 돌아가며
GD_BY = {}
for g in GL.get('gdacs') or []:
    for ko in g.get('ko') or []: GD_BY.setdefault(ko, []).append(g)
WX_BY = {}
for w in GL.get('weather') or []:
    if w.get('level'): WX_BY.setdefault(w['ko'], []).append(w)
extra = [c for c in t2 if c not in rot and (c['ko'] in GD_BY or c['ko'] in WX_BY)]   # 재난·날씨가 잡힌 나라는 순번과 무관하게 오늘 본다
origin_events = []
for c in t1 + rot + extra:
    cko = c['ko']; imports = by_country.get(cko, [])
    base = {'id': 'origin-' + cko, 'cat': '원산지', 'name': f'{cko} — ' + ', '.join(sorted({it['name'] for it, _ in imports})[:5]) + (' 외' if len(imports) > 5 else ''), 'kind': 'origin', 'country': cko, 'en': c['en'], 'route': c.get('route', ''), 'standing': c.get('standing', ''), 'tier': c.get('tier', 2), 'imports': [[it['name'], s] for it, s in sorted(imports, key=lambda x: -x[1])], 'titles': [], 'parts': []}
    lv = 0; txt = []; aff = {}
    # 공급 충격·정치/무역 뉴스
    for key in ('supply', 'trade'):
        ch = CH.get(key)
        if not ch or over(): continue
        q = ch['q'].replace('{EN}', c['en']); g = news(q)
        part = {'kind': ch['name'], 'ratio': g.get('ratio'), 'src': g.get('src', ''), 'level': lv_from_news(g) if g.get('ratio') is not None else None}
        if part['level'] is None:
            old = OLD_EV.get(base['id']) or {}; op = next((p for p in old.get('parts', []) if p.get('kind') == ch['name']), None)
            if op and op.get('level') is not None: part = dict(op, stale=True)
        base['parts'].append(part)
        if part.get('level'):
            lv = max(lv, part['level']); txt.append(f'{ch["name"]} 뉴스 평소의 {part.get("ratio")}배' + ('(어제 값)' if part.get('stale') else ''))
            for a in country_affects(cko, ch['w'] * part['level'], ch['dir'], ch['name'] + ' 뉴스 급증'):
                k = (a['sector'], a['item'])
                if k not in aff or aff[k]['w'] < a['w']: aff[k] = a
            if not base['titles'] and not part.get('stale'): base['titles'] = (g.get('titles') or news_titles(q))
    # 재난(세계 재난 경보 조정 체계 — 측정값, 경보까지 가능)
    for g in GD_BY.get(cko, [])[:3]:
        l = int(g.get('level') or 0)
        if not l: continue
        lv = max(lv, l); txt.append(f'재난 {g["type"]} {("빨강" if l == 2 else "주황")} 경보 ({g["date"]})' + (' (어제 값)' if g.get('stale') else ''))
        base['parts'].append({'kind': '재난', 'level': l, 'src': '세계 재난 경보 조정 체계', 'title': g.get('title', '')})
        for a in country_affects(cko, 0.35 * l, '오름 쪽', f'{g["type"]} 재난'):
            k = (a['sector'], a['item'])
            if k not in aff or aff[k]['w'] < a['w']: aff[k] = a
    # 주산지 날씨(미국 항공우주국 농업 기상 — 30일 평년 대비, 측정값)
    for w in WX_BY.get(cko, [])[:3]:
        l = int(w.get('level') or 0)
        lv = max(lv, l); txt.append(f'{w["name"]} {w["why"]}' + (' (어제 값)' if w.get('stale') else ''))
        base['parts'].append({'kind': '주산지 날씨', 'level': l, 'src': '미국 항공우주국 농업 기상', 'title': f'{w["name"]}: {w["why"]}'})
        for a in country_affects(cko, 0.3 * l, '오름 쪽', f'주산지 {w["why"][:14]}'):
            if not re.search(w.get('items') or '.', a.get('why', '')): continue   # 그 주산지 품목에 닿는 것만
            k = (a['sector'], a['item'])
            if k not in aff or aff[k]['w'] < a['w']: aff[k] = a
    # 통화
    fx = fx_of(c)
    if fx:
        l = lv_from_pct(fx['strong3'], FXT['warn'], FXT['alarm']); base['fx'] = fx
        if l:
            lv = max(lv, l); d = '오름 쪽' if fx['strong3'] > 0 else '내림 쪽'; txt.append(f'통화 3개월 달러 대비 {fx["strong3"]:+.1f}% → 수입 단가 {"↑" if d == "오름 쪽" else "↓"}')
            for a in country_affects(cko, FXT['w'] * l, d, f'통화 {"강세" if d == "오름 쪽" else "약세"}'): aff.setdefault((a['sector'], a['item']), a)
    # 엘니뇨·라니냐 영향권
    if ONI and ONI['phase'] in (c.get('enso') or {}):
        e = c['enso'][ONI['phase']]; l = 2 if (ONI['strong'] and c.get('enso_core')) else 1
        lv = max(lv, l); txt.append(f'{ONI["phase"]} 영향권: {e["text"]}')
        for a in country_affects(cko, OR.get('enso_w', 0.3) * l, e['dir'], ONI['phase'] + ' 영향'): aff.setdefault((a['sector'], a['item']), a)
    base.update({'level': lv, 'text': ' · '.join(txt) if txt else '조용함', 'affects': list(aff.values()) if lv else [], 'affects_all': country_affects(cko, 0.45, '오름 쪽', '공급 충격'), 'why': c.get('standing', ''), 'react': '수입 단가 변동 전 계약 조건 점검', 'lag': '2~8주(투입재는 2~7개월)', 'src': '뉴스 흐름 · 미 연준 경제자료 환율 · 엘니뇨 지수 · 세계 재난 경보 · 미국 항공우주국 농업 기상'})
    origin_events.append(base)
CUR['tier2_pos'] = (pos + len(rot)) % max(1, len(t2)); jsave(CURSOR_P, CUR)
events += origin_events

# ── ③ 국내 주산지 날씨 ────────────────────────────────────────
CW = crop_weather()
if CW:
    grp = collections.defaultdict(list)
    for e in CW: grp[e['kind']].append(e)
    for kind, es in grp.items():
        lv = max(e['level'] for e in es); crops = sorted({c for e in es for c in e['crops'] if kind != '서리' or TODAY.month != 10 or c in FROST_OCT})
        events.append({'id': 'kr_weather_' + {'서리': 'frost', '폭염': 'heat', '호우': 'rain', '강풍': 'wind'}.get(kind, kind), 'cat': '국내 날씨', 'name': f'주산지 {kind} 예보', 'kind': 'meteo', 'level': lv,
                       'text': '7일 안 ' + ', '.join(f'{e["point"]}({e["text"]})' for e in es[:8]) + (f' 외 {len(es) - 8}곳' if len(es) > 8 else ''), 'why': {'서리': '꽃·어린 과채 냉해로 착과·출하 감소', '폭염': '엽채 생육 불량·시들음, 과채 일소', '호우': '침수·병해·수확 지연', '강풍': '낙과·시설 파손'}.get(kind, ''),
                       'react': '해당 산지 품목 1~2주치 앞당겨 확보', 'lag': '0~3주', 'src': '오픈메테오 7일 예보 × 주산지 32곳', 'titles': [],
                       'affects': [{'sector': '농산', 'item': '|'.join(re.escape(x) for x in crops), 'dir': '오름 쪽', 'w': round(0.25 * lv, 2), 'why': f'주산지 {kind} 예보'}], 'affects_all': [{'sector': '농산', 'item': '|'.join(re.escape(x) for x in crops), 'dir': '오름 쪽', 'w': 0.25}]})
else:
    events.append({'id': 'kr_weather', 'cat': '국내 날씨', 'name': '주산지 32곳 7일 날씨(서리·폭염·호우·강풍)', 'kind': 'meteo', 'level': 0, 'text': '7일 안 기준 넘는 날씨 없음' if not any('주산지 날씨' in m for m in MSG) else '자료 못 받음', 'why': '주산지 날씨가 기준을 넘으면 그 산지 품목에 더함', 'react': '', 'lag': '0~3주', 'src': '오픈메테오 7일 예보', 'titles': [], 'affects': [], 'affects_all': []})

# ── ⑤ 확인 메모 ─────────────────────────────────────────────
for n in NOTES:
    if n.get('until') and n['until'] < TS: continue
    events.append({'id': 'note-' + re.sub(r'\W+', '', n.get('item', ''))[:20], 'cat': n.get('cat', '확인 메모'), 'name': n.get('item', ''), 'level': int(n.get('level', 1)), 'value': '', 'text': n.get('text', ''), 'why': n.get('why', ''), 'react': n.get('react', ''), 'lag': n.get('lag', ''), 'src': n.get('src', ''), 'kind': 'manual', 'titles': [],
                   'affects': [dict(a, w=round(a['w'] * int(n.get('level', 1)), 2)) for a in n.get('affects', [])], 'affects_all': n.get('affects', []), 'until': n.get('until', ''), 'date': n.get('date', '')})

# ── 품목별 원산지 노출(화면용) ────────────────────────────────
def hhi(origins): return round(sum(s * s for _, s in origins), 2)
exposure = {}
for it in IM.get('items', []):
    for role, key in (('경쟁', 'competes'), ('투입', 'inputs_for')):
        t = it.get(key)
        if not t: continue
        k = t['sector'] + '|' + t['item']
        exposure.setdefault(k, []).append({'import': it['name'], 'role': role, 'origins': it['origins'], 'hhi': hhi(it['origins']), 'pt': it.get('pt'), 'lag': it.get('lag', ''), 'scale': it.get('scale', ''), 'note': it.get('note', ''), 'export': bool(it.get('export'))})
origin_level = {e['country']: e['level'] for e in origin_events}

active = sorted([e for e in events if e['level']], key=lambda e: (-e['level'], e['cat']))
out = {'at': stamp(), 'date': TS, 'caps': R.get('caps') or {}, 'n_rules': len(events), 'n_topic': len(R.get('rules', [])) + len(EXTRA_CAL) + len(EXTRA_NEWS), 'n_origin': len(origin_events), 'n_origin_all': len(countries), 'n_import_items': len(IM.get('items', [])), 'n_crop_points': len(CP.get('points') or []),
       'n_active': len(active), 'n_alarm': sum(1 for e in active if e['level'] == 2), 'events': events, 'oni': ONI, 'sst': SST, 'exposure': exposure, 'origin_level': origin_level, 'msgs': MSG[:40],
       'news_src': '구글 뉴스로 대신' if gd_off else 'GDELT', 'elapsed_sec': round(time.time() - T0),
       'basis': '세계 뉴스 흐름(GDELT, 막히면 구글 뉴스) · 엘니뇨 지수(미 해양대기청) · 위성 수온 이상(산호초감시, 안 되면 오픈메테오 3년 대비) · 세계 상품값·환율(국제통화기금·미 연준) · 지진(미 지질조사국) · 태풍(합동태풍경보센터) · 주산지 7일 날씨(오픈메테오) · 해외 선물판 · 달력 · 확인 메모'}
jsave(os.path.join(DATA, 'world.json'), out)
jsave(os.path.join(OUT_LOG, TS + '.json'), {'at': out['at'], 'active': [{k: e.get(k) for k in ('id', 'level', 'value', 'text')} for e in active], 'oni': ONI})
os.makedirs(os.path.join(HERE, '_debug'), exist_ok=True)
jsave(os.path.join(HERE, '_debug', 'world_debug.json'), {'at': out['at'], 'elapsed': out['elapsed_sec'], 'news_src': out['news_src'], 'msgs': MSG, 'events': [{k: e.get(k) for k in ('id', 'level', 'value', 'text', 'news', 'parts', 'fx')} for e in events]})
fail = sum(1 for e in events if '못 받음' in (e.get('text') or '') or '실패' in (e.get('text') or ''))
status('world', fail < max(5, len(events) // 3), f'요인 {len(events)}(주제 {out["n_topic"]}·원산지 {len(origin_events)}/{len(countries)}·날씨 {len(CW)}) · 활성 {len(active)}(경보 {out["n_alarm"]}) · 못 받음 {fail} · {out["elapsed_sec"]}초')
print('세계 요인', len(events), '활성', [(e['id'], e['level']) for e in active][:20], 'msgs', MSG[:6], out['elapsed_sec'], '초')
