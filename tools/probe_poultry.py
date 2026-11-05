# 진단: 축평원 가금산물 일일거래가격(계란·육계·토종닭·산란계)·축산물 소비자가격 응답 앞부분 저장(열쇠는 남기지 않음)
# 연동창구 점검(collect_all)에서 「어제 하루」로 물으면 빈 응답 → 최근 30일 범위·거래종류별로 다시 물어 칸 이름과 발표 주기를 확인한다.
import sys, os, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
K = env('DATA_GO_KR_KEY'); B = 'http://data.ekape.or.kr/openapi-data/service/user/grade/'
t = dt.date.today(); e = (t - dt.timedelta(days=1)).strftime('%Y%m%d'); s = (t - dt.timedelta(days=30)).strftime('%Y%m%d')
rng = {'startYmd': s, 'endYmd': e, 'numOfRows': '20', 'pageNo': '1'}
cases = [('poultry/egg', dict(rng, type='1')), ('poultry/egg', dict(rng, type='2')), ('poultry/egg', dict(rng, type='3')),
         ('poultry/chickenSanji', dict(rng, type='1')), ('poultry/chickenSanji', dict(rng, type='2')),
         ('poultry/chickenDomae', rng), ('poultry/nativechichen', rng),
         ('poultry/layingOldChicken', dict(rng, periodType='1')), ('poultry/layingChicken', rng),
         ('consumerPriceDaily', {'standYmd': e, 'judgeKind': '4301', 'itemCd': '21'}),
         ('consumerPriceDaily', {'standYmd': e, 'judgeKind': '4304'}),
         ('consumerPriceMonth', {'standYm': (t.replace(day=1) - dt.timedelta(days=1)).strftime('%Y%m'), 'judgeKind': '4301'})]
out = []
for op, p in cases:
    try: r = get(B + op, dict(p, serviceKey=K), timeout=30, retry=1).decode('utf-8', 'replace')[:3000]
    except Exception as x: r = '오류 ' + str(x)[:200]
    out.append({'op': op, 'params': p, 'resp': r})
os.makedirs(os.path.join(ROOT, 'tools', '_debug'), exist_ok=True)
json.dump(out, open(os.path.join(ROOT, 'tools', '_debug', 'poultry.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
