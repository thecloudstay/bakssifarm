# 진단: 공영도매시장 코드(6자리) 목록 찾기 — 도매시장 통합 홈페이지·옛 연동창구 견본에서 <option> 값 긁기
import re, os, json, urllib.request, http.cookiejar
OP = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36', 'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.5', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8', 'Upgrade-Insecure-Requests': '1', 'Sec-Fetch-Dest': 'document', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'none'}
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_debug'); os.makedirs(D, exist_ok=True)
URLS = ['https://www.data.go.kr/data/15141818/openapi.do', 'https://at.agromarket.kr/', 'https://at.agromarket.kr/domeinfo/sanRealtime.do', 'https://at.agromarket.kr/domeinfo/smallTrade.do',
        'https://at.agromarket.kr/openApi/apiInfo.do', 'https://at.agromarket.kr/domeinfo/marketInfo.do', 'https://api.agromarket.kr/sample/', 'https://www.agromarket.kr/',
        'https://at.agromarket.kr/statistics/daily.do', 'https://at.agromarket.kr/mrktInfo/mrktList.do']
out = {'pages': {}, 'codes': {}}
for u in URLS:
    try:
        h = OP.open(urllib.request.Request(u, headers=UA), timeout=40).read().decode('utf-8', 'replace')
        cs = re.findall(r'<option[^>]*value=["\']?(\d{6})["\']?[^>]*>\s*([^<]{1,30})<', h)
        js = re.findall(r'["\'](\d{6})["\']\s*[,:]\s*["\']([가-힣()\s]{2,20})["\']', h)
        for c, n in cs + js: out['codes'][c] = n.strip()
        links = sorted(set(re.findall(r'href=["\'](/[a-zA-Z]+/[a-zA-Z]+\.do)', h)))[:80]
        if 'data.go.kr' in u: out['katcode_snips'] = [h[max(0, m.start() - 200): m.start() + 400] for m in re.finditer('도매시장', h)][:12]
        out['pages'][u] = {'len': len(h), 'n': len(cs) + len(js), 'links': links, 'mk': [h[max(0, m.start() - 150): m.start() + 150] for m in re.finditer('가락', h)][:3]}
    except Exception as e: out['pages'][u] = {'err': str(e)[:120]}
json.dump(out, open(os.path.join(D, 'mkt_codes.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(out['codes']), {k: v.get('len', v.get('err')) for k, v in out['pages'].items()})
