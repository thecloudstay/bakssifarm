# 국내 실행기에서 원좌표(베셀 중부원점)로만 남긴 인허가 핀을 위경도로 바꿈(올리기 단계, 우분투에서)
import os, json, glob
from pyproj import Transformer
TR = Transformer.from_crs('EPSG:5174', 'EPSG:4326', always_xy=True)
D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'site', 'data', 'biz')
for f in glob.glob(os.path.join(D, '*.json')):
    j = json.load(open(f, encoding='utf-8')); n = 0
    for p in j.get('pins', []):
        if 'x' in p:
            x, y = p.pop('x'), p.pop('y')
            try:
                if x and y: lng, lat = TR.transform(float(x), float(y)); p['lat'], p['lng'] = round(lat, 5), round(lng, 5); n += 1
            except Exception: pass
    if n: json.dump(j, open(f, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':')); print('좌표 바꿈', os.path.basename(f), n)
