# 연동창구 명세 모으기(열쇠 불필요): 공공데이터포털 상세 화면에 박힌 명세(swaggerJson)를 읽어 tools/api_specs.json 으로
# 깃허브 작업 흐름에서 돌림(작업 공간에서는 포털 접속이 막혀 있음)
import json, os, re, time, urllib.request
ROOT = os.path.dirname(os.path.abspath(__file__))
cands = json.load(open(os.path.join(ROOT, 'api_candidates.json'), encoding='utf-8'))
old = {}
p_out = os.path.join(ROOT, 'api_specs.json')
if os.path.exists(p_out):
    old = {x['id']: x for x in json.load(open(p_out, encoding='utf-8'))}
import http.cookiejar
JAR = http.cookiejar.CookieJar(); OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(JAR))
REF = ['https://www.data.go.kr/']
def get(url, data=None):
    body = urllib.parse.urlencode(data).encode() if data else None
    hd = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36', 'Accept-Language': 'ko-KR,ko', 'Referer': REF[0]}
    if data is not None: hd.update({'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'Origin': 'https://www.data.go.kr', 'Accept': 'text/html, */*; q=0.01'})
    else: REF[0] = url
    req = urllib.request.Request(url, data=body, headers=hd)
    with OPENER.open(req, timeout=40) as r: return r.read().decode('utf-8', 'replace')
import urllib.parse, urllib.error, html as H
def cells(tr): return [re.sub(r'\s+', ' ', H.unescape(re.sub(r'<[^>]+>', ' ', c))).strip() for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.S)]
def parse_detail(h):
    # 상세기능 조각: 요청주소 + 요청변수 표 + 출력결과 표 (칸: 국문·영문·크기·구분·샘플·설명)
    url = None
    m = re.search(r'요청주소.*?(https?://[A-Za-z0-9.\-]+(?::\d+)?/[A-Za-z0-9_/\-.]+)', H.unescape(re.sub(r'<[^>]+>', ' ', h)), re.S)
    if m: url = m.group(1)
    cut = h.find('출력결과')
    params, props = [], {}
    for part, kind in ((h[:cut] if cut > 0 else h, 'req'), (h[cut:] if cut > 0 else '', 'res')):
        for t in re.findall(r'<table.*?</table>', part, re.S):
            for tr in re.findall(r'<tr.*?</tr>', t, re.S):
                cs = [x for x in cells(tr) if x != '']
                if len(cs) < 2: continue
                en = next((x for x in cs[:3] if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', x)), None)
                if not en or en in ('항목명',): continue
                ko = cs[0] if cs[0] != en else ''
                if kind == 'req': params.append({'name': en, 'req': '필수' in ' '.join(cs) or ' 1 ' in ' ' + ' '.join(cs[2:4]) + ' ', 'desc': ko[:40], 'sample': cs[-2][:30] if len(cs) >= 4 else ''})
                else: props[en] = ko[:40]
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
            opts = re.findall(r'<option value="(\d+)"[^>]*>\s*([^<]*?)\s*</option>', html.split('open_api_detail_select', 1)[-1][:20000]) if 'open_api_detail_select' in html else []
            ops = []; host = ''
            for sq, nm in opts[:6]:
                try:
                    dh = get('https://www.data.go.kr/tcs/dss/selectApiDetailFunction.do', {'oprtinSeqNo': sq, 'publicDataDetailPk': dpk, 'publicDataPk': c['id']})
                    if os.environ.get('SPEC_DEBUG') and c['id'] in os.environ['SPEC_DEBUG'].split(','):
                        os.makedirs(os.path.join(ROOT, '_debug'), exist_ok=True); open(os.path.join(ROOT, '_debug', c['id'] + '_' + sq + '.html'), 'w', encoding='utf-8').write(dh)
                    url, params, props = parse_detail(dh)
                    if url:
                        u = urllib.parse.urlparse(url); host = host or u.netloc
                        ops.append({'path': u.path if u.netloc == host else url, 'sum': nm.strip()[:60], 'params': params, 'props': props, 'full': url})
                except urllib.error.HTTPError as e:
                    rec.setdefault('detail_err', f'{e.code} ' + e.read().decode('utf-8', 'replace')[:200])
                except Exception as e: rec.setdefault('detail_err', str(e)[:80])
                time.sleep(0.4)
            if ops:
                rec['spec'] = {'host': host, 'scheme': 'https', 'ops': ops, 'from': 'detail'}; ok += 1
            elif not opts:
                # 바로가기(링크형): 표준데이터는 다른 번호로 연결됨 → 화면의 fn_goUrlLink('번호') 를 우선
                lpk = re.search(r"fn_goUrlLink\('(\d+)'\)", html)
                for pk in dict.fromkeys([lpk.group(1) if lpk else c['id'], c['id']]):
                    try:
                        lk = json.loads(get('https://www.data.go.kr/tcs/dss/selectApiLinkUrl.do?' + urllib.parse.urlencode({'publicDataPk': pk})))
                        if isinstance(lk, str): lk = json.loads(lk)
                        if lk.get('linkUrl'): rec['external'] = lk['linkUrl']; rec['link_pk'] = pk; break
                        rec['link_err'] = str(lk.get('errorDc') or lk)[:120]
                    except Exception as e: rec['link_err'] = str(e)[:120]
            if os.environ.get('SPEC_DEBUG') and c['id'] in os.environ['SPEC_DEBUG'].split(','):
                os.makedirs(os.path.join(ROOT, '_debug'), exist_ok=True); open(os.path.join(ROOT, '_debug', c['id'] + '.html'), 'w', encoding='utf-8').write(html)
        if rec.get('external'):
            # 제공처 화면에서 부르는 주소 단서 모으기(농식품 공공데이터: Grid_… 번호, 그 밖: api 들어간 주소)
            try:
                eh = get(rec['external'])
                grids = sorted(set(re.findall(r'Grid_\d+_\d+', eh)))
                apis = sorted(set(u for u in re.findall(r'https?://[A-Za-z0-9.\-:]+/[A-Za-z0-9_/\-.{}]*', eh) if re.search(r'api', u, re.I) and not u.endswith(('.js', '.css', '.png', '.gif', '.jpg'))))[:15]
                rec['ext_hint'] = {'grids': grids[:10], 'apis': apis}
                if os.environ.get('SPEC_DEBUG') and (c['id'] in os.environ['SPEC_DEBUG'].split(',') or 'ext' in os.environ['SPEC_DEBUG'].split(',')):
                    os.makedirs(os.path.join(ROOT, '_debug'), exist_ok=True); open(os.path.join(ROOT, '_debug', c['id'] + '_ext.html'), 'w', encoding='utf-8').write(eh)
            except Exception as e: rec['ext_err'] = str(e)[:120]
        rec['fetched'] = time.strftime('%Y-%m-%d')
    except Exception as e:
        rec = old.get(c['id'], rec); rec['err'] = str(e)[:120]
    out.append(rec); time.sleep(0.6)
json.dump(out, open(p_out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('명세', ok, '/', len(cands))
