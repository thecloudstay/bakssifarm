# 연동창구 명세 모으기(열쇠 불필요): 공공데이터포털 상세 화면에 박힌 명세(swaggerJson)를 읽어 tools/api_specs.json 으로
# 깃허브 작업 흐름에서 돌림(작업 공간에서는 포털 접속이 막혀 있음)
import json, os, re, time, urllib.request
ROOT = os.path.dirname(os.path.abspath(__file__))
cands = json.load(open(os.path.join(ROOT, 'api_candidates.json'), encoding='utf-8'))
old = {}
p_out = os.path.join(ROOT, 'api_specs.json')
if os.path.exists(p_out):
    old = {x['id']: x for x in json.load(open(p_out, encoding='utf-8'))}
def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (bakssifarm spec reader)', 'Accept-Language': 'ko'})
    with urllib.request.urlopen(req, timeout=40) as r: return r.read().decode('utf-8', 'replace')
def parse_swagger(html):
    m = re.search(r'const\s+swaggerJson\s*=\s*`(.*?)`\s*;', html, re.S)
    if not m: return None
    raw = m.group(1).replace('\\`', '`')
    try: sw = json.loads(raw)
    except Exception:
        try: sw = json.loads(raw.encode().decode('unicode_escape'))
        except Exception: return None
    host = (sw.get('host') or '') + (sw.get('basePath') or '')
    ops = []
    for path, meth in (sw.get('paths') or {}).items():
        g = meth.get('get') or meth.get('post') or {}
        params = [{'name': p.get('name'), 'req': bool(p.get('required')), 'desc': (p.get('description') or '')[:60]} for p in g.get('parameters', []) if p.get('in') in ('query', None)]
        props = {}
        def walk(sch, depth=0):
            if not isinstance(sch, dict) or depth > 8: return
            if '$ref' in sch:
                ref = sch['$ref'].split('/')[-1]; walk((sw.get('definitions') or sw.get('components', {}).get('schemas', {})).get(ref, {}), depth + 1); return
            for k, v in (sch.get('properties') or {}).items():
                if isinstance(v, dict) and (v.get('properties') or v.get('items') or v.get('$ref')): walk(v.get('items', v), depth + 1)
                else: props[k] = (v.get('description') or '')[:40] if isinstance(v, dict) else ''
            if sch.get('items'): walk(sch['items'], depth + 1)
        for code, resp in (g.get('responses') or {}).items():
            walk(resp.get('schema') or (resp.get('content') or {}).get('application/json', {}).get('schema') or {})
        ops.append({'path': path, 'sum': (g.get('summary') or '')[:60], 'params': params, 'props': props})
    return {'host': host, 'scheme': (sw.get('schemes') or ['https'])[0], 'ops': ops}
def parse_plain(html):
    urls = sorted(set(re.findall(r'https?://(?:apis\.data\.go\.kr|data\.ekape\.or\.kr|openapi\.[a-z0-9.]+)/[A-Za-z0-9_/\-.]+', html)))
    names = sorted(set(re.findall(r'<td[^>]*>\s*([a-zA-Z][A-Za-z0-9_]{1,40})\s*</td>', html)))
    return {'urls': urls[:20], 'names': names[:120]}
out = []; ok = 0
for i, c in enumerate(cands):
    rec = dict(c)
    try:
        html = get(f'https://www.data.go.kr/data/{c["id"]}/openapi.do')
        sw = parse_swagger(html)
        if sw and sw['ops']: rec['spec'] = sw; ok += 1
        else: rec['plain'] = parse_plain(html)
        rec['fetched'] = time.strftime('%Y-%m-%d')
    except Exception as e:
        rec = old.get(c['id'], rec); rec['err'] = str(e)[:120]
    out.append(rec); time.sleep(0.6)
json.dump(out, open(p_out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('명세', ok, '/', len(cands))
