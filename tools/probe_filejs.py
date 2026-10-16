# 진단: 공공데이터포털 파일데이터 화면의 내려받기 스크립트(script_fileDetail.js)를 받아 tools/_debug 에 저장
import os, urllib.request
ROOT = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(ROOT, '_debug'); os.makedirs(D, exist_ok=True)
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36', 'Referer': 'https://www.data.go.kr/data/15102794/fileData.do'}
for p in ('/js/biz/datset/script_fileDetail.js',):
    try:
        b = urllib.request.urlopen(urllib.request.Request('https://www.data.go.kr' + p, headers=H), timeout=60).read()
        open(os.path.join(D, os.path.basename(p) + '.txt'), 'wb').write(b); print(p, len(b))
    except Exception as e: print(p, e)
