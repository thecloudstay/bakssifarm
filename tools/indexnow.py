# 색인 알림(인덱스나우): 바뀐 주소를 검색 엔진(빙·네이버 등 참여 엔진)에 바로 알림
# 열쇠: INDEXNOW_KEY (아무 영숫자 8~128자). 같은 값이 site/<키>.txt 로 올라가 있어야 함(build 단계에서 만듦).
import sys, os, json, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
KEY = env('INDEXNOW_KEY'); keyflag('indexnow', KEY)
if not KEY:
    status('indexnow', None, '열쇠 없음(INDEXNOW_KEY)'); print('열쇠 없음'); sys.exit(0)
urls = [l.strip() for l in open(os.path.join(ROOT, 'tools', 'urls.txt'), encoding='utf-8') if l.strip()]
open(os.path.join(SITE, KEY + '.txt'), 'w').write(KEY)
body = json.dumps({'host': 'bakssine.netlify.app', 'key': KEY, 'keyLocation': f'https://bakssine.netlify.app/{KEY}.txt', 'urlList': urls[:10000]}).encode()
try:
    req = urllib.request.Request('https://api.indexnow.org/indexnow', data=body, headers={'Content-Type': 'application/json; charset=utf-8', 'User-Agent': 'bakssine/1.0'})
    with urllib.request.urlopen(req, timeout=40) as r: code = r.status
    status('indexnow', code in (200, 202), f'{len(urls)}개 주소, 응답 {code}'); print('색인 알림', code, len(urls))
except Exception as e:
    status('indexnow', False, str(e)[:160]); print('실패', e)
