"""세계 공개 연동창구 2차 점검 — 미국 농무부 보고서 목록·항목 이름, 세페아 표 전체, 유럽연합 닭고기 품목 이름, 세계동물보건기구(긴 대기)"""
import json, os, re, datetime as dt, urllib.request, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__))
UA = {'User-Agent': 'Mozilla/5.0 (compatible; bakssifarm-probe/1.0)', 'Accept': 'application/json,text/csv,text/xml,*/*'}
def get(url, params=None, timeout=120, data=None, headers=None):
    if params: url += ('&' if '?' in url else '?') + urllib.parse.urlencode(params)
    h = dict(UA); h.update(headers or {})
    req = urllib.request.Request(url, headers=h, data=data, method='POST' if data is not None else 'GET')
    with urllib.request.urlopen(req, timeout=timeout) as r: return r.read().decode('utf-8', 'replace')
out = {'at': dt.datetime.now().strftime('%Y-%m-%d %H:%M')}
Y = dt.date.today(); D = Y - dt.timedelta(days=21)
def safe(k, fn):
    try: out[k] = fn()
    except Exception as e: out[k] = {'err': str(e)[:200]}
def usda_list():
    t = get('https://mpr.datamart.ams.usda.gov/services/v1.1/reports', timeout=170)
    j = json.loads(t); rows = j if isinstance(j, list) else j.get('results', j)
    keep = []
    for r in rows:
        name = json.dumps(r, ensure_ascii=False)
        if re.search(r'Daily|Weekly', name) and re.search(r'Hog|Cattle|Beef|Pork|Chicken|Broiler|Egg|Turkey|Lamb', name): keep.append(r)
    return {'n_all': len(rows), 'keep': keep[:80]}
safe('usda_list', usda_list)
safe('usda_2461_avg', lambda: json.loads(get('https://mpr.datamart.ams.usda.gov/services/v1.1/reports/2461/Weekly%20Average%20Cutout%20Values', {'q': f'report_date={D.strftime("%m/%d/%Y")}:{Y.strftime("%m/%d/%Y")}'}))['results'][:3])
for rid in ('2511', '2675', '3457', '2498', '2466', '2453'):
    safe(f'usda_{rid}', lambda rid=rid: {'sections': json.loads(get(f'https://mpr.datamart.ams.usda.gov/services/v1.1/reports/{rid}', {'q': f'report_date={D.strftime("%m/%d/%Y")}:{Y.strftime("%m/%d/%Y")}'})).get('reportSections'), 'first': json.loads(get(f'https://mpr.datamart.ams.usda.gov/services/v1.1/reports/{rid}', {'q': f'report_date={D.strftime("%m/%d/%Y")}:{Y.strftime("%m/%d/%Y")}'})).get('results', [])[:2]})
def cepea():
    t = get('https://www.cepea.esalq.usp.br/br/widgetproduto.js.php', {'fonte': 'arial', 'tamanho': '10', 'largura': '400px', 'corfundo': 'dbd6b2', 'cortexto': '333333', 'corlinha': 'ede7bf', 'id_indicador[]': [str(i) for i in (2, 130, 129, 77, 92, 53, 54, 181, 12, 91)]})
    rows = re.findall(r'<tr>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*</tr>', t, re.S)
    return [[re.sub('<[^>]+>', '', c).strip() for c in r] for r in rows]
safe('cepea', cepea)
def eu_poultry():
    j = json.loads(get('https://www.ec.europa.eu/agrifood/api/poultry/prices', {'memberStateCodes': 'PL,DE,FR,ES,NL,IT', 'beginDate': D.strftime('%d/%m/%Y'), 'endDate': Y.strftime('%d/%m/%Y')}))
    return sorted({(r.get('productName'), r.get('priceType'), r.get('unit')) for r in j})
safe('eu_poultry_products', eu_poultry)
def eu_pig():
    j = json.loads(get('https://www.ec.europa.eu/agrifood/api/pigmeat/prices', {'memberStateCodes': 'DE,ES,NL,DK,FR,PL', 'beginDate': D.strftime('%d/%m/%Y'), 'endDate': Y.strftime('%d/%m/%Y')}))
    return sorted({(r.get('pigClass'), r.get('unit')) for r in j})
safe('eu_pig_classes', eu_pig)
def eu_beef():
    j = json.loads(get('https://www.ec.europa.eu/agrifood/api/beef/prices', {'memberStateCodes': 'IE,FR,DE,PL', 'beginDate': D.strftime('%d/%m/%Y'), 'endDate': Y.strftime('%d/%m/%Y')}))
    return {'n': len(j), 'first': j[:2], 'cats': sorted({(r.get('category'), r.get('unit')) for r in j})[:12]}
safe('eu_beef', eu_beef)
body = {"eventIds": [], "reportIds": [], "countries": [], "firstDiseases": [], "secondDiseases": [], "typeStatuses": [], "reasons": [], "eventStatuses": [], "reportTypes": [], "reportStatuses": [], "eventStartDate": {"from": (Y - dt.timedelta(days=45)).isoformat(), "to": Y.isoformat()}, "sortColName": "", "sortColOrder": "ASC", "pageNumber": 1, "pageSize": 30}
safe('wahis', lambda: get('https://wahis.woah.org/api/v1/pi/event/filtered-list?language=en', data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'}, timeout=170)[:2500])
safe('ibge_ipca', lambda: get('https://servicodados.ibge.gov.br/api/v3/agregados/1737/periodos/-3/variaveis/63', {'localidades': 'N1[all]'}, timeout=120)[:600])
def wb_sheet():
    import io, zipfile
    url = 'https://thedocs.worldbank.org/en/doc/18675f1d1639c7a34d463f59263ba0a2-0050012025/related/CMO-Historical-Data-Monthly.xlsx'
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r: b = r.read()
    z = zipfile.ZipFile(io.BytesIO(b)); names = z.namelist()
    wb = z.read('xl/workbook.xml').decode('utf-8', 'replace')
    return {'names': names[:20], 'sheets': re.findall(r'<sheet [^>]*name="([^"]+)"', wb)}
safe('wb_sheets', wb_sheet)
os.makedirs(os.path.join(HERE, '_debug'), exist_ok=True)
json.dump(out, open(os.path.join(HERE, '_debug', 'probe_global2.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print({k: (('err' in v) if isinstance(v, dict) else 'ok') for k, v in out.items()})
