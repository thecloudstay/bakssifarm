# 박씨팜 물가 지수(2026-10-28) — 흩어진 값 자료를 한 줄의 지수로 묶어 「천천히 오르나 내리나」를 본다.
#   ① 갈래 지수: 농산(공영도매시장 정산 일별, 품목 거래금액 가중 연쇄), 축산(한우 거세·돼지 탕박 등외제외 경락가, 두수×값 가중), 수산(수협 위판 일별·월별, 어종 금액 가중 연쇄)
#   ② 종합 지수: 축산 0.40 · 농산 0.35 · 수산 0.25 (가계 식료품 지출 비중 근사)
#   ③ 원가 압력 지수: 사료 원가 지수 0.40 · 경유 0.25 · 원/달러 0.25 · 천연가스 0.10 (일별, 2년)
#   ④ 세계 요인 활성 점수: 날마다 켜진 요인의 단계 합(기록이 쌓이는 대로)
#   고정 가중 기하 지수: 지수_t = exp(Σ w_i·ln(P_it/P_i기준)/Σ w_i)×100, 기준값 = 품목이 처음 보인 5일 평균(≈100), 가중치 = 기간 거래금액 비중(고정). 반쪽 장(거래 금액이 중앙값의 60% 아래)은 뺌.
#   결과 site/data/pindex.json — 지수 줄·계량 요약(trend_lib.metrics)·구성 품목 수. 화면은 forecast_pages.index_page 가 그린다.
import sys, os, re, json, glob, math, statistics, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from trend_lib import metrics
W_SECT = {'축산': 0.40, '농산': 0.35, '수산': 0.25}
W_COST = {'feed': 0.40, 'diesel': 0.25, 'usdkrw': 0.25, 'natgas': 0.10}

def chain(days):
    """고정 가중 기하 지수(연쇄 아님 — 들쭉날쭉한 날이 쌓여도 새지 않음).
    days = [(날짜, {품목: (값, 가중치)})] 오름차순. 품목 가중치 = 기간 전체 가중치 합의 비중(고정), 기준값 = 그 품목이 처음 보인 5일 평균.
    지수_t = exp( Σ_{그날 있는 품목} w_i·ln(P_it/P_i기준) / Σ w_i ) × 100 — 그날 없는 품목은 빼고 가중치를 다시 정규화."""
    if not days: return []
    tot = collections.defaultdict(float); first = collections.defaultdict(list)
    for d, cur in days:
        for k, (p, w) in cur.items():
            if p and w: tot[k] += w
            if p and len(first[k]) < 5: first[k].append(p)
    allw = sum(tot.values()) or 1
    W = {k: v / allw for k, v in tot.items()}; REF = {k: statistics.mean(v) for k, v in first.items() if v}
    out = []
    for d, cur in days:
        ks = [k for k in cur if cur[k][0] and k in REF and REF[k] > 0 and W.get(k)]
        if not ks: continue
        sw = sum(W[k] for k in ks)
        if sw < 0.3 * sum(W.values()): continue   # 그날 바구니가 전체의 3할도 안 되면(반쪽 장) 뺌
        lr = sum(W[k] / sw * max(-1.2, min(1.2, math.log(cur[k][0] / REF[k]))) for k in ks)
        out.append((d, round(100 * math.exp(lr), 2)))
    return out

# ── 농산 ─────────────────────────────────────────────────────
def farm_index():
    files = sorted(glob.glob(os.path.join(PRIVATE, 'wholesale', '*.json')))
    days = []
    for p in files:
        try: d = json.load(open(p, encoding='utf-8'))
        except Exception: continue
        tot = sum((v[2] or 0) for v in d.values())
        days.append((os.path.basename(p)[:10], d, tot))
    if not days: return None
    med = sorted(x[2] for x in days)[len(days) // 2]
    days = [(d, {k: (v[0], v[2]) for k, v in dd.items() if v[0] and v[1] and v[1] >= 1000}, t) for d, dd, t in days if t >= med * 0.6]
    ser = chain([(d, dd) for d, dd, _ in days])
    return {'daily': ser, 'items': round(statistics.mean(len(dd) for _, dd, _ in days)) if days else 0, 'src': '공영도매시장 26곳 정산 ㎏당 값 — 품목 거래금액 가중 고정 기하 지수(처음 5일 평균 = 100)', 'vol': [(d, round(t / 1e8, 1)) for d, _, t in days]}

# ── 축산 ─────────────────────────────────────────────────────
def live_index():
    days = []
    for p in sorted(glob.glob(os.path.join(DATA, 'price', 'history', '*.json'))):
        try: h = json.load(open(p, encoding='utf-8'))
        except Exception: continue
        cur = {}; heads = 0
        for s in h.get('ekape', []):
            t = s.get('title'); r = next((r for r in s['rows'] if r['g'] in ('등외제외', '평균')), None)
            # 두수가 적은 날(월요일·토요일 몇십 두)은 값이 튀어 지수에서 뺌 — 한우 200두·돼지 500두 아래
            if t in ('한우 거세', '돼지 탕박') and r and r.get('p') and (r.get('n') or 0) >= (200 if t == '한우 거세' else 500): cur[t] = (r['p'], (r.get('n') or 1) * r['p']); heads += r.get('n') or 0
        if cur: days.append((h.get('date') or os.path.basename(p)[:10], cur, heads))
    if not days: return None
    ser = chain([(d, c) for d, c, _ in days])
    parts = {}
    for t in ('한우 거세', '돼지 탕박'):
        parts[t] = [(d, c[t][0]) for d, c, _ in days if t in c]
    return {'daily': ser, 'items': 2, 'src': '축산물품질평가원 등급별 경락가(등외 제외 평균) — 두수×값 가중 고정 기하 지수(처음 5일 평균 = 100)', 'vol': [(d, hd) for d, _, hd in days], 'parts': parts}

# ── 수산 ─────────────────────────────────────────────────────
def sea_index():
    WP = jload(os.path.join(DATA, 'wipan.json'), {})
    out = {}
    # 월별(달 집계 파일)
    months = []
    for p in sorted(glob.glob(os.path.join(PRIVATE, 'wipan', '2*.json'))):
        try: m = json.load(open(p, encoding='utf-8'))
        except Exception: continue
        fish = m.get('fish') or {}
        cur = {k: (v[0] / v[1], v[0]) for k, v in fish.items() if v[1] and v[1] > 0 and v[0] > 0}
        months.append((m.get('month') or os.path.basename(p)[:7], cur, sum(v[0] for v in fish.values())))
    if months:
        out['monthly'] = chain([(d, c) for d, c, _ in months]); out['monthly_vol'] = [(d, round(t / 1e8)) for d, _, t in months]
    # 일별: 달 파일에 저장된 일별(앞으로 쌓임) + 이번 달 공개 자료
    daily_by = {}
    for p in sorted(glob.glob(os.path.join(PRIVATE, 'wipan', '2*.json'))):
        try: m = json.load(open(p, encoding='utf-8'))
        except Exception: continue
        for name, rows in (m.get('daily') or {}).items():
            for d, won, kg in rows:
                if won and kg and kg >= 1000: daily_by.setdefault(d, {})[name] = (won, won * kg)
    mo = WP.get('month') or ''
    for f in sorted(WP.get('fish', []), key=lambda f: -f.get('amt', 0))[:30]:   # 금액 상위 30어종만(꼬리 어종은 하루 몇 상자로 값이 튐)
        kgm = {d: q for d, q in f.get('daily_kg', [])}
        for d, won in f.get('daily', []):
            if won and (kgm.get(d) or 0) >= 1000: daily_by.setdefault(f'{mo[:4]}-{d}', {})[f['name']] = (won, won * kgm[d])
    if daily_by:
        days = sorted(daily_by.items())
        tots = [sum(v[1] for v in c.values()) for _, c in days]; med = sorted(tots)[len(tots) // 2] if tots else 0
        days = [(d, c) for (d, c), t in zip(days, tots) if t >= med * 0.5]
        out['daily'] = chain(days); out['vol'] = [(d, round(sum(v[1] for v in c.values()) / 1e8, 1)) for d, c in days]
        out['items'] = round(statistics.mean(len(c) for _, c in days)) if days else 0
    out['src'] = '수협 산지 위판 ㎏당 값(금액÷중량) — 어종 금액 가중 고정 기하 지수(처음 5일 평균 = 100)'
    return out or None

# ── 원가 압력 ─────────────────────────────────────────────────
def cost_index():
    M = jload(os.path.join(DATA, 'macro.json'), {}); F = jload(os.path.join(DATA, 'forecast.json'), {})
    ser = {k: dict(v['d']) for k, v in (M.get('series') or {}).items() if k in W_COST}
    if F.get('feed', {}).get('d'): ser['feed'] = dict(F['feed']['d'])
    if not ser: return None
    dates = sorted(set().union(*[set(s.keys()) for s in ser.values()]))
    last = {}; days = []
    for d in dates:
        for k, s in ser.items():
            if d in s and s[d]: last[k] = s[d]
        if len(last) >= 3: days.append((d, {k: (v, W_COST.get(k, 0.1)) for k, v in last.items()}))
    days = days[-520:]
    return {'daily': chain(days), 'src': '사료 원가 지수 0.40 · 경유 0.25 · 원/달러 0.25 · 천연가스 0.10 — 고정 가중 기하 지수(2년 전 5일 평균 = 100)', 'parts': {k: sorted(s.items())[-260:] for k, s in ser.items()}}

# ── 세계 요인 활성 점수 ────────────────────────────────────────
def world_score():
    rows = []
    for p in sorted(glob.glob(os.path.join(PRIVATE, 'world', '2*.json'))):
        try: w = json.load(open(p, encoding='utf-8'))
        except Exception: continue
        act = w.get('active') or []
        rows.append((os.path.basename(p)[:10], sum(int(a.get('level') or 0) for a in act), sum(1 for a in act if a.get('level') == 2), len(act)))
    return {'daily': [(d, s) for d, s, _, _ in rows], 'alarms': [(d, a) for d, _, a, _ in rows], 'n': [(d, n) for d, _, _, n in rows], 'src': '그날 켜진 요인의 단계 합(주의 1·경보 2)'} if rows else None

# ── 종합 ─────────────────────────────────────────────────────
def total_index(sect):
    """갈래 지수를 날짜별로 이어 붙임(없는 날은 직전 값), 가중 기하 평균 → 첫날 100"""
    series = {k: dict(v['daily']) for k, v in sect.items() if v and v.get('daily')}
    if len(series) < 2: return None
    start = max(min(s) for s in series.values()); dates = sorted(d for d in set().union(*[set(s) for s in series.values()]) if d >= start)
    last = {}; base = {}; out = []
    for d in dates:
        for k, s in series.items():
            if d in s: last[k] = s[d]
        if len(last) < len(series): continue
        if not base: base = dict(last)
        tw = sum(W_SECT[k] for k in last)
        out.append((d, round(100 * math.exp(sum(W_SECT[k] / tw * math.log(last[k] / base[k]) for k in last)), 2)))
    return {'daily': out, 'src': '축산 0.40 · 농산 0.35 · 수산 0.25 가중(가계 식료품 지출 비중 근사) — 갈래 지수의 가중 기하 평균, 세 갈래가 다 있는 첫날 = 100'}

sect = {'농산': farm_index(), '축산': live_index(), '수산': sea_index()}
tot = total_index({k: v for k, v in sect.items() if v and v.get('daily')})
cost = cost_index(); ws = world_score()
def M(v, monthly=False): return metrics(v, monthly=monthly) if v else None
out = {'at': stamp(), 'weights': W_SECT, 'cost_weights': W_COST, 'sectors': {}, 'total': None, 'cost': None, 'world': ws}
for k, v in sect.items():
    if not v: continue
    v['metrics'] = M(v.get('daily'))
    if v.get('monthly'): v['metrics_m'] = M(v['monthly'], monthly=True)
    if v.get('parts'): v['parts_metrics'] = {pk: M(pv) for pk, pv in v['parts'].items()}
    out['sectors'][k] = v
if tot: tot['metrics'] = M(tot['daily']); out['total'] = tot
if cost:
    cost['metrics'] = M(cost['daily']); cost['metrics_1y'] = M(cost['daily'][-250:])
    cost['parts_metrics'] = {k: M(v) for k, v in cost['parts'].items()}; out['cost'] = cost
jsave(os.path.join(DATA, 'pindex.json'), out)
status('pindex', True, ' · '.join(f'{k} {v["metrics"]["regime"] if v.get("metrics") else "–"}({len(v.get("daily") or [])}점)' for k, v in out['sectors'].items()) + (f' · 종합 {tot["metrics"]["regime"]}' if tot and tot.get('metrics') else '') + (f' · 원가 {cost["metrics"]["regime"]}' if cost and cost.get('metrics') else ''))
print('물가 지수', {k: (len(v.get('daily') or []), (v.get('metrics') or {}).get('regime')) for k, v in out['sectors'].items()}, '종합', len(tot['daily']) if tot else 0, '원가', len(cost['daily']) if cost else 0)
