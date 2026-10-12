# 진단: 축평원 등급판정 연동창구 응답 앞부분 저장(열쇠는 남기지 않음)
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
K = env('DATA_GO_KR_KEY'); B = 'http://data.ekape.or.kr/openapi-data/service/user/grade/'
out = []
for op, p in [('auct/cattle', {'startYmd': '20261008', 'endYmd': '20261008', 'breedCd': '024001', 'sexCd': '025003', 'qgradeYn': 'N', 'defectIncludeYn': 'Y'}),
              ('auct/cattle', {'startYmd': '20261008', 'endYmd': '20261008'}),
              ('auct/pigGrade', {'startYmd': '20261008', 'endYmd': '20261008', 'skinYn': 'Y', 'egradeExceptYn': 'N'}),
              ('auct/pigGrade', {'startYmd': '20261008', 'endYmd': '20261008'})]:
    try: r = get(B + op, dict(p, serviceKey=K), timeout=30, retry=1).decode('utf-8', 'replace')[:2500]
    except Exception as e: r = '오류 ' + str(e)[:200]
    out.append({'op': op, 'params': p, 'resp': r})
os.makedirs(os.path.join(ROOT, 'tools', '_debug'), exist_ok=True)
json.dump(out, open(os.path.join(ROOT, 'tools', '_debug', 'ekape.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
