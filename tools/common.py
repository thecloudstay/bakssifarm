# 수집기 공통: 경로, 상태 기록, 요청
import json, os, re, datetime, urllib.request, urllib.parse, ssl, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'site')
DATA = os.path.join(SITE, 'data')
PRIVATE = os.path.join(ROOT, 'private')   # 리 단위 집계 등 공개하지 않는 가공 자료(배포 폴더 밖)
KST = datetime.timezone(datetime.timedelta(hours=9))
def now(): return datetime.datetime.now(KST)
def stamp(): return now().strftime('%Y-%m-%d %H:%M')
def jload(p, default=None):
    if not os.path.exists(p): return default
    with open(p, encoding='utf-8') as f: return json.load(f)
def jsave(p, obj, indent=None):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f: json.dump(obj, f, ensure_ascii=False, indent=indent, separators=None if indent else (',', ':'))
def status(key, ok, msg=''):
    p = os.path.join(DATA, 'status.json'); st = jload(p, {})
    st.setdefault('collectors', {})[key] = {'ok': ok, 'at': stamp(), 'msg': msg}
    jsave(p, st, indent=1)
def keyflag(name, present):
    p = os.path.join(DATA, 'status.json'); st = jload(p, {})
    st.setdefault('keys', {})[name] = bool(present); jsave(p, st, indent=1)
def get(url, params=None, timeout=40, retry=3, headers=None):
    if params: url += ('&' if '?' in url else '?') + urllib.parse.urlencode(params, safe='=%')
    last = None
    for i in range(retry):
        try:
            req = urllib.request.Request(url, headers=headers or {'User-Agent': 'bakssine-collector/1.0'})
            with urllib.request.urlopen(req, timeout=timeout) as r: return r.read()
        except Exception as e:
            last = e; time.sleep(2 + i * 3)
    raise last
def env(k, default=None): return os.environ.get(k) or default
def find_file(h, page, fetch):
    # 공공데이터포털 파일데이터 화면에서 내려받기 번호(atchFileId, fileDetailSn) 찾기. fetch(url, ref, data) → (내용, 머리글)
    #  1) 화면에 바로 받기 주소가 박혀 있는 옛 방식  2) 「fn_fileDataDown(번호, 상세번호, …)」 단추만 있는 새 방식 → 포털 화면 스크립트처럼 내려받기 번호를 물어봄
    m = re.search(r'/cmm/cmm/fileDownload\.do\?atchFileId=(\w+)&(?:amp;)?fileDetailSn=(\d+)', h)
    if m: return m.group(1), m.group(2)
    m = re.search(r"fn_fileDataDown\('(\d+)',\s*'([^']+)',\s*'([^']*)',\s*'([^']*)'", h)
    if not m: return None
    b = fetch('https://www.data.go.kr/tcs/dss/selectFileDataDownload.do', page, {'publicDataDetailPk': m.group(2), 'publicDataPk': m.group(1), 'atchFileId': m.group(3),
              'fileDetailSn': m.group(4), 'publicDataTyCode': 'PR0051', 'url': '/tcs/dss/selectFileDataDownload.do'})[0]
    j = json.loads(b.decode('utf-8', 'replace'))
    if not j.get('status') or not j.get('atchFileId'): raise RuntimeError('내려받기 번호 응답 이상: ' + (j.get('error') or str(j)[:80]))
    return str(j['atchFileId']), str(j.get('fileDetailSn') or 1)
