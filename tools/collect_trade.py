# 관세청 수출입 실적(공공데이터포털 「관세청_품목별 국가별 수출입실적」)으로 수입 단가(원/㎏) 만들기
# 열쇠: DATA_GO_KR_KEY. 월 단위. 끝점·항목 이름은 열쇠 발급 뒤 첫 호출에서 확인(아래 표기는 포털 명세 기준, 확인 필요)
import sys, os, json, datetime, xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
KEY = env('DATA_GO_KR_KEY')
if env('ONLY_SCHEDULED') and now().day != 3 and not env('FORCE_RUN'): print('매달 3일에만'); sys.exit(0)
# 비교할 품목: (이름, HS 부호, 우리 쪽 비교 대상)
ITEMS = [('쇠고기(냉장·냉동)', '0201', '한우 경락가'), ('쇠고기 냉동', '0202', '한우 경락가'), ('돼지고기', '0203', '돼지 경락가'),
         ('옥수수(사료용)', '1005', '배합사료 구입가'), ('대두박', '2304', '배합사료 구입가'), ('어분', '2301', '양식 사료 구입가'),
         ('전복', '030781', '전복 위판가'), ('김', '121221', '김 위판가'), ('넙치', '030229', '넙치 위판가'), ('새우', '0306', '새우 위판가')]
if not KEY:
    status('trade', None, '열쇠 없음(DATA_GO_KR_KEY)'); print('열쇠 없음'); sys.exit(0)
URL = 'https://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList'
d = now().date().replace(day=1); months = [(d - datetime.timedelta(days=1)).replace(day=1)]
for _ in range(11): months.append((months[-1] - datetime.timedelta(days=1)).replace(day=1))
def ym(x): return x.strftime('%Y%m')
out = []; errs = []
for name, hs, cmp_ in ITEMS:
    try:
        raw = get(URL, {'serviceKey': KEY, 'strtYymm': ym(months[-1]), 'endYymm': ym(months[0]), 'hsSgn': hs})
        root = ET.fromstring(raw); rows = []
        for it in root.iter('item'):
            g = lambda k: (it.findtext(k) or '').strip()
            if g('statCd') and g('statCd') != '-': continue   # 국가별 줄은 건너뛰고 합계 줄만
            try: imp_amt = float(g('impDlr') or 0); imp_wgt = float(g('impWgt') or 0)
            except ValueError: continue
            if '총계' in (g('year') or g('yymm')): continue   # 기간 합계 줄 빼고 달별만
            if imp_wgt > 0: rows.append({'ym': g('year') or g('yymm'), 'usd_kg': round(imp_amt / imp_wgt, 3), 'wgt_t': round(imp_wgt / 1000, 1)})
        rows.sort(key=lambda r: r['ym']); out.append({'name': name, 'hs': hs, 'cmp': cmp_, 'rows': rows[-12:]})
    except Exception as e:
        errs.append(f'{name} {str(e)[:50]}')
jsave(os.path.join(DATA, 'trade.json'), {'at': stamp(), 'items': out, 'note': '관세청 수출입실적, 달러/㎏ 단가. 원화 환산은 화면에서 월평균 환율로', 'errors': errs}, indent=1)
status('trade', not errs, f'{len(out)}품목' + (' · 실패 ' + ', '.join(errs) if errs else ''))
print('수출입', len(out), errs)
