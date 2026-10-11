# 파일데이터 가공 → 공개 집계(개별 업소 명단 없음)
#  site/data/seastock.json : 수협 물류센터·공판장 재고(㎏)와 조합창고 재고(수량) — 달 초 대비 달 말, 품목별(재고가 쌓이면 값 내림 압력)
# 원본은 같은 작업 안의 .cache/files(collect_files.py가 받음)에서 읽고, 없으면 앞서 만든 공개 집계를 그대로 둔다.
import sys, os, io, csv, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
RAW = os.path.join(ROOT, '.cache', 'files')
def rows(i):
    for ext in ('csv', 'CSV'):
        p = os.path.join(RAW, f'{i}.{ext}')
        if os.path.exists(p):
            b = open(p, 'rb').read()
            for enc in ('utf-8-sig', 'cp949'):
                try: t = b.decode(enc); break
                except UnicodeDecodeError: continue
            else: t = b.decode('cp949', 'replace')
            return list(csv.DictReader(io.StringIO(t)))
    return None
def num(x):
    try: return float(str(x).replace(',', '') or 0)
    except ValueError: return 0.0
made = []
# ── 수산 재고
a = rows('15102798'); c = rows('15102800')
if a or c:
    out = {'at': stamp(), 'source': '해양수산부 수협 물류센터·공판장 품목별 재고 현황, 조합창고 품목별 창고 재고 현황(공공데이터포털 파일데이터)'}
    if a:
        days = sorted({r['기준일자'] for r in a}); d0, d1 = days[0], days[-1]
        by = collections.defaultdict(lambda: [0.0, 0.0]); tot = collections.Counter()
        for r in a:
            k = r['수산물품목명'].strip() + (r.get('상태가공분류명') or '').strip(); kg = num(r.get('재고량(킬로그램)'))
            tot[r['기준일자']] += kg
            if r['기준일자'] == d0: by[k][0] += kg
            if r['기준일자'] == d1: by[k][1] += kg
        it = sorted(by.items(), key=lambda x: -x[1][1])[:30]
        out['center'] = {'from': d0, 'to': d1, 'total': [[d[5:], round(tot[d])] for d in days],
                         'items': [[k, round(v[0]), round(v[1]), (round((v[1] / v[0] - 1) * 100, 1) if v[0] > 0 else None)] for k, v in it]}
    if c:
        days = sorted({r['기준일자'] for r in c}); d0, d1 = days[0], days[-1]
        by = collections.defaultdict(lambda: [0.0, 0.0]); tot = collections.Counter(); coops = collections.Counter()
        for r in c:
            k = r['표준어종명'].strip(); q = num(r.get('수량'))
            tot[r['기준일자']] += q
            if r['기준일자'] == d0: by[k][0] += q
            if r['기준일자'] == d1: by[k][1] += q; coops[k] += 1
        it = sorted(by.items(), key=lambda x: -x[1][1])[:30]
        out['coop'] = {'from': d0, 'to': d1, 'total': [[d[5:], round(tot[d])] for d in days],
                       'items': [[k, round(v[0]), round(v[1]), (round((v[1] / v[0] - 1) * 100, 1) if v[0] > 0 else None)] for k, v in it]}
    out['month'] = ((out.get('center') or out.get('coop'))['to'])[:7]
    jsave(os.path.join(DATA, 'seastock.json'), out); made.append('수산 재고')
# 부산공동어시장 위판정보(15130234)는 중량·금액 단위가 줄마다 들쭉날쭉해 ㎏당 값이 맞지 않아 쓰지 않음(2026-10 확인)
print('파일데이터 가공', made)
