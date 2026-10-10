# 연동창구 명세 모으기(열쇠 불필요): 공공데이터포털 상세 화면에 박힌 명세(swaggerJson)를 읽어 tools/api_specs.json 으로
# 깃허브 작업 흐름에서 돌림(작업 공간에서는 포털 접속이 막혀 있음)
import json, os, re, time, urllib.request
ROOT = os.path.dirname(os.path.abspath(__file__))
cands = json.load(open(os.path.join(ROOT, 'api_candidates.json'), encoding='utf-8'))
old = {}
p_out = os.path.join(ROOT, 'api_specs.json')
if os.path.exists(p_out):
    old = {x['id']: x for x in json.load(open(p_out, encoding='utf-8'))}
def get(url, data=None):
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers={'User-Agent': 'Mozilla/5.0 (bakssifarm spec reader)', 'Accept-Language': 'ko', 'X-Requested-With': 'XMLHttpRequest', 'Referer': 'https://www.data.go.kr/'})
    with urllib.request.urlopen(req, timeout=40) as r: return r.read().decode('utf-8', 'replace')
import urllib.parse, html as H
def cells(tr): return [re.sub(r'\s+', ' ', H.unescape(re.sub(r'<[^>]+>', ' ', c))).strip() for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.S)]
def parse_detail(h):
    # 상세기능 조각: 요청주소·요청변수·출력결과 표
    url = None
    m = re.search(r'(https?://[A-Za-z0-9.\-]+(?::\d+)?/[A-Za-z0-9_/\-.]+)', H.unescape(h))
    if m: url = m.group(1)
    tables = re.findall(r'<table.*?</table>', h, re.S)
    params, props = [], {}
    for i, t in enumerate(tables):
        rows = [cells(tr) for tr in re.findall(r'<tr.*?</tr>', t, re.S)]
        head = ' '.join(rows[0]) if rows else ''
        for r in rows[1:]:
            if not r or not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', r[0]): continue
            if '요청' in head or (not props and ('필수' in ' '.join(r) or len(r) >= 5) and i == 0):
                params.append({'name': r[0], 'req': any(x in ('1', '필수', 'Y') for x in r[2:5]), 'desc': (r[1] if len(r) > 1 else '')[:40]})
            else: props[r[0]] = (r[1] if len(r) > 1 else '')[:40]
    return url, params, props
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
ONLY = os.environ.get('SPEC_ONLY', '')
for i, c in enumerate(cands):
    if ONLY and c['id'] not in ONLY.split(','): out.append(old.get(c['id'], c)); continue
    rec = dict(c)
    try:
        html = get(f'https://www.data.go.kr/data/{c["id"]}/openapi.do')
        sw = parse_swagger(html)
        if sw and sw['ops']: rec['spec'] = sw; ok += 1
        else:
            rec['plain'] = parse_plain(html)
            dpk = re.search(r'id="publicDataDetailPk"[^>]*value="([^"]+)"|name="publicDataDetailPk"[^>]*value="([^"]+)"|publicDataDetailPk" value="([^"]+)"', html)
            dpk = next((g for g in (dpk.groups() if dpk else []) if g), None)
            opts = re.findall(r'<option value="(\d+)"[^>]*>\s*([^<]*)', html.split('open_api_detail_select', 1)[-1][:20000]) if 'open_api_detail_select' in html else []
            ops = []; host = ''
            for sq, nm in opts[:6]:
                try:
                    dh = get('https://www.data.go.kr/tcs/dss/selectApiDetailFunction.do', {'oprtinSeqNo': sq, 'publicDataDetailPk': dpk})
                    url, params, props = parse_detail(dh)
                    if url:
                        u = urllib.parse.urlparse(url); host = host or u.netloc
                        ops.append({'path': u.path if u.netloc == host else url, 'sum': nm.strip()[:60], 'params': params, 'props': props, 'full': url})
                except Exception as e: rec.setdefault('detail_err', str(e)[:80])
                time.sleep(0.4)
            if ops:
                rec['spec'] = {'host': host, 'scheme': 'https', 'ops': ops, 'from': 'detail'}; ok += 1
            elif not opts:
                try:
                    lk = json.loads(get('https://www.data.go.kr/tcs/dss/selectApiLinkUrl.do?' + urllib.parse.urlencode({'publicDataPk': c['id']})))
                    if lk.get('linkUrl'): rec['external'] = lk['linkUrl']
                except Exception: pass
            if os.environ.get('SPEC_DEBUG') and c['id'] in os.environ['SPEC_DEBUG'].split(','):
                os.makedirs(os.path.join(ROOT, '_debug'), exist_ok=True); open(os.path.join(ROOT, '_debug', c['id'] + '.html'), 'w', encoding='utf-8').write(html)
        rec['fetched'] = time.strftime('%Y-%m-%d')
    except Exception as e:
        rec = old.get(c['id'], rec); rec['err'] = str(e)[:120]
    out.append(rec); time.sleep(0.6)
json.dump(out, open(p_out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('명세', ok, '/', len(cands))
