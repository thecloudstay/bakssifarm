# 국내 실행기 진단: 몇몇 연동창구를 여러 변수 조합으로 불러 앞부분을 tools/_debug/probe.json 에 남김(열쇠는 남기지 않음)
import sys, os, json, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
K = env('DATA_GO_KR_KEY'); out = []
T = [('katSale', 'https://apis.data.go.kr/B552845/katSale/trades', [{'cond[trd_clcln_ymd::EQ]': '20261008'}, {'trd_clcln_ymd': '20261008'}, {}]),
     ('katOrigin', 'https://apis.data.go.kr/B552845/katOrigin/trades', [{'cond[trd_clcln_ymd::EQ]': '20261008'}, {}]),
     ('license', 'https://apis.data.go.kr/1741000/livestock_farming_v2/info_v2', [{'type': 'json'}]),
     ('trade', 'https://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList', [{'strtYymm': '202608', 'endYymm': '202608', 'hsSgn': '0201'}])]
for nm, url, vs in T:
    for v in vs:
        p = dict({'serviceKey': K, 'pageNo': 1, 'numOfRows': 3, 'returnType': 'json'}, **v)
        try: r = get(url, p, timeout=30, retry=1).decode('utf-8', 'replace')[:900]
        except Exception as e: r = '오류 ' + str(e)[:200]
        out.append({'name': nm, 'params': v, 'resp': r})
os.makedirs(os.path.join(ROOT, 'tools', '_debug'), exist_ok=True)
json.dump(out, open(os.path.join(ROOT, 'tools', '_debug', 'probe.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('진단 끝', len(out))
