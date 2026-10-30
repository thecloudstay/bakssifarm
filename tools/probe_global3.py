"""세계 창구 3차 점검 — 유럽연합 계란·유제품 값 창구, 노르웨이 통계청 고등어 표, 세계 유제품 경매 지수"""
import json, os, datetime as dt, urllib.request, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__))
UA = {'User-Agent': 'Mozilla/5.0 (compatible; bakssifarm-probe/1.0)', 'Accept': 'application/json,*/*'}
def get(url, params=None, timeout=60):
    if params: url += ('&' if '?' in url else '?') + urllib.parse.urlencode(params)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r: return r.read().decode('utf-8', 'replace')
Y = dt.date.today(); D = Y - dt.timedelta(days=35); P = {'memberStateCodes': 'DE,FR,ES,NL,IT,PL', 'beginDate': D.strftime('%d/%m/%Y'), 'endDate': Y.strftime('%d/%m/%Y')}
out = {}
for k, u in [('eu_eggs_a', 'https://www.ec.europa.eu/agrifood/api/poultry/eggs/prices'), ('eu_eggs_b', 'https://www.ec.europa.eu/agrifood/api/eggs/prices'), ('eu_eggs_c', 'https://www.ec.europa.eu/agrifood/api/poultry/egg/prices'),
             ('eu_dairy', 'https://www.ec.europa.eu/agrifood/api/dairy/prices'), ('eu_dairy_b', 'https://www.ec.europa.eu/agrifood/api/dairy/weeklyPrices'), ('eu_fruit', 'https://www.ec.europa.eu/agrifood/api/fruitAndVegetable/prices'), ('eu_sheep', 'https://www.ec.europa.eu/agrifood/api/sheepAndGoat/prices')]:
    try: t = get(u, P); out[k] = {'ok': True, 'n': len(t), 'head': t[:700]}
    except Exception as e: out[k] = {'ok': False, 'err': str(e)[:120]}
for k, u in [('ssb_mackerel', 'https://data.ssb.no/api/v0/en/table/?query=mackerel'), ('ssb_fish_export', 'https://data.ssb.no/api/v0/en/table/?query=export%20fish'), ('gdt', 'https://www.globaldairytrade.info/en/product-results/')]:
    try: t = get(u); out[k] = {'ok': True, 'n': len(t), 'head': t[:1200]}
    except Exception as e: out[k] = {'ok': False, 'err': str(e)[:120]}
os.makedirs(os.path.join(HERE, '_debug'), exist_ok=True)
json.dump(out, open(os.path.join(HERE, '_debug', 'probe_global3.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print({k: (v['ok'], v.get('n') or v.get('err')) for k, v in out.items()})
