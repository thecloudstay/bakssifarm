# 거시 시장 지표 모으기(열쇠 불필요) — 해외 선물·환율·운임 대용 지표의 날마다 종가
#  시카고 옥수수·대두박·대두·소맥(배합사료 원가), 생우·비육우·돈육 선물(세계 축산 경기), 서부텍사스유(운송·난방 원가),
#  원/달러 환율(수입 원료 원화 값), 건화물선 운임 대용 상장지수펀드(곡물 해상운임).
#  1차: 야후 금융 차트(하루 한 번 종가) → 실패하면 스투크 일별 파일 → 환율은 미국 연준 경제자료(FRED)까지.
#  결과: site/data/macro.json = {at, series: {키: {name, unit, src, d: [[날짜, 종가], ...]}}}  (최근 3년)
import sys, os, json, csv, io, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

SERIES = [
    # 키, 이름, 단위, 야후 기호, 스투크 기호
    ('corn',    '옥수수 선물(시카고)',       '센트/부셸',   'ZC=F',  'zc.f'),
    ('soymeal', '대두박 선물(시카고)',       '달러/숏톤',   'ZM=F',  'zm.f'),
    ('soy',     '대두 선물(시카고)',         '센트/부셸',   'ZS=F',  'zs.f'),
    ('wheat',   '소맥 선물(시카고)',         '센트/부셸',   'ZW=F',  'zw.f'),
    ('cattle',  '생우 선물(시카고)',         '센트/파운드', 'LE=F',  'le.f'),
    ('feeder',  '비육우 선물(시카고)',       '센트/파운드', 'GF=F',  'gf.f'),
    ('hog',     '돈육 선물(시카고)',         '센트/파운드', 'HE=F',  'he.f'),
    ('oil',     '서부텍사스유 선물',         '달러/배럴',   'CL=F',  'cl.f'),
    ('diesel',  '경유·난방유 선물(뉴욕)',    '달러/갤런',   'HO=F',  'ho.f'),
    ('brent',   '브렌트유 선물',             '달러/배럴',   'BZ=F',  'cb.f'),
    ('natgas',  '천연가스 선물(미국)',       '달러/백만열량단위', 'NG=F', 'ng.f'),
    ('usdkrw',  '원/달러 환율',              '원',          'KRW=X', 'usdkrw'),
    ('freight', '건화물선 운임 대용 지표',   '달러',        'BDRY',  'bdry.us'),
]
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) bakssifarm-macro/1.0'}
P = os.path.join(DATA, 'macro.json')
old = jload(P, {'series': {}})
START = (now().date() - datetime.timedelta(days=365 * 3 + 30))

def yahoo(sym):
    j = json.loads(get(f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}', {'range': '5y', 'interval': '1d'}, headers=UA, retry=2))
    r = j['chart']['result'][0]; ts = r.get('timestamp') or []; cl = r['indicators']['quote'][0].get('close') or []
    out = []
    for t, c in zip(ts, cl):
        if c is None: continue
        out.append([datetime.datetime.fromtimestamp(t, KST).date().isoformat(), round(float(c), 4)])
    return out

def stooq(sym):
    b = get(f'https://stooq.com/q/d/l/', {'s': sym, 'i': 'd'}, headers=UA, retry=2).decode('utf-8', 'replace')
    out = []
    for row in csv.DictReader(io.StringIO(b)):
        try: out.append([row['Date'], round(float(row['Close']), 4)])
        except Exception: pass
    return out

def fred_krw():
    b = get('https://fred.stlouisfed.org/graph/fredgraph.csv', {'id': 'DEXKOUS'}, headers=UA, retry=2).decode('utf-8', 'replace')
    out = []
    for row in csv.reader(io.StringIO(b)):
        if len(row) < 2 or not row[0][:2].isdigit(): continue
        try: out.append([row[0], round(float(row[1]), 2)])
        except Exception: pass
    return out

ok = 0; msgs = []; series = {}
for key, name, unit, ysym, ssym in SERIES:
    d = None; src = ''
    srcs = [(yahoo, ysym, '야후 금융'), (stooq, ssym, '스투크')]
    if key == 'usdkrw': srcs.append((lambda _: fred_krw(), None, '미국 연준 경제자료'))
    for fn, arg, label in srcs:
        try:
            d = fn(arg)
            if d and len(d) >= 30: src = label; break
        except Exception as e:
            msgs.append(f'{key}:{label} {str(e)[:40]}')
        d = None
    prev = (old.get('series') or {}).get(key, {}).get('d', [])
    if d:
        # 지난 기록과 합치기(같은 날짜는 새 값) — 제공처가 짧게 주는 날에도 이력이 끊기지 않게
        m = {a: b for a, b in prev}; m.update({a: b for a, b in d})
        merged = sorted([[a, b] for a, b in m.items() if a >= START.isoformat()])
        series[key] = {'name': name, 'unit': unit, 'src': src, 'd': merged}; ok += 1
    elif prev:
        series[key] = dict(old['series'][key]); series[key]['stale'] = True
jsave(P, {'at': stamp(), 'series': series})
last = {k: v['d'][-1] for k, v in series.items() if v.get('d')}
status('macro', ok >= 8, f'{ok}/{len(SERIES)}종 · ' + ' · '.join(f'{k} {v[0][5:]} {v[1]}' for k, v in list(last.items())[:4]) + (' · ' + '; '.join(msgs[:3]) if ok < len(SERIES) else ''))
print('거시 지표', ok, '/', len(SERIES), msgs[:5])
