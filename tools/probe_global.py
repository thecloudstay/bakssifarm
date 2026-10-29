"""세계 공개 연동창구 통로 점검(진단 작업용) — 미국·브라질·노르웨이·유럽연합·국제기구의 열쇠 없는 연동창구가 깃허브 실행기에서 열리는지 tools/_debug/probe_global.json 에 기록"""
import json, os, datetime as dt, urllib.request, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__))
UA = {'User-Agent': 'Mozilla/5.0 (compatible; bakssifarm-probe/1.0; +https://thecloudstay.github.io/bakssifarm/)', 'Accept': 'application/json,text/csv,text/xml,*/*'}
def get(url, params=None, timeout=40, data=None, headers=None):
    if params: url += ('&' if '?' in url else '?') + urllib.parse.urlencode(params)
    h = dict(UA); h.update(headers or {})
    req = urllib.request.Request(url, headers=h, data=data, method='POST' if data is not None else 'GET')
    with urllib.request.urlopen(req, timeout=timeout) as r: return r.status, r.headers.get('Content-Type', ''), r.read()
def probe(name, url, params=None, data=None, headers=None, show=400):
    try:
        st, ct, b = get(url, params, data=data, headers=headers)
        t = b.decode('utf-8', 'replace')
        return {'ok': True, 'status': st, 'type': ct[:40], 'bytes': len(b), 'head': t[:show]}
    except Exception as e:
        return {'ok': False, 'err': str(e)[:200]}
Y = dt.date.today(); D30 = Y - dt.timedelta(days=30)
out = {'at': dt.datetime.now().strftime('%Y-%m-%d %H:%M')}
# 미국 농무부 의무보고(가축 경락·도축) — 열쇠 없음, 보고서 목록
out['usda_mpr_list'] = probe('usda', 'https://mpr.datamart.ams.usda.gov/services/v1.1/reports', show=1500)
# 미국 농무부 의무보고 상세(2461 국립 일별 생돈 요약 추정)
out['usda_mpr_2461'] = probe('usda', 'https://mpr.datamart.ams.usda.gov/services/v1.1/reports/2461/Summary', {'q': f'report_date={D30.strftime("%m/%d/%Y")}:{Y.strftime("%m/%d/%Y")}'}, show=800)
# 노르웨이 통계청 연어 수출 주간(표 03024) — 메타·최근 6주
out['ssb_meta'] = probe('ssb', 'https://data.ssb.no/api/v0/en/table/03024/', show=1500)
q = {"query": [{"code": "Tid", "selection": {"filter": "top", "values": ["6"]}}], "response": {"format": "json-stat2"}}
out['ssb_data'] = probe('ssb', 'https://data.ssb.no/api/v0/en/table/03024/', data=json.dumps(q).encode(), headers={'Content-Type': 'application/json'}, show=1500)
# 브라질 중앙은행 통계(환율 1, 소비자물가 433) — 열쇠 없음
out['bcb_usdbrl'] = probe('bcb', 'https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados/ultimos/5', {'formato': 'json'})
# 브라질 지리통계원 집계(소비자물가 월별)
out['ibge_ipca'] = probe('ibge', 'https://servicodados.ibge.gov.br/api/v3/agregados/1737/periodos/-3/variaveis/63', {'localidades': 'N1[all]'}, show=600)
# 브라질 세페아(상파울루대) 지표 위젯(소·닭·돼지·옥수수·대두)
out['cepea_widget'] = probe('cepea', 'https://www.cepea.esalq.usp.br/br/widgetproduto.js.php', {'fonte': 'arial', 'tamanho': '10', 'largura': '400px', 'corfundo': 'dbd6b2', 'cortexto': '333333', 'corlinha': 'ede7bf', 'id_indicador[]': ['2', '130', '129', '77', '92']}, show=1500)
# 세계동물보건기구 질병 사건 목록(최근 60일)
body = {"eventIds": [], "reportIds": [], "countries": [], "firstDiseases": [], "secondDiseases": [], "typeStatuses": [], "reasons": [], "eventStatuses": [], "reportTypes": [], "reportStatuses": [],
        "eventStartDate": {"from": (Y - dt.timedelta(days=60)).isoformat(), "to": Y.isoformat()}, "sortColName": "", "sortColOrder": "ASC", "pageNumber": 1, "pageSize": 50}
out['wahis'] = probe('wahis', 'https://wahis.woah.org/api/v1/pi/event/filtered-list?language=en', data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'}, show=1500)
# 유엔 식량농업기구 식량가격지수(월별 파일)
out['fao_fpi'] = probe('fao', 'https://www.fao.org/worldfoodsituation/foodpricesindex/en/', show=300)
out['fao_fpi_csv'] = probe('fao', 'https://www.fao.org/fileadmin/templates/worldfood/Reports_and_docs/Food_price_indices_data_oct.csv', show=400)
# 세계은행 상품값(월별, 요소·대두·옥수수·어분 등)
out['wb_pink'] = probe('wb', 'https://thedocs.worldbank.org/en/doc/18675f1d1639c7a34d463f59263ba0a2-0050012025/related/CMO-Historical-Data-Monthly.xlsx', show=100)
# 세계 재난 경보(지진·태풍·홍수·가뭄) RSS
out['gdacs'] = probe('gdacs', 'https://www.gdacs.org/xml/rss.xml', show=600)
# 유럽연합 농식품 가격(돼지고기 주간)
out['eu_pig'] = probe('eu', 'https://www.ec.europa.eu/agrifood/api/pigmeat/prices', {'memberStateCodes': 'DE,ES,NL,DK', 'beginDate': D30.strftime('%d/%m/%Y'), 'endDate': Y.strftime('%d/%m/%Y')}, show=800)
out['eu_poultry'] = probe('eu', 'https://www.ec.europa.eu/agrifood/api/poultry/prices', {'memberStateCodes': 'PL,DE,FR', 'beginDate': D30.strftime('%d/%m/%Y'), 'endDate': Y.strftime('%d/%m/%Y')}, show=600)
# 일본 기상청 지진 목록
out['jma_quake'] = probe('jma', 'https://www.jma.go.jp/bosai/quake/data/list.json', show=500)
# 미국 항공우주국 농업 기상(브라질 마투그로수 한 점)
out['nasa_power'] = probe('nasa', 'https://power.larc.nasa.gov/api/temporal/daily/point', {'parameters': 'T2M,PRECTOTCORR', 'community': 'AG', 'longitude': -56.1, 'latitude': -15.6, 'start': D30.strftime('%Y%m%d'), 'end': Y.strftime('%Y%m%d'), 'format': 'JSON'}, show=500)
# 미국 농무부 세계 농업 전망(수급표) 공개 파일
out['usda_wasde'] = probe('usda', 'https://www.usda.gov/oce/commodity/wasde/latest.json', show=300)
# 유엔 식량농업기구 통계(생산자 가격, 브라질 닭)
out['faostat'] = probe('faostat', 'https://faostatservices.fao.org/api/v1/en/data/PP', {'area': '21', 'item': '1058', 'element': '5532', 'year': '2024,2025', 'output_type': 'objects'}, show=600)
os.makedirs(os.path.join(HERE, '_debug'), exist_ok=True)
json.dump(out, open(os.path.join(HERE, '_debug', 'probe_global.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({k: (v.get('ok'), v.get('status') or v.get('err', '')[:60], v.get('bytes')) for k, v in out.items() if isinstance(v, dict)}, ensure_ascii=False))
