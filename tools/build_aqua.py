# 해루낚 어장정보도(국립해양조사원 개방해 2025) 구역을 시군·품종별로 집계
import json, glob, re, collections, os
HN = 'raw/eo/'
units = json.load(open('raw/units_sigun.geojson'))

# 품종 정규화
SPEC = [
 # (정규 이름, 묶음, 찾을 말들)
 ('김', '해조류', ['김']), ('미역', '해조류', ['미역']), ('다시마', '해조류', ['다시마']), ('톳', '해조류', ['톳']),
 ('매생이', '해조류', ['매생이']), ('파래', '해조류', ['파래']), ('모자반', '해조류', ['모자반']), ('꼬시래기', '해조류', ['꼬시래기']),
 ('감태', '해조류', ['감태']), ('청각', '해조류', ['청각']), ('우뭇가사리', '해조류', ['우뭇가사리', '우무']),
 ('굴', '패류', ['굴']), ('꼬막', '패류', ['새고막', '새꼬막', '꼬막', '고막', '참꼬막']), ('전복', '패류', ['전복']),
 ('피조개', '패류', ['피조개']), ('바지락', '패류', ['바지락']), ('홍합', '패류', ['홍합', '담치']), ('가리비', '패류', ['가리비']),
 ('가무락', '패류', ['가무락', '모시조개']), ('키조개', '패류', ['키조개']), ('진주조개', '패류', ['진주조개', '진주']), ('소라', '패류', ['소라']),
 ('백합', '패류', ['백합']), ('동죽', '패류', ['동죽']), ('개조개', '패류', ['개조개']), ('우럭조개', '패류', ['우럭조개']), ('새조개', '패류', ['새조개']),
 ('넙치', '어류', ['넙치', '광어']), ('조피볼락', '어류', ['우럭', '조피볼락']), ('방어', '어류', ['방어', '부시리']), ('참돔', '어류', ['참돔', '돔류', '도미', '돔']),
 ('숭어', '어류', ['숭어']), ('농어', '어류', ['농어']), ('전갱이', '어류', ['전갱이']), ('능성어', '어류', ['능성어', '다금바리']), ('감성돔', '어류', ['감성돔']),
 ('볼락', '어류', ['볼락']), ('강도다리', '어류', ['강도다리']), ('어류', '어류', ['어류', '어종', '어', '양식어']),
 ('멍게', '기타', ['우렁쉥이', '멍게']), ('해삼', '기타', ['해삼']), ('미더덕', '기타', ['미더덕']), ('오만둥이', '기타', ['오만둥이', '오만디']),
 ('성게', '기타', ['성게']), ('새우', '기타', ['새우', '갑각']), ('게', '기타', ['게', '꽃게']), ('낙지', '기타', ['낙지']), ('문어', '기타', ['문어']),
 ('쥐치', '어류', ['쥐치']), ('놀래미', '어류', ['놀래미', '노래미']), ('멸치', '어류', ['멸치']),
 ('맛조개', '패류', ['참맛', '맛조개', '맛']), ('갯지렁이', '기타', ['갯지렁이']), ('우뭇가사리', '해조류', ['천초']), ('멍게', '기타', ['우렁셍이']),
 ('해면동물', '기타', ['해면']), ('해조류', '해조류', ['해조']), ('패류', '패류', ['패류', '조개', '패']), ('정착성 수산동식물', '기타', ['정착성', '유용수산']),
]
def norm_tokens(f):
    out = []
    for raw in re.split(r'[,.·/\n]|\s및\s|\s외', f):
        t = raw.strip()
        t = re.sub(r'\(.*?\)', '', t).strip()
        t0 = t
        t = re.sub(r'(양식|등|류)$', '', t).strip()
        if not t: continue
        hit = None
        for name, grp, keys in SPEC:
            if any(k in t for k in keys) or any(k in t0 for k in keys): hit = (name, grp); break
        out.append(hit or ('기타', '기타'))
    seen = []; [seen.append(x) for x in out if x not in seen]
    return seen or [('기타', '기타')]

# 점이 다각형 안에 있는지
def pip(pt, ring):
    x, y = pt; inside = False; n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]; x2, y2 = ring[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xi = (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1
            if x < xi: inside = not inside
    return inside
feats = []
for f in units['features']:
    g = f['geometry']; polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
    for poly in polys:
        outer = poly[0]; xs = [p[0] for p in outer]; ys = [p[1] for p in outer]
        feats.append((f['properties']['u'], (min(xs), min(ys), max(xs), max(ys)), outer, poly[1:]))
def unit_of(lng, lat):
    for u, bb, outer, holes in feats:
        if bb[0] <= lng <= bb[2] and bb[1] <= lat <= bb[3] and pip((lng, lat), outer) and not any(pip((lng, lat), h) for h in holes):
            return u
    return None
# 바다 위 점은 가장 가까운 시군(경계 꼭짓점 거리)으로
def nearest_unit(lng, lat):
    best = None; bd = 1e9
    for u, bb, outer, holes in feats:
        if abs((bb[0]+bb[2])/2 - lng) > 1.2 or abs((bb[1]+bb[3])/2 - lat) > 1.2: continue
        for p in outer[::3]:
            d = (p[0]-lng)**2 + (p[1]-lat)**2
            if d < bd: bd = d; best = u
    return best

SP = collections.OrderedDict()   # 품종 → {g, n, ha, units{u:[n,ha]}}
UN = collections.defaultdict(lambda: {'n': 0, 'ha': 0.0, 'sp': collections.Counter(), 'ha_sp': collections.Counter(), 'v': [0, 0.0], 'j': 0})
cells = []
os.makedirs('site/data/aqua', exist_ok=True)
miss = 0
for fn in sorted(glob.glob(HN + 'eo_*.json')):
    zones = json.load(open(fn)); out = []
    for z in zones:
        ring = z['p'][0] if z['p'] else []
        if not ring: continue
        lat = sum(p[0] for p in ring) / len(ring); lng = sum(p[1] for p in ring) / len(ring)
        u = unit_of(lng, lat) or nearest_unit(lng, lat)
        if not u: miss += 1; continue
        ha = float(z.get('ha') or 0)
        if z['k'] == 'M':
            UN[u]['v'][0] += 1; UN[u]['v'][1] += ha; kinds = []
        elif z['k'] == 'J':
            UN[u]['j'] += 1; kinds = []
        else:
            kinds = norm_tokens(z['f'])
            UN[u]['n'] += 1; UN[u]['ha'] += ha
            for name, grp in kinds:
                s = SP.setdefault(name, {'g': grp, 'n': 0, 'ha': 0.0, 'units': {}})
                s['n'] += 1; s['ha'] += ha / len(kinds)
                uu = s['units'].setdefault(u, [0, 0.0]); uu[0] += 1; uu[1] += ha / len(kinds)
                UN[u]['sp'][name] += 1; UN[u]['ha_sp'][name] += ha / len(kinds)
        out.append({'k': z['k'], 'f': z['f'], 'a': z['a'], 'ha': z.get('ha'), 'e': z.get('e'), 's': [k[0] for k in kinds], 'p': z['p']})
    base = os.path.basename(fn)
    json.dump(out, open('site/data/aqua/' + base, 'w'), ensure_ascii=False, separators=(',', ':'))
    lats = [p[0] for z in out for r in z['p'] for p in r]; lngs = [p[1] for z in out for r in z['p'] for p in r]
    if out: cells.append({'f': base, 'n': len(out), 'b': [round(min(lats), 3), round(min(lngs), 3), round(max(lats), 3), round(max(lngs), 3)]})
print('miss', miss)
ORDER = ['김', '미역', '다시마', '톳', '매생이', '파래', '모자반', '해조류', '굴', '꼬막', '전복', '피조개', '바지락', '홍합', '가리비', '키조개', '가무락', '진주조개', '소라', '백합', '동죽', '새조개', '패류', '넙치', '조피볼락', '방어', '참돔', '숭어', '농어', '볼락', '감성돔', '능성어', '어류', '멍게', '해삼', '미더덕', '성게', '새우', '오만둥이', '게', '낙지', '해면동물', '기타']
species = []
for name in ORDER + [k for k in SP if k not in ORDER]:
    if name not in SP: continue
    s = SP[name]
    species.append({'k': name, 'g': s['g'], 'n': s['n'], 'ha': round(s['ha'], 1), 'units': {u: [v[0], round(v[1], 1)] for u, v in s['units'].items()}})
units_out = {}
for u, e in UN.items():
    top = [[k, c, round(e['ha_sp'][k], 1)] for k, c in e['sp'].most_common(5)]
    units_out[u] = {'n': e['n'], 'ha': round(e['ha'], 1), 'top': top, 'v': [e['v'][0], round(e['v'][1], 1)], 'j': e['j']}
json.dump({'species': species, 'units': units_out, 'cells': cells,
           'source': '국립해양조사원 어장정보도 2025(개방해, 해루낚 보관본) — 면허 유효 어장 11,486구역. 품종은 면허 표기(「어류등」 같은 분류군 표기 포함)를 정리한 것',
           'kinds': {'P': '패류양식', 'H': '해조류양식', 'Y': '기타양식(어류·전복·멍게 등)', 'M': '마을어업(어촌계)', 'J': '정치망'}},
          open('site/data/aqua.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print(len(species), len(units_out), len(cells))
for s in species[:45]: print(s['k'], s['g'], s['n'], s['ha'], len(s['units']))
