"""원가·경기 지표 통로 점검(진단 작업용): 경제협력개발기구 직접 통계와 미 연준 경유 지표가 살아 있는지 tools/_debug/probe_cost.json 에 기록"""
import json, os, csv, io, datetime as dt, urllib.request, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__))
MSG = []
def get(url, params=None, timeout=40):
    if params: url += ('&' if '?' in url else '?') + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 bakssifarm-probe', 'Accept': 'text/csv,*/*'})
    with urllib.request.urlopen(req, timeout=timeout) as r: return r.read().decode('utf-8', 'replace')
def oecd_series(key, flow='OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0', n=18):
    try:
        b = get(f'https://sdmx.oecd.org/public/rest/data/{flow}/{key}', {'lastNObservations': n, 'format': 'csvfile'})
        rows = list(csv.reader(io.StringIO(b)))
        if not rows: return {'err': '빈 응답'}
        hd = rows[0]
        if 'TIME_PERIOD' not in hd or 'OBS_VALUE' not in hd: return {'err': '열 이름 ' + ','.join(hd)[:120], 'head': b[:300]}
        it, iv = hd.index('TIME_PERIOD'), hd.index('OBS_VALUE')
        return sorted((r[it], r[iv]) for r in rows[1:] if len(r) > max(it, iv))
    except Exception as e:
        return {'err': str(e)[:160]}
def fred(sid):
    try:
        b = get('https://fred.stlouisfed.org/graph/fredgraph.csv', {'id': sid})
        rows = [r for r in csv.reader(io.StringIO(b)) if len(r) > 1 and r[0][:2].isdigit()]
        return {'n': len(rows), 'last3': rows[-3:]}
    except Exception as e:
        return {'err': str(e)[:160]}
out = {'at': dt.datetime.now().strftime('%Y-%m-%d %H:%M'),
       'oecd_cpi': oecd_series('KOR.M.N.CPI.PA._T.N.GY'), 'oecd_cpi_food': oecd_series('KOR.M.N.CPI.PA.CP01.N.GY'),
       'oecd_cpi_labels': oecd_series('KOR.M.N.CPI.PA._T.N.GY', n=3) if False else None,
       'fred': {sid: fred(sid) for sid in ('KORCPALTT01GYM', 'CPALTT01KRM659N', 'CSCICP02KRM066S', 'IR3TIB01KRM156N')}}
os.makedirs(os.path.join(HERE, '_debug'), exist_ok=True)
json.dump(out, open(os.path.join(HERE, '_debug', 'probe_cost.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False)[:2000])
