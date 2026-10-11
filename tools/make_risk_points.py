# 수급 위험 예보용 지점 만들기(한 번): 시군 중심(육지 기온·습도), 시군별 양식 면허 구역 가운데(바다 수온)
import json, os, glob, collections, math
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'site', 'data')
U = json.load(open(os.path.join(D, 'units.json'), encoding='utf-8'))
sc = U['transform']['scale']; tr = U['transform']['translate']; arcs = []
for a in U['arcs']:
    x = y = 0; pts = []
    for d in a: x += d[0]; y += d[1]; pts.append((x * sc[0] + tr[0], y * sc[1] + tr[1]))
    arcs.append(pts)
land = {}; polys = {}
for g in U['objects']['units']['geometries']:
    xs, ys = [], []
    def walk(a):
        for x in a:
            if isinstance(x, list): walk(x)
            else:
                for p in arcs[x if x >= 0 else ~x]: xs.append(p[0]); ys.append(p[1])
    walk(g['arcs']); land[g['properties']['u']] = [round((min(ys) + max(ys)) / 2, 3), round((min(xs) + max(xs)) / 2, 3)]
AQ = json.load(open(os.path.join(D, 'aqua.json'), encoding='utf-8'))
coast = list(AQ['units'].keys())
pts = collections.defaultdict(list)
for f in glob.glob(os.path.join(D, 'aqua', '*.json')):
    for z in json.load(open(f, encoding='utf-8')):
        if z.get('k') not in ('P', 'H', 'Y'): pass
        try: q = z['p'] if isinstance(z['p'], list) else json.loads(z['p']); p = q[0][0]
        except Exception: continue
        la, lo = p[0], p[1]
        u = min(coast, key=lambda c: (land[c][0] - la) ** 2 + ((land[c][1] - lo) * math.cos(math.radians(la))) ** 2)
        pts[u].append((la, lo))
sea = {}
for u in coast:
    if pts[u]:
        la = sorted(p[0] for p in pts[u])[len(pts[u]) // 2]; lo = sorted(p[1] for p in pts[u])[len(pts[u]) // 2]
        sea[u] = [round(la, 3), round(lo, 3)]
json.dump({'land': land, 'sea': sea}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'risk_points.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print(len(land), len(sea), list(sea.items())[:5])
