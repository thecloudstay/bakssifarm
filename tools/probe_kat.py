# 진단: 도매시장 정산·원천(katSale·katOrigin) 명세 원문을 받아 요청변수 확인 — 우분투에서 www.data.go.kr 접속 가능
import re, os, json, urllib.request, http.cookiejar
OP = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130 Safari/537.36', 'Accept-Language': 'ko-KR,ko;q=0.9'}
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_debug'); os.makedirs(D, exist_ok=True)
out = {}
for pk in ('15141809', '15141810', '15141808'):
    try:
        h = OP.open(urllib.request.Request(f'https://www.data.go.kr/data/{pk}/openapi.do', headers=UA), timeout=90).read().decode('utf-8', 'replace')
        m = re.search(r'const\s+swaggerJson\s*=\s*`(.*?)`\s*;', h, re.S)
        sw = m.group(1) if m else ''
        out[pk] = {'len': len(h), 'swagger': sw[:60000], 'cond_snips': [h[max(0, i.start() - 300): i.start() + 300] for i in re.finditer(r'cond', h)][:15],
                   'title': (re.search(r'<title>(.*?)</title>', h, re.S) or [None, ''])[1][:100]}
    except Exception as e: out[pk] = {'err': str(e)}
json.dump(out, open(os.path.join(D, 'kat_swagger.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print({k: (v.get('len'), len(v.get('swagger', ''))) for k, v in out.items()})
