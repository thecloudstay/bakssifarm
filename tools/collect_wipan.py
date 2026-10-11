# 수협 산지 위판 시세 — 해양수산부 「일자별 위탁판매 현황」 파일데이터(공공데이터포털 15102791, 열쇠 불필요, 달마다 갱신)
# 낙찰 한 줄마다 위판일자·산지조합·위판장·어종·상태(활어/선어/냉동)·업종(어업 종류·양식)·중량·금액이 있음.
# 공개: 조합별 상위 어종과 금액, 어종별 전국 ㎏당 단가(일별), 조합별 같은 어종 단가 비교 → site/data/wipan.json
# 원자료(수십 ㎆)는 저장소에 넣지 않고, 달별 집계만 private/wipan/YYYY-MM.json 으로 쌓음.
import sys, os, re, io, csv, json, collections, urllib.request, http.cookiejar
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
PK = '15102791'
OP = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36', 'Accept-Language': 'ko-KR,ko;q=0.9'}
def fetch(url, ref='https://www.data.go.kr/'):
    with OP.open(urllib.request.Request(url, headers=dict(UA, Referer=ref)), timeout=300) as r: return r.read()
PD = os.path.join(PRIVATE, 'wipan'); os.makedirs(PD, exist_ok=True)
STATE = os.path.join(PD, 'state.json'); st = jload(STATE, {})
WH = jload(os.path.join(DATA, 'places.json'), {'wharfs': []})['wharfs']
def norm(n): return re.sub(r'\s+', '', (n or '').replace('수산업협동조합', '수협').replace('(주)', ''))
COOP_U = {norm(w['name']): w['u'] for w in WH}
def coop_unit(name):
    n = norm(name)
    if n in COOP_U: return COOP_U[n]
    for k, u in COOP_U.items():
        if k and (k in n or n in k): return u
    return None
def num(x):
    try: return float(str(x).replace(',', '') or 0)
    except ValueError: return 0.0
try:
    page_url = f'https://www.data.go.kr/data/{PK}/fileData.do'
    h = fetch(page_url).decode('utf-8', 'replace') if not env('WIPAN_FILE') else '/cmm/cmm/fileDownload.do?atchFileId=TEST&fileDetailSn=1'
    m = re.search(r'/cmm/cmm/fileDownload\.do\?atchFileId=(\w+)&(?:amp;)?fileDetailSn=(\d+)', h)
    if not m: raise RuntimeError('내려받기 주소를 못 찾음')
    fid = m.group(1) + '_' + m.group(2)
    if st.get('fid') == fid and not env('WIPAN_FORCE'):
        status('wipan', True, f'새 파일 없음({st.get("month")})'); print('새 파일 없음'); sys.exit(0)
    raw = open(env('WIPAN_FILE'), 'rb').read() if env('WIPAN_FILE') else fetch(f'https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId={m.group(1)}&fileDetailSn={m.group(2)}&insertDataPrcus=N', page_url)
    for enc in ('utf-8-sig', 'cp949'):
        try: text = raw.decode(enc); break
        except UnicodeDecodeError: continue
    else: text = raw.decode('cp949', 'replace')
    rd = csv.DictReader(io.StringIO(text))
    coop = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0.0]))   # 조합 → 어종 → [금액, ㎏]
    fishday = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0.0])) # 어종 → 날짜 → [금액, ㎏]
    fish = collections.defaultdict(lambda: [0.0, 0.0, set()])                              # 어종 → [금액, ㎏, 조합들]
    kind = collections.Counter(); farm = collections.Counter(); days = set(); n = 0
    for r in rd:
        amt = num(r.get('위판금액')); kg = num(r.get('위판중량'))
        if amt <= 0: continue
        f = (r.get('수산물표준코드명') or '').strip(); s = (r.get('어종상태명') or '').strip()
        name = f + (f'({s})' if s else ''); c = (r.get('산지조합명') or '').strip(); d = r.get('위판일자') or ''
        a = coop[c][name]; a[0] += amt; a[1] += kg
        b = fishday[name][d]; b[0] += amt; b[1] += kg
        g = fish[name]; g[0] += amt; g[1] += kg; g[2].add(c)
        kind[(r.get('업종명') or '').strip()] += amt
        if '양식' in (r.get('업종명') or ''): farm[name] += amt
        days.add(d); n += 1
    month = max(days)[:7] if days else ''
    def wk(a): return round(a[0] / a[1]) if a[1] > 0 else None
    agg = {'month': month, 'rows': n, 'coops': {c: {k: [round(v[0]), round(v[1], 1)] for k, v in d.items()} for c, d in coop.items()},
           'fish': {k: [round(v[0]), round(v[1], 1)] for k, v in fish.items()}, 'kind': dict(kind), 'farm': dict(farm)}
    jsave(os.path.join(PD, month + '.json'), agg)
    # 공개 집계
    topfish = sorted(fish.items(), key=lambda x: -x[1][0])[:80]
    pub = {'at': stamp(), 'month': month, 'days': len(days), 'rows': n, 'source': '해양수산부 일자별 위탁판매 현황(수협 산지 위판, 공공데이터포털 파일데이터)',
           'total': round(sum(v[0] for v in fish.values())),
           'fish': [{'name': k, 'amt': round(v[0]), 'kg': round(v[1]), 'wonkg': wk(v), 'coops': len(v[2]),
                     'daily': [[d[5:], wk(x)] for d, x in sorted(fishday[k].items()) if wk(x)],
                     'by': sorted([[c, wk(coop[c][k]), round(coop[c][k][0])] for c in v[2] if wk(coop[c][k])], key=lambda x: -x[2])[:12]} for k, v in topfish],
           'coops': sorted([{'name': c, 'u': coop_unit(c), 'amt': round(sum(v[0] for v in d.values())),
                             'top': [[k, round(v[0]), wk(v)] for k, v in sorted(d.items(), key=lambda x: -x[1][0])[:8]]} for c, d in coop.items()], key=lambda x: -x['amt']),
           'kind': sorted([[k, round(v)] for k, v in kind.items()], key=lambda x: -x[1])[:15],
           'farm': sorted([[k, round(v)] for k, v in farm.items()], key=lambda x: -x[1])[:20]}
    # 시군별 합(조합 소재 시군 기준)
    byu = collections.defaultdict(lambda: {'amt': 0, 'coops': []})
    for c in pub['coops']:
        if c['u']: byu[c['u']]['amt'] += c['amt']; byu[c['u']]['coops'].append(c['name'])
    pub['units'] = byu
    # 앞달 대비(있으면)
    prev = sorted(f for f in os.listdir(PD) if re.match(r'\d{4}-\d\d\.json$', f) and f[:7] < month)
    if prev:
        pa = jload(os.path.join(PD, prev[-1]), {}).get('fish', {})
        for x in pub['fish']:
            p = pa.get(x['name'])
            if p and p[1] > 0 and x['wonkg']: x['prev'] = round(p[0] / p[1]); x['chg'] = round((x['wonkg'] / x['prev'] - 1) * 100, 1)
        pub['prev_month'] = prev[-1][:7]
    jsave(os.path.join(DATA, 'wipan.json'), pub)
    st.update({'fid': fid, 'month': month, 'at': stamp(), 'rows': n}); jsave(STATE, st, indent=1)
    status('wipan', True, f'{month} 위판 {n:,}줄 · 조합 {len(coop)} · 어종 {len(fish)}')
    print('위판', month, n, len(coop), len(fish))
except Exception as e:
    status('wipan', False, str(e)[:200]); print('실패', e)
