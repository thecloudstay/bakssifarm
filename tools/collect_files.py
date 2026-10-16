# 파일데이터(열쇠 불필요) 일괄 내려받기 — tools/file_sets.json 의 공공데이터포털 파일데이터를 바뀐 것만 받아
#  private/files/<번호>.<확장자>(8㎆ 이하일 때 원본), private/files/<번호>.json(칸 이름·줄 수·앞 200줄) 로 저장.
#  공개 화면용 가공은 build_files.py 가 이 요약을 읽어 만든다(개별 업소 명단은 공개하지 않음).
import sys, os, re, io, csv, json, time, zipfile, collections, urllib.request, urllib.parse, http.cookiejar
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
SETS = jload(os.path.join(ROOT, 'tools', 'file_sets.json'), [])
PD = os.path.join(PRIVATE, 'files'); os.makedirs(PD, exist_ok=True)
RAW = os.path.join(ROOT, '.cache', 'files'); os.makedirs(RAW, exist_ok=True)   # 원본 전체(저장소에 안 올림) — 같은 작업 안에서 build_files.py 가 가공
STATE = os.path.join(PD, 'state.json'); st = jload(STATE, {})
OP = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36', 'Accept-Language': 'ko-KR,ko;q=0.9'}
def fetch(url, ref='https://www.data.go.kr/', data=None):
    hd = dict(UA, Referer=ref)
    if data is not None: hd.update({'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'})
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data is not None else None, headers=hd)
    with OP.open(req, timeout=120) as r: return r.read(), dict(r.headers)
def decode(b):
    for enc in ('utf-8-sig', 'cp949'):
        try: return b.decode(enc)
        except UnicodeDecodeError: pass
    return b.decode('cp949', 'replace')
def table(b, name):
    ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
    if ext in ('xlsx', 'xls') or b[:2] == b'PK':
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(b), read_only=True, data_only=True); ws = wb.worksheets[0]
            rows = [[('' if c is None else str(c)).strip() for c in r] for r in ws.iter_rows(values_only=True)]
            rows = [r for r in rows if any(r)]
            return rows
        except Exception as e:
            return [['열기 실패', str(e)[:80]]]
    if ext == 'json':
        j = json.loads(decode(b)); arr = j if isinstance(j, list) else next((v for v in j.values() if isinstance(v, list)), [])
        if arr and isinstance(arr[0], dict):
            cols = list(arr[0].keys()); return [cols] + [[str(x.get(c, '')) for c in cols] for x in arr]
        return []
    return [r for r in csv.reader(io.StringIO(decode(b)))]
ok = fail = same = 0
T0 = time.time()
for s in SETS:
    i = s['id']
    if time.time() - T0 > 600: print('10분 넘어 나머지는 다음에'); break
    try:
        page = f'https://www.data.go.kr/data/{i}/fileData.do'
        h = fetch(page)[0].decode('utf-8', 'replace')
        m = find_file(h, page, fetch)
        t = re.search(r'<title>([^<|]*)', h); title = t.group(1).strip() if t else s.get('title', '')
        upd = re.search(r'수정일</th>\s*<td[^>]*>\s*([\d-]+)', h)
        if not m:
            if '기관자체에서 다운로드' in h: st[i] = {'link': True, 'at': stamp(), 'title': title}; print('제공처 링크(로그인 필요)', i); continue
            raise RuntimeError('내려받기 주소 없음')
        fid = m[0] + '_' + m[1]
        if st.get(i, {}).get('fid') == fid and os.path.exists(os.path.join(PD, i + '.json')) and not env('FILES_FORCE'):
            same += 1; continue
        b, hd = fetch(f'https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId={m[0]}&fileDetailSn={m[1]}&insertDataPrcus=N', page)
        disp = urllib.parse.unquote(re.sub(r'.*filename="?([^";]+)"?.*', r'\1', hd.get('Content-Disposition', '') or 'x.csv'))
        ext = disp.rsplit('.', 1)[-1].lower() if '.' in disp else 'bin'
        if ext == 'zip':
            z = zipfile.ZipFile(io.BytesIO(b)); nm = max(z.namelist(), key=lambda n: z.getinfo(n).file_size); b = z.read(nm); disp = nm; ext = nm.rsplit('.', 1)[-1].lower()
        rows = table(b, disp)
        for f in os.listdir(PD):
            if f.startswith(i + '.') and not f.endswith('.json'): os.remove(os.path.join(PD, f))
        open(os.path.join(RAW, f'{i}.{ext}'), 'wb').write(b)
        if len(b) <= 1024 * 1024: open(os.path.join(PD, f'{i}.{ext}'), 'wb').write(b)
        jsave(os.path.join(PD, i + '.json'), {'id': i, 'key': s.get('key'), 'title': title, 'file': disp, 'size': len(b), 'updated': upd.group(1) if upd else '', 'at': stamp(),
                                              'cols': rows[0] if rows else [], 'n': max(0, len(rows) - 1), 'head': rows[1:201]})
        st[i] = {'fid': fid, 'at': stamp(), 'file': disp, 'n': max(0, len(rows) - 1)}; ok += 1
        print('받음', i, title[:30], disp, len(b), len(rows))
    except Exception as e:
        st.setdefault(i, {})['err'] = str(e)[:160]; fail += 1; print('실패', i, e)
    time.sleep(1)
jsave(STATE, st, indent=1)
# 연동 대장에 파일데이터도 올림
reg = jload(os.path.join(DATA, 'apis.json'), {'items': {}})
DOM = {'feed': '동물농장', 'import_cattle': '동물농장', 'cattle': '동물농장', 'pig': '동물농장', 'ls': '동물농장', 'grade': '동물농장', 'dairy': '동물농장', 'abattoirs': '동물농장', 'dealers': '동물농장', 'insect': '동물농장',
       'wipan': '어장', 'sea': '어장', 'busan': '어장', 'import_meat': '동물농장', 'at_trade': '공통'}
for s in SETS:
    v = st.get(s['id'], {}); k = s.get('key', '')
    dom = next((d for p, d in DOM.items() if k.startswith(p)), '공통')
    cat = '시세·거래' if any(w in s['title'] for w in ('가격', '경락', '위판', '판매')) else '수출입' if '수입' in s['title'] or '수출' in s['title'] else '업체·인허가' if any(w in s['title'] for w in ('현황', '등록')) else '사육·생산'
    reg['items']['file-' + s['id']] = {'title': '파일데이터_' + s['title'], 'dom': dom, 'cat': cat, 'host': 'www.data.go.kr', 'at': v.get('at', ''),
        'state': '정상' if v.get('fid') else '제공처 열쇠' if v.get('link') else '실패', 'n': v.get('n'), 'msg': '열쇠 없이 내려받음' if v.get('fid') else '제공처 링크(포털 로그인 필요)' if v.get('link') else v.get('err', '')}
reg['summary'] = dict(collections.Counter(x.get('state', '?') for x in reg['items'].values()))
jsave(os.path.join(DATA, 'apis.json'), reg, indent=1)
nl = sum(1 for v in st.values() if isinstance(v, dict) and v.get('link'))
status('files', fail == 0, f'파일데이터 {len(SETS)}종 · 새로 받음 {ok} · 그대로 {same} · 제공처 링크 {nl} · 실패 {fail}')
