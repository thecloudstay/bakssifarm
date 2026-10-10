# 공공데이터포털 밖 제공처(열쇠가 따로 있는 곳) — 열쇠가 있는 것만 돌고, 없으면 「열쇠 대기」로 연동 대장에 올림
#  KAMIS_KEY+KAMIS_ID : 한국농수산식품유통공사 농산물유통정보 — 축산·수산 부류 일일 소매·도매 가격(소비자 쪽 가격과 산지 경락의 차이)
#  ECOS_KEY          : 한국은행 경제통계 — 원/달러, 원/100엔 환율(수입 사료·수입 축수산물 원가 환산)
#  OPINET_KEY        : 한국석유공사 오피넷 — 전국 평균 경유·등유 값(어선·하우스·축사 난방 원가)
#  KOSIS_KEY         : 통계청 국가통계포털 — 가축동향조사 시도별 사육 마릿수(분기)
#  USDA_KEY          : 미국 농무부 시장뉴스 — 미국 소고기 도매 가격(수입 소고기 원가 비교)
import sys, os, json, datetime, base64
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
OUT = os.path.join(DATA, 'extra'); T = now().date()
reg = jload(os.path.join(DATA, 'apis.json'), {'items': {}})
def mark(sid, title, dom, cat, state, n=None, msg='', link=''):
    e = reg['items'].setdefault(sid, {}); e.update({'title': title, 'dom': dom, 'cat': cat, 'state': state, 'at': stamp(), 'msg': msg[:140], 'link': link, 'host': link.split('/')[2] if link else ''})
    if n is not None: e['n'] = n
def J(url, params=None, headers=None): return json.loads(get(url, params, headers=headers))

# 1) 농산물유통정보: 축산(500)·수산(600) 부류, 소매(01)·도매(02)
K, KID = env('KAMIS_KEY'), env('KAMIS_ID')
if K and KID:
    try:
        out = {'at': stamp(), 'rows': []}
        for cls in ('01', '02'):
            for cat in ('500', '600'):
                j = J('https://www.kamis.or.kr/service/price/xml.do', {'action': 'dailyPriceByCategoryList', 'p_product_cls_code': cls, 'p_item_category_code': cat,
                      'p_regday': (T - datetime.timedelta(days=1)).isoformat(), 'p_convert_kg_yn': 'N', 'p_cert_key': K, 'p_cert_id': KID, 'p_returntype': 'json'})
                items = (j.get('data') or {}).get('item') or []
                for it in items if isinstance(items, list) else [items]:
                    out['rows'].append({'구분': '소매' if cls == '01' else '도매', '부류': '축산' if cat == '500' else '수산', '품목': it.get('item_name'), '품종': it.get('kind_name'),
                                        '등급': it.get('rank'), '단위': it.get('unit'), '당일': it.get('dpr1'), '1일전': it.get('dpr2'), '1주전': it.get('dpr3'), '1개월전': it.get('dpr5'), '1년전': it.get('dpr6')})
        jsave(os.path.join(OUT, 'kamis.json'), out)
        mark('ext-kamis', '농산물유통정보 축산·수산 소매·도매 가격', '공통', '시세·거래', '정상' if out['rows'] else '빈 응답', len(out['rows']), link='https://www.kamis.or.kr')
    except Exception as e: mark('ext-kamis', '농산물유통정보 축산·수산 소매·도매 가격', '공통', '시세·거래', '실패', msg=str(e), link='https://www.kamis.or.kr')
else: mark('ext-kamis', '농산물유통정보 축산·수산 소매·도매 가격', '공통', '시세·거래', '제공처 열쇠', msg='KAMIS_KEY, KAMIS_ID', link='https://www.kamis.or.kr/customer/reference/openapi_list.do')

# 2) 한국은행 환율
K = env('ECOS_KEY')
if K:
    try:
        s, e = (T - datetime.timedelta(days=40)).strftime('%Y%m%d'), T.strftime('%Y%m%d'); out = {'at': stamp()}
        for code, nm in (('0000001', '원/달러'), ('0000002', '원/100엔')):
            j = J(f'https://ecos.bok.or.kr/api/StatisticSearch/{K}/json/kr/1/100/731Y001/D/{s}/{e}/{code}')
            out[nm] = [[r['TIME'], float(r['DATA_VALUE'])] for r in (j.get('StatisticSearch') or {}).get('row', [])]
        jsave(os.path.join(OUT, 'fx.json'), out); mark('ext-ecos', '한국은행 환율(원/달러·원/100엔)', '공통', '수출입', '정상', len(out['원/달러']), link='https://ecos.bok.or.kr')
    except Exception as e: mark('ext-ecos', '한국은행 환율(원/달러·원/100엔)', '공통', '수출입', '실패', msg=str(e), link='https://ecos.bok.or.kr')
else: mark('ext-ecos', '한국은행 환율(원/달러·원/100엔)', '공통', '수출입', '제공처 열쇠', msg='ECOS_KEY', link='https://ecos.bok.or.kr/api/')

# 3) 오피넷 전국 평균 기름값
K = env('OPINET_KEY')
if K:
    try:
        j = J('https://www.opinet.co.kr/api/avgAllPrice.do', {'out': 'json', 'code': K})
        oil = [{'날짜': o.get('TRADE_DT'), '유종': o.get('PRODNM'), '값': o.get('PRICE'), '전일대비': o.get('DIFF')} for o in (j.get('RESULT') or {}).get('OIL', [])]
        p = os.path.join(OUT, 'oil.json'); old = jload(p, {'hist': []})
        hist = [h for h in old.get('hist', []) if h['날짜'] != (oil[0]['날짜'] if oil else '')] + oil
        jsave(p, {'at': stamp(), 'today': oil, 'hist': hist[-800:]}); mark('ext-opinet', '오피넷 전국 평균 경유·등유 값', '공통', '원가', '정상', len(oil), link='https://www.opinet.co.kr')
    except Exception as e: mark('ext-opinet', '오피넷 전국 평균 경유·등유 값', '공통', '원가', '실패', msg=str(e), link='https://www.opinet.co.kr')
else: mark('ext-opinet', '오피넷 전국 평균 경유·등유 값', '공통', '원가', '제공처 열쇠', msg='OPINET_KEY', link='https://www.opinet.co.kr/user/custapi/openApiInfo.do')

# 4) 국가통계포털 가축동향조사(시도별 사육 마릿수)
K = env('KOSIS_KEY')
if K:
    try:
        j = J('https://kosis.kr/openapi/Param/statisticsParameterData.do', {'method': 'getList', 'apiKey': K, 'itmId': 'ALL', 'objL1': 'ALL', 'objL2': 'ALL', 'format': 'json', 'jsonVD': 'Y',
              'prdSe': 'Q', 'newEstPrdCnt': '4', 'orgId': '101', 'tblId': 'DT_1EO099'})
        rows = j if isinstance(j, list) else []
        jsave(os.path.join(OUT, 'kosis_livestock.json'), {'at': stamp(), 'rows': [{k: r.get(k) for k in ('PRD_DE', 'C1_NM', 'C2_NM', 'ITM_NM', 'DT', 'UNIT_NM')} for r in rows]})
        mark('ext-kosis', '통계청 가축동향조사(시도별 사육 마릿수)', '동물농장', '사육·생산', '정상' if rows else '빈 응답', len(rows), msg='' if rows else str(j)[:120], link='https://kosis.kr')
    except Exception as e: mark('ext-kosis', '통계청 가축동향조사(시도별 사육 마릿수)', '동물농장', '사육·생산', '실패', msg=str(e), link='https://kosis.kr')
else: mark('ext-kosis', '통계청 가축동향조사(시도별 사육 마릿수)', '동물농장', '사육·생산', '제공처 열쇠', msg='KOSIS_KEY', link='https://kosis.kr/openapi/')

# 5) 미국 농무부 시장뉴스 — 소고기 도매 부분육 가격(보고서 2453)
K = env('USDA_KEY')
if K:
    try:
        auth = base64.b64encode(f'{K}:'.encode()).decode()
        j = J('https://marsapi.ams.usda.gov/services/v1.2/reports/2453', {'lastDays': '30'}, headers={'Authorization': 'Basic ' + auth, 'User-Agent': 'bakssifarm/1.0'})
        res = j.get('results', []) if isinstance(j, dict) else []
        jsave(os.path.join(OUT, 'usda_beef.json'), {'at': stamp(), 'rows': res[:400]})
        mark('ext-usda', '미국 농무부 소고기 도매 부분육 가격', '동물농장', '수출입', '정상' if res else '빈 응답', len(res), link='https://mymarketnews.ams.usda.gov')
    except Exception as e: mark('ext-usda', '미국 농무부 소고기 도매 부분육 가격', '동물농장', '수출입', '실패', msg=str(e), link='https://mymarketnews.ams.usda.gov')
else: mark('ext-usda', '미국 농무부 소고기 도매 부분육 가격', '동물농장', '수출입', '제공처 열쇠', msg='USDA_KEY', link='https://mymarketnews.ams.usda.gov/mymarketnews-api')

import collections
reg['summary'] = dict(collections.Counter(v.get('state', '?') for v in reg['items'].values()))
jsave(os.path.join(DATA, 'apis.json'), reg, indent=1)
print('제공처 연동', {k: v['state'] for k, v in reg['items'].items() if k.startswith('ext-')})
