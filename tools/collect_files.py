# 파일데이터(열쇠 불필요) 일괄 내려받기 — tools/file_sets.json 의 공공데이터포털 파일데이터를 바뀐 것만 받아
#  private/files/<번호>.<확장자>(8㎆ 이하일 때 원본), private/files/<번호>.json(칸 이름·줄 수·앞 200줄) 로 저장.
#  공개 화면용 가공은 build_files.py 가 이 요약을 읽어 만든다(개별 업소 명단은 공개하지 않음).
import sys, os, re, io, csv, json, time, zipfile, urllib.request, urllib.parse, http.cookiejar
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
SETS = jload(os.path.join(ROOT, 'tools', 'file_sets.json'), [])
PD = os.path.join(PRIVATE, 'files'); os.makedirs(PD, exist_ok=True)
STATE = os.path.join(PD, 'state.json'); st = jload(STATE, {})
OP = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36', 'Accept-Language': 'ko-KR,ko;q=0.9'}
def fetch(url, ref='https://www.data.go.kr/'):
    with OP.open(urllib.request.Request(url, headers=dict(UA, Referer=ref)), timeout=300) as r: return r.read(), dict(r.headers)
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
for s in SETS:
    i = s['id']
    try:
        page = f'https://www.data.go.kr/data/{i}/fileData.do'
        h = fetch(page)[0].decode('utf-8', 'replace')
        m = re.search(r'/cmm/cmm/fileDownload\.do\?atchFileId=(\w+)&(?:amp;)?fileDetailSn=(\d+)', h)
        t = re.search(r'<title>([^<|]*)', h); title = t.group(1).strip() if t else s.get('title', '')
        upd = re.search(r'수정일</th>\s*<td[^>]*>\s*([\d-]+)', h)
        if not m: raise RuntimeError('내려받기 주소 없음')
        fid = m.group(1) + '_' + m.group(2)
        if st.get(i, {}).get('fid') == fid and os.path.exists(os.path.join(PD, i + '.json')) and not env('FILES_FORCE'):
            same += 1; continue
        b, hd = fetch(f'https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId={m.group(1)}&fileDetailSn={m.group(2)}&insertDataPrcus=N', page)
        disp = urllib.parse.unquote(re.sub(r'.*filename="?([^";]+)"?.*', r'\1', hd.get('Content-Disposition', '') or 'x.csv'))
        ext = disp.rsplit('.', 1)[-1].lower() if '.' in disp else 'bin'
        if ext == 'zip':
            z = zipfile.ZipFile(io.BytesIO(b)); nm = max(z.namelist(), key=lambda n: z.getinfo(n).file_size); b = z.read(nm); disp = nm; ext = nm.rsplit('.', 1)[-1].lower()
        rows = table(b, disp)
        if len(b) <= 8 * 1024 * 1024:
            for f in os.listdir(PD):
                if f.startswith(i + '.') and not f.endswith('.json'): os.remove(os.path.join(PD, f))
            open(os.path.join(PD, f'{i}.{ext}'), 'wb').write(b)
        jsave(os.path.join(PD, i + '.json'), {'id': i, 'key': s.get('key'), 'title': title, 'file': disp, 'size': len(b), 'updated': upd.group(1) if upd else '', 'at': stamp(),
                                              'cols': rows[0] if rows else [], 'n': max(0, len(rows) - 1), 'head': rows[1:201]})
        st[i] = {'fid': fid, 'at': stamp(), 'file': disp, 'n': max(0, len(rows) - 1)}; ok += 1
        print('받음', i, title[:30], disp, len(b), len(rows))
    except Exception as e:
        st.setdefault(i, {})['err'] = str(e)[:160]; fail += 1; print('실패', i, e)
    time.sleep(1)
jsave(STATE, st, indent=1)
status('files', fail == 0, f'파일데이터 {len(SETS)}종 · 새로 받음 {ok} · 그대로 {same} · 실패 {fail}')
