"""식량농업기구 식량가격지수 안내 화면의 연결 주소 전부 기록(진단)"""
import re, json, os, urllib.request
h = urllib.request.urlopen(urllib.request.Request('https://www.fao.org/worldfoodsituation/foodpricesindex/en/', headers={'User-Agent': 'Mozilla/5.0'}), timeout=60).read().decode('utf-8', 'replace')
links = sorted(set(m.group(1) for m in re.finditer(r'href="([^"]+)"', h) if re.search(r'(?i)xls|csv|price|indice|download|docs', m.group(1))))
os.makedirs('tools/_debug', exist_ok=True)
json.dump({'n': len(links), 'links': links[:200]}, open('tools/_debug/probe_fao.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(links), links[:40])
