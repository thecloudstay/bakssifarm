# 파일데이터(열쇠 없이 내려받는 공공데이터) 모으기 — 진단 단계: 상세 화면과 내려받기 단서를 저장
import os, re, json, time, urllib.request, urllib.parse, http.cookiejar
ROOT = os.path.dirname(os.path.abspath(__file__))
OP = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36', 'Accept-Language': 'ko-KR,ko;q=0.9'}
def get(url, data=None, ref='https://www.data.go.kr/', raw=False):
    hd = dict(H, Referer=ref)
    if data is not None: hd.update({'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'})
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data else None, headers=hd)
    with OP.open(req, timeout=60) as r:
        b = r.read(); return (b, dict(r.headers)) if raw else b.decode('utf-8', 'replace')
os.makedirs(os.path.join(ROOT, '_debug'), exist_ok=True)
out = {}
for i in os.environ.get('FILE_IDS', '').split(','):
    if not i: continue
    u = f'https://www.data.go.kr/data/{i}/fileData.do'
    h = get(u); open(os.path.join(ROOT, '_debug', f'file_{i}.html'), 'w', encoding='utf-8').write(h)
    hints = sorted(set(re.findall(r'(fn_\w*[Dd]own\w*\([^)]{0,200}\)|/[\w/]*[Dd]ownload[\w/]*\.do[^"\' ]{0,200}|atchFileId[^,;]{0,80}|publicDataDetailPk[^,;]{0,80})', h)))[:60]
    rec = {'hints': hints[:8]}
    m = re.search(r'/cmm/cmm/fileDownload\.do\?atchFileId=(\w+)&(?:amp;)?fileDetailSn=(\d+)', h)
    t = re.search(r'<title>([^<|]*)', h); rec['title'] = t.group(1).strip() if t else ''
    if m:
        try:
            b, hd = get(f'https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId={m.group(1)}&fileDetailSn={m.group(2)}&insertDataPrcus=N', ref=u, raw=True)
            rec.update({'size': len(b), 'type': hd.get('Content-Type'), 'disp': hd.get('Content-Disposition'), 'head': b[:300].decode('cp949', 'replace')})
            os.makedirs(os.path.join(ROOT, '_debug', 'files'), exist_ok=True); open(os.path.join(ROOT, '_debug', 'files', i + '.bin'), 'wb').write(b[:200000])
        except Exception as e: rec['err'] = str(e)[:200]
    out[i] = rec; time.sleep(1)
json.dump(out, open(os.path.join(ROOT, '_debug', 'file_hints.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False)[:3000])
