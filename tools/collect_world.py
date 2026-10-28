# 세계 요인 감시(2026-10-28) — 기후·질병·지정학·정책·세계 상품·달력 요인을 열쇠 없는 공개 자료로 매일 재서
#   site/data/world.json (활성 요인·단계·근거·영향 품목) 과 private/world/날짜.json (기록) 으로 남긴다.
#   구매 신호(수산·농산)·축산 판단은 world_lib.world_adjust() 로 이 결과를 점수에 더한다(갈래별 상한 있음).
# 자료(모두 열쇠 없음, 깃허브 우분투에서 접속):
#   gdelt  세계 뉴스 흐름(GDELT 2.0 문서 검색) — 최근 7일 기사 비중을 앞 11주와 비교(표준점수·배수)
#   oni    엘니뇨 지수(미 해양대기청 기후예측센터 ONI)
#   sst    한반도 주변 7개 점 위성 수온 이상(미 해양대기청 산호초감시 5㎞, ERDDAP)
#   fred   국제통화기금 상품값 월간(미 연준 경제자료 경유: 어분·닭고기·쇠고기·새우·요소)
#   usgs   일본·한반도 근해 지진(미 지질조사국)
#   jtwc   서태평양 태풍 경보(미 합동태풍경보센터 RSS)
#   tiles  우리 해외 선물판(site/data/forecast.json)
#   cal    달력(설·추석·김장·휴가·개학)
#   manual tools/world_notes.json — 사람이 확인해 적은 메모(until 지나면 빠짐)
# 뉴스 흐름은 「그 이야기가 평소보다 많이 나온다」는 뜻이지 사실 확인이 아니다. 화면에도 그렇게 적는다.
import sys, os, re, io, csv, json, math, time, datetime, statistics, collections, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
HERE = os.path.dirname(os.path.abspath(__file__))
R = jload(os.path.join(HERE, 'world_rules.json'), {'rules': []})
NOTES = jload(os.path.join(HERE, 'world_notes.json'), {}).get('notes', [])
FC = jload(os.path.join(DATA, 'forecast.json'), {})
TODAY = now().date(); TS = TODAY.isoformat()
UA = {'User-Agent': 'Mozilla/5.0 (compatible; bakssifarm-world/1.0; +https://thecloudstay.github.io/bakssifarm/)'}
DBG = {}; MSG = []
T0 = time.time(); BUDGET = int(os.environ.get('WORLD_BUDGET_SEC') or 900)   # 전체 15분 안에 끝냄 — 넘으면 남은 뉴스 흐름 질의는 건너뜀
def over(): return time.time() - T0 > BUDGET
OUT_LOG = os.path.join(PRIVATE, 'world'); os.makedirs(OUT_LOG, exist_ok=True)
OLD = jload(os.path.join(DATA, 'world.json'), {})

def fetch(url, params=None, timeout=30, retry=2):
    return get(url, params, timeout=timeout, retry=retry, headers=UA)

# ── 자료별 측정 ──────────────────────────────────────────────
_gd_cache = {}
def gdelt(q):
    """최근 12주 일별 기사 비중 → 최근 7일 평균 대 앞 기간 평균. (z, ratio, last7, titles)"""
    if q in _gd_cache: return _gd_cache[q]
    res = {'z': None, 'ratio': None, 'last7': None, 'titles': [], 'err': ''}
    if over(): res['err'] = '시간 예산 초과로 건너뜀'; _gd_cache[q] = res; return res
    try:
        b = fetch('https://api.gdeltproject.org/api/v2/doc/doc', {'query': q, 'mode': 'timelinevol', 'timespan': '12w', 'format': 'json'}, timeout=25, retry=1)
        j = json.loads(b.decode('utf-8', 'replace'))
        data = ((j.get('timeline') or [{}])[0].get('data') or [])
        vals = [float(x.get('value') or 0) for x in data]
        if len(vals) >= 21:
            last7 = vals[-7:]; base = vals[:-7]
            m7 = statistics.mean(last7); mb = statistics.mean(base); sd = statistics.pstdev(base) or (mb * 0.5) or 1e-9
            res.update({'z': round((m7 - mb) / sd, 2), 'ratio': round(m7 / mb, 2) if mb > 0 else (9.9 if m7 > 0 else 1.0), 'last7': round(m7, 4), 'base': round(mb, 4)})
        else: res['err'] = f'자료 {len(vals)}일뿐'
    except Exception as e:
        res['err'] = str(e)[:80]
    time.sleep(1.2)
    _gd_cache[q] = res; return res
def gdelt_titles(q, n=3):
    if over(): return []
    try:
        b = fetch('https://api.gdeltproject.org/api/v2/doc/doc', {'query': q, 'mode': 'artlist', 'maxrecords': 8, 'sort': 'datedesc', 'format': 'json'}, timeout=25, retry=1)
        arts = json.loads(b.decode('utf-8', 'replace')).get('articles') or []
        seen, out = set(), []
        for a in arts:
            t = re.sub(r'\s+', ' ', a.get('title') or '').strip()
            if not t or t[:30] in seen: continue
            seen.add(t[:30]); out.append({'t': t[:90], 'u': a.get('url', ''), 'd': (a.get('seendate') or '')[:8], 's': a.get('domain', '')})
            if len(out) >= n: break
        time.sleep(1.0); return out
    except Exception: return []

def oni():
    """ONI 표(계절 3개월 평균) 마지막 값과 흐름"""
    try:
        t = fetch('https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt', timeout=30).decode('ascii', 'replace')
        rows = [l.split() for l in t.strip().splitlines()[1:] if len(l.split()) >= 4]
        vals = [(r[0], int(r[1]), float(r[3])) for r in rows]
        if not vals: return None
        last = vals[-1]; prev = vals[-2] if len(vals) > 1 else last
        return {'season': last[0], 'year': last[1], 'anom': last[2], 'prev': prev[2], 'phase': '엘니뇨' if last[2] >= 0.5 else '라니냐' if last[2] <= -0.5 else '중립',
                'strong': abs(last[2]) >= 1.0, 'hist': [v[2] for v in vals[-8:]]}
    except Exception as e:
        MSG.append('oni ' + str(e)[:60]); return None

SST_PTS = [('서해 중부', 36.6, 125.6), ('서해 남부', 34.8, 125.6), ('남해 서부', 34.3, 127.3), ('남해 동부', 34.6, 128.3), ('동해 남부', 36.0, 129.9), ('동해 중부', 37.8, 129.3), ('제주 남쪽', 33.0, 126.5)]
def sst_anom():
    out = []
    for nm, la, lo in SST_PTS:
        try:
            u = f'https://coastwatch.pfeg.noaa.gov/erddap/griddap/NOAA_DHW.csv?CRW_SSTANOMALY%5B(last)%5D%5B({la}):({la})%5D%5B({lo}):({lo})%5D'
            t = fetch(u, timeout=40, retry=1).decode('utf-8', 'replace')
            rows = [r for r in csv.reader(io.StringIO(t)) if r and r[0][:2] == '20']
            if rows:
                v = rows[-1][-1]
                if v not in ('', 'NaN'): out.append({'name': nm, 'anom': round(float(v), 2), 'date': rows[-1][0][:10]})
        except Exception as e:
            MSG.append(f'sst {nm} {str(e)[:40]}')
    return out

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
        return {'id': series_id, 'date': out[-1][0][:7], 'last': last, 'c1': round((last / m1 - 1) * 100, 1) if m1 else None, 'c3': round((last / m3 - 1) * 100, 1) if m3 else None, 'c12': round((last / y1 - 1) * 100, 1) if y1 else None}
    except Exception as e:
        MSG.append(f'fred {series_id} {str(e)[:40]}'); return None

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
        wp = [re.sub(r'\s+', ' ', x).strip() for x in titles if re.search(r'\b\d{2}W\b', x) or 'Western' in x or 'West Pacific' in x]
        return wp
    except Exception as e:
        MSG.append('jtwc ' + str(e)[:50]); return None

def tile(key):
    return next((t for t in (FC.get('tiles') or []) if t.get('key') == key), None)

def cal_state(kind):
    """달력 요인: (단계, 설명, 'before'|'after'|None)"""
    H = R.get('holidays') or {}
    if kind == 'holiday':
        best = None
        for nm, ds in H.items():
            for d in ds:
                dd = datetime.date.fromisoformat(d); k = (dd - TODAY).days
                if -21 <= k <= 45 and (best is None or abs(k) < abs(best[1])): best = (nm, k, d)
        if not best: return 0, '', None
        nm, k, d = best
        if k >= 0: return (2 if k <= 14 else 1), f'{nm}({d}) {k}일 전 — 명절 수요 구간', 'before'
        return 1, f'{nm}({d}) {-k}일 지남 — 명절 뒤 되돌림 구간', 'after'
    m, d = TODAY.month, TODAY.day
    if kind == 'kimjang':
        if (m == 10 and d >= 25) or (m == 11): return (2 if m == 11 and d <= 20 else 1), '김장철 수요 구간', 'before'
        if m == 12 and d <= 20: return 1, '김장 뒤 되돌림 구간', 'after'
        return 0, '', None
    if kind == 'summer':
        if (m == 7 and d >= 10) or (m == 8 and d <= 20): return 1, '여름 휴가철 횟감 수요', 'before'
        return 0, '', None
    if kind == 'school':
        if (m in (2, 8) and d >= 18) or (m in (3, 9) and d <= 10): return 1, '개학 급식 수요', 'before'
        return 0, '', None
    return 0, '', None

def lv_from_z(z, ratio):
    if z is None or ratio is None: return 0
    if z >= 3 and ratio >= 2.0: return 2
    if z >= 1.5 and ratio >= 1.4: return 1
    return 0
def lv_from_pct(v, warn, alarm):
    if v is None: return 0
    return 2 if abs(v) >= alarm else 1 if abs(v) >= warn else 0

# ── 규칙마다 재기 ─────────────────────────────────────────────
events = []
ONI = None; SST = None; JT = None
for r in R.get('rules', []):
    dt = r.get('detect') or {}; typ = dt.get('type', '')
    ev = {'id': r['id'], 'cat': r['cat'], 'name': r['name'], 'level': 0, 'value': '', 'text': '', 'why': r.get('why', ''), 'react': r.get('react', ''), 'lag': r.get('lag', ''), 'src': r.get('src', ''), 'affects': [], 'kind': typ, 'titles': []}
    try:
        aff = r.get('affects') or []
        if typ == 'oni':
            ONI = ONI or oni()
            if ONI:
                lv = 2 if ONI['strong'] else 1 if ONI['phase'] != '중립' else 0
                ev.update({'level': lv, 'value': f'{ONI["anom"]:+.1f}', 'text': f'{ONI["season"]} {ONI["year"]} 지수 {ONI["anom"]:+.1f} — {ONI["phase"]}' + (' 강함' if ONI['strong'] else '') + f' (앞 계절 {ONI["prev"]:+.1f})', 'hist': ONI['hist']})
                aff = r.get('affects_elnino' if ONI['phase'] == '엘니뇨' else 'affects_lanina' if ONI['phase'] == '라니냐' else 'affects') or []
            else: ev['text'] = '자료 못 받음'
        elif typ == 'sst':
            SST = SST if SST is not None else sst_anom()
            if SST:
                mean = statistics.mean(x['anom'] for x in SST); hi = max(SST, key=lambda x: x['anom']); lo = min(SST, key=lambda x: x['anom'])
                lv = 2 if mean >= 1.5 or hi['anom'] >= 2.5 else 1 if mean >= 1.0 or hi['anom'] >= 1.8 or mean <= -1.0 else 0
                ev.update({'level': lv, 'value': f'{mean:+.1f}℃', 'text': f'7개 해역 평균 평년 대비 {mean:+.1f}℃ · 가장 높은 곳 {hi["name"]} {hi["anom"]:+.1f}℃ · 가장 낮은 곳 {lo["name"]} {lo["anom"]:+.1f}℃ ({SST[0]["date"]})', 'points': SST})
                aff = r.get('affects_hi') if mean >= 0 else r.get('affects_lo')
            else: ev['text'] = '자료 못 받음'
        elif typ == 'usgs':
            q = usgs(dt.get('box', [24, 46, 122, 146]), dt.get('warn', 6.0))
            if q is None: ev['text'] = '자료 못 받음'
            elif q:
                top = q[0]; ev.update({'level': 2 if top['mag'] >= dt.get('alarm', 7.0) else 1, 'value': f'규모 {top["mag"]}', 'text': f'최근 7일 규모 {dt.get("warn", 6.0)} 이상 {len(q)}건 — 가장 큰 것 규모 {top["mag"]} {top["place"]} ({top["time"]})'})
            else: ev['text'] = f'최근 7일 규모 {dt.get("warn", 6.0)} 이상 없음'
        elif typ in ('fred', 'fred+gdelt'):
            got = None
            for sid in dt.get('series', []):
                got = fred(sid)
                if got: break
            if got:
                v = got['c3'] if got['c3'] is not None else got['c1']
                ev.update({'level': lv_from_pct(v, dt.get('warn', 10), dt.get('alarm', 20)), 'value': f'{v:+.1f}%(3개월)', 'text': f'{got["date"]} 기준 {got["last"]:,.1f} · 1개월 {got["c1"]:+.1f}% · 3개월 {(got["c3"] if got["c3"] is not None else 0):+.1f}% · 1년 {(got["c12"] if got["c12"] is not None else 0):+.1f}%'})
                if v is not None and v < 0: aff = []   # 원가 요인은 오를 때만 반영(내릴 때는 메모만)
            else: ev['text'] = '자료 못 받음'
            if typ == 'fred+gdelt' and dt.get('q'):
                g = gdelt(dt['q']); ev['news'] = g
                if g.get('z') is not None and lv_from_z(g['z'], g['ratio']) > ev['level']: ev['level'] = lv_from_z(g['z'], g['ratio']); ev['text'] += f' · 뉴스 흐름 평소의 {g["ratio"]}배'
        elif typ == 'fred_multi':
            parts = []; worst = 0; direction = 0
            for k, sid in (dt.get('series') or {}).items():
                got = fred(sid)
                if not got: continue
                v = got['c3'] if got['c3'] is not None else got['c1']
                nm = {'poultry': '닭고기', 'beef': '쇠고기', 'shrimp': '새우'}.get(k, k)
                parts.append(f'{nm} {v:+.1f}%'); l = lv_from_pct(v, dt.get('warn', 8), dt.get('alarm', 15))
                if l > worst or (l == worst and abs(v) > abs(direction)): worst, direction = l, v
            ev.update({'level': worst, 'value': ' · '.join(parts), 'text': '세계 값 3개월 변동 — ' + (' · '.join(parts) or '자료 못 받음')})
            aff = (r.get('affects_up') if direction > 0 else r.get('affects_down')) if worst else []
        elif typ == 'jtwc+gdelt':
            JT = JT if JT is not None else jtwc()
            g = gdelt(dt['q']); ev['news'] = g
            lv = max(1 if JT else 0, lv_from_z(g.get('z'), g.get('ratio')))
            if JT and lv_from_z(g.get('z'), g.get('ratio')) >= 1: lv = 2
            ev.update({'level': lv, 'value': f'서태평양 활동 {len(JT or [])}개', 'text': ('서태평양 태풍 경보 ' + ', '.join(JT[:3]) if JT else '서태평양 태풍 경보 없음' if JT is not None else '태풍 경보 자료 못 받음') + (f' · 한반도 태풍 뉴스 평소의 {g["ratio"]}배' if g.get('ratio') else '')})
        elif typ in ('tiles', 'tiles+gdelt'):
            vals = []
            for k in dt.get('keys', []):
                t = tile(k)
                if t and t.get('c20') is not None: vals.append((t['name'], t['c20'], t.get('c60')))
            lv = 0; txt = []
            for nm, c20, c60 in vals:
                l = lv_from_pct(c20 if c20 > 0 else 0, dt.get('warn', 8), dt.get('alarm', 15))
                lv = max(lv, l); txt.append(f'{nm} 1개월 {c20:+.1f}%' + (f'·3개월 {c60:+.1f}%' if c60 is not None else ''))
            if typ == 'tiles+gdelt' and dt.get('q'):
                g = gdelt(dt['q']); ev['news'] = g
                if g.get('ratio'): txt.append(f'뉴스 흐름 평소의 {g["ratio"]}배'); lv = max(lv, lv_from_z(g['z'], g['ratio']))
            ev.update({'level': lv, 'value': ' · '.join(f'{c20:+.1f}%' for _, c20, _ in vals), 'text': ' · '.join(txt) or '자료 없음'})
        elif typ == 'gdelt':
            g = gdelt(dt['q']); ev['news'] = g
            lv = lv_from_z(g.get('z'), g.get('ratio'))
            ev.update({'level': lv, 'value': f'뉴스 {g["ratio"]}배' if g.get('ratio') else '', 'text': (f'최근 7일 관련 기사 비중이 앞 11주 평균의 {g["ratio"]}배(표준점수 {g["z"]})' if g.get('ratio') is not None else '뉴스 흐름 자료 못 받음 ' + g.get('err', ''))})
        elif typ == 'cal':
            lv, txt, ph = cal_state(dt.get('kind', ''))
            ev.update({'level': lv, 'value': '', 'text': txt or '해당 구간 아님'})
            aff = (r.get('affects_before') if ph == 'before' else r.get('affects_after') if ph == 'after' else []) or []
        # 활성이면 기사 제목 몇 개
        if ev['level'] and dt.get('q') and typ in ('gdelt', 'tiles+gdelt', 'jtwc+gdelt', 'fred+gdelt'): ev['titles'] = gdelt_titles(dt['q'])
        if ev['level']: ev['affects'] = [dict(a, w=round(a['w'] * ev['level'], 2)) for a in (aff or [])]
        ev['affects_all'] = aff if aff else (r.get('affects') or r.get('affects_before') or r.get('affects_hi') or r.get('affects_up') or r.get('affects_elnino') or [])
    except Exception as e:
        ev['text'] = '측정 실패 ' + str(e)[:60]; MSG.append(f'{r["id"]} {str(e)[:50]}')
    events.append(ev)

# ── 사람이 확인한 메모(기한 안) ─────────────────────────────────
for n in NOTES:
    if n.get('until') and n['until'] < TS: continue
    events.append({'id': 'note-' + re.sub(r'\W+', '', n.get('item', ''))[:20], 'cat': n.get('cat', '확인 메모'), 'name': n.get('item', ''), 'level': int(n.get('level', 1)), 'value': '', 'text': n.get('text', ''),
                   'why': n.get('why', ''), 'react': n.get('react', ''), 'lag': n.get('lag', ''), 'src': n.get('src', ''), 'kind': 'manual', 'titles': [],
                   'affects': [dict(a, w=round(a['w'] * int(n.get('level', 1)), 2)) for a in n.get('affects', [])], 'affects_all': n.get('affects', []), 'until': n.get('until', ''), 'date': n.get('date', '')})

active = [e for e in events if e['level']]
active.sort(key=lambda e: (-e['level'], e['cat']))
out = {'at': stamp(), 'date': TS, 'caps': R.get('caps') or {}, 'n_rules': len(R.get('rules', [])), 'n_active': len(active), 'n_alarm': sum(1 for e in active if e['level'] == 2),
       'events': events, 'oni': ONI, 'sst': SST, 'msgs': MSG[:30],
       'basis': '세계 뉴스 흐름(GDELT) · 엘니뇨 지수(미 해양대기청) · 위성 수온 이상(미 해양대기청 산호초감시) · 세계 상품값(국제통화기금) · 지진(미 지질조사국) · 태풍(미 합동태풍경보센터) · 해외 선물판 · 달력 · 확인 메모'}
jsave(os.path.join(DATA, 'world.json'), out)
jsave(os.path.join(OUT_LOG, TS + '.json'), {'at': out['at'], 'active': [{k: e.get(k) for k in ('id', 'level', 'value', 'text')} for e in active]})
os.makedirs(os.path.join(HERE, '_debug'), exist_ok=True)
jsave(os.path.join(HERE, '_debug', 'world_debug.json'), {'at': out['at'], 'msgs': MSG, 'events': [{k: e.get(k) for k in ('id', 'level', 'value', 'text', 'news')} for e in events]})
fail = sum(1 for e in events if '못 받음' in e.get('text', '') or '실패' in e.get('text', ''))
status('world', fail < max(3, len(events) // 2), f'요인 {len(events)} · 활성 {len(active)}(경보 {out["n_alarm"]}) · 자료 못 받음 {fail}')
print('세계 요인', len(events), '활성', [(e['id'], e['level']) for e in active], 'msgs', MSG[:5])
