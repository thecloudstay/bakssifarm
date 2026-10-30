# 박씨팜 갭 기회(2026-10-30) — 해외 원산지 값(환율 환산)과 국산 값의 비율이 평소 범위를 벗어났을 때(갭)를 재고, 되돌림을 기록·채점한다.
#   비율 = 국산 원/㎏ ÷ (현지 값 × 환율 → 원/㎏). 같은 물건의 두 가격은 운임·관세·품질 차이만큼 떨어져 있되 그 차이는 보통 좁은 띠 안에 머문다(일물일가·수입 평가 괴리).
#   띠를 벗어나면 ① 국산이 상대적으로 비쌈(백분위 ≥ 85): 수입 대체 유리·국산 출하 서두르기 ② 국산이 상대적으로 쌈(≤ 15): 국산 매입·수입 미루기. 관세·운임 계수를 억지로 정하지 않고 비율의 「자기 역사」로 판정한다.
#   자료: 국산 — 축평원 경락가(history), 수협 위판(wipan 달 파일 일별), 도매시장 정산(private/wholesale); 현지 — global.json(세계 창구); 환율 — macro usdkrw + 미 연준 일별(유로·크로네·헤알·호주달러, 캐시 private/gap/fx.json).
#   결과 site/data/gap.json, 기록 private/gap/<날짜>.json, 채점 private/gap/score.json. 화면은 forecast_pages.gap_page.
import sys, os, re, io, csv, json, glob, math, statistics, datetime, collections, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from trend_lib import metrics
HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = now().date(); TS = TODAY.isoformat()
G = jload(os.path.join(DATA, 'global.json'), {}) or {}; GS = G.get('series') or {}
M = jload(os.path.join(DATA, 'macro.json'), {}) or {}
GAP_DIR = os.path.join(PRIVATE, 'gap'); os.makedirs(GAP_DIR, exist_ok=True)
LB = 0.45359237   # 1파운드 = 0.4536㎏ → 달러/100파운드 ÷ 45.359 = 달러/㎏

# ── 환율(원/달러는 거시 자료, 나머지는 미 연준 일별 → 원 환산) ─────────
FXC_P = os.path.join(GAP_DIR, 'fx.json'); FXC = jload(FXC_P, {}); FX_ERR = []
def fred_daily(sid):
    try:
        b = get('https://fred.stlouisfed.org/graph/fredgraph.csv', {'id': sid, 'cosd': (TODAY - datetime.timedelta(days=420)).isoformat()}, timeout=75, retry=2, headers={'User-Agent': 'Mozilla/5.0 (compatible; bakssifarm-gap/1.0)'}).decode('utf-8', 'replace')   # 1999년부터 다 받으면 시간 초과 — 최근 14개월만
        out = {}
        for row in csv.reader(io.StringIO(b)):
            if len(row) < 2 or not row[0][:2].isdigit(): continue
            try: out[row[0]] = float(row[1])
            except ValueError: pass
        if out: FXC[sid] = out
        return out
    except Exception as e:
        FX_ERR.append(f'{sid} {type(e).__name__} {str(e)[:80]}')
        if env('GAP_FX_SEED') and sid not in FXC:   # 사무실 컴퓨터 시험용 씨앗(실행기에서는 쓰이지 않음)
            seed = {'DEXUSEU': 1.08, 'DEXNOUS': 10.9, 'DEXBZUS': 5.3, 'DEXUSAL': 0.66}
            return {'2020-01-01': seed[sid]} if sid in seed else {}
        return FXC.get(sid) or {}
USDKRW = {d: v for d, v in (M.get('series', {}).get('usdkrw', {}).get('d') or [])}
EUR = fred_daily('DEXUSEU'); NOK = fred_daily('DEXNOUS'); BRL = fred_daily('DEXBZUS'); AUD = fred_daily('DEXUSAL')
jsave(FXC_P, FXC)
def ffill(series, dates):
    """series {날짜: 값} 을 dates 각 날짜의 「그날 또는 직전」 값으로"""
    ks = sorted(series); out = {}; j = 0; last = None
    for d in sorted(dates):
        while j < len(ks) and ks[j] <= d: last = series[ks[j]]; j += 1
        out[d] = last
    return out
def krw_per(unit_ccy, dates):
    """통화 1단위당 원 — dates 날짜별"""
    uk = ffill(USDKRW, dates)
    if unit_ccy == 'USD': return uk
    if unit_ccy == 'EUR': e = ffill(EUR, dates); return {d: (uk[d] * e[d]) if uk.get(d) and e.get(d) else None for d in dates}
    if unit_ccy == 'NOK': n = ffill(NOK, dates); return {d: (uk[d] / n[d]) if uk.get(d) and n.get(d) else None for d in dates}
    if unit_ccy == 'BRL': b = ffill(BRL, dates); return {d: (uk[d] / b[d]) if uk.get(d) and b.get(d) else None for d in dates}
    if unit_ccy == 'AUD': a = ffill(AUD, dates); return {d: (uk[d] * a[d]) if uk.get(d) and a.get(d) else None for d in dates}
    return {d: None for d in dates}

# ── 국산 계열 ────────────────────────────────────────────────
def hanwoo_series():
    """한우 거세 육질등급(1++~3) 두수 가중 평균 원/㎏(등외·D 제외)"""
    out = {}
    for p in sorted(glob.glob(os.path.join(DATA, 'price', 'history', '*.json'))):
        try: h = json.load(open(p, encoding='utf-8'))
        except Exception: continue
        for s in h.get('ekape', []):
            if s.get('title') != '한우 거세': continue
            rows = [r for r in s['rows'] if r.get('p') and r.get('n') and str(r['g'])[:1] in '123']
            n = sum(r['n'] for r in rows)
            if n >= 150: out[h.get('date') or os.path.basename(p)[:10]] = sum(r['p'] * r['n'] for r in rows) / n
    return out
def pig_series():
    out = {}
    for p in sorted(glob.glob(os.path.join(DATA, 'price', 'history', '*.json'))):
        try: h = json.load(open(p, encoding='utf-8'))
        except Exception: continue
        for s in h.get('ekape', []):
            if s.get('title') != '돼지 탕박': continue
            r = next((r for r in s['rows'] if r['g'] in ('등외제외', '평균')), None)
            if r and r.get('p') and (r.get('n') or 0) >= 300: out[h.get('date') or os.path.basename(p)[:10]] = r['p']
    return out
def wipan_series(name_pat):
    """수협 위판 어종(이름 정규식) 일별 ㎏당 값(달 파일의 daily, 1톤 이상 거래일)"""
    out = {}
    for p in sorted(glob.glob(os.path.join(PRIVATE, 'wipan', '2*.json'))):
        try: m = json.load(open(p, encoding='utf-8'))
        except Exception: continue
        for nm, rows in (m.get('daily') or {}).items():
            if not re.search(name_pat, nm): continue
            for d, won, kg in rows:
                if won and kg and kg >= 1000: out.setdefault(d, []).append((won, kg))
    return {d: sum(w * k for w, k in v) / sum(k for _, k in v) for d, v in out.items()}
def wholesale_series(item):
    out = {}
    for p in sorted(glob.glob(os.path.join(PRIVATE, 'wholesale', '*.json'))):
        try: d = json.load(open(p, encoding='utf-8'))
        except Exception: continue
        v = d.get(item)
        if v and v[0] and v[1] and v[1] >= 1000: out[os.path.basename(p)[:10]] = v[0]
    return out
def gl(sid):
    s = GS.get(sid)
    return ({d: v for d, v in s['points']} if s else {}), s

# ── 짝 정의 ─────────────────────────────────────────────────
#   (id, 이름, 국산 계열 함수, 국산 설명, 현지 계열 id, 현지 단위→원/㎏ 변환(통화, 나누는 수), 현지 설명, 영향 품목(예보 쪽), 메모)
PAIRS = [
 {'id': 'hanwoo_usbeef', 'name': '한우 거세 ↔ 미국 쇠고기(초이스 박스육)', 'sector': '축산', 'item': '한우 거세', 'dom': hanwoo_series, 'dom_desc': '한우 거세 1++~3등급 두수 가중 경락가(지육 원/㎏)',
  'origin': 'us_beef_choice', 'ccy': 'USD', 'div': 100 * LB, 'org_desc': '미국 농무부 초이스 박스육 도매값(달러/100파운드 → 원/㎏)', 'note': '한우와 미국산은 품질·등급이 다른 물건이라 비율의 절댓값이 아니라 「평소 범위를 벗어났나」만 봅니다. 수입 쇠고기의 절반이 미국산.'},
 {'id': 'hanwoo_wbbeef', 'name': '한우 거세 ↔ 세계 쇠고기(호주 수출, 세계은행)', 'sector': '축산', 'item': '한우 거세', 'dom': hanwoo_series, 'dom_desc': '한우 거세 두수 가중 경락가(원/㎏)',
  'origin': 'wb_beef', 'ccy': 'USD', 'div': 1, 'org_desc': '세계은행 쇠고기(호주 수출, 달러/㎏ → 원/㎏, 월별)', 'note': '수입 쇠고기의 42%가 호주산. 월별 값이라 느리게 움직입니다.'},
 {'id': 'pig_ushog', 'name': '돼지 탕박 ↔ 미국 생돈', 'sector': '축산', 'item': '돼지 탕박', 'dom': pig_series, 'dom_desc': '돼지 탕박 등외 제외 경락가(원/㎏)',
  'origin': 'us_hog_net', 'ccy': 'USD', 'div': 100 * LB, 'org_desc': '미국 농무부 생돈 순가격(달러/100파운드 지육 기준 → 원/㎏)', 'note': '수입 돼지고기의 30%가 미국산(삼겹·목살·앞다리).'},
 {'id': 'pig_eupig', 'name': '돼지 탕박 ↔ 유럽연합 돼지고기(S등급)', 'sector': '축산', 'item': '돼지 탕박', 'dom': pig_series, 'dom_desc': '돼지 탕박 등외 제외 경락가(원/㎏)',
  'origin': 'eu_pig_s', 'ccy': 'EUR', 'div': 100, 'org_desc': '유럽연합 집행위 돼지고기 S등급 도축장 값(유로/100㎏ → 원/㎏, 주간)', 'note': '스페인·네덜란드·독일·덴마크 합쳐 수입 돼지고기의 3분의 1.'},
 {'id': 'flatfish_salmon', 'name': '넙치(활어) ↔ 노르웨이 연어', 'sector': '수산', 'item': '넙치', 'dom': lambda: wipan_series(r'^넙치\(활어\)'), 'dom_desc': '수협 산지 위판 넙치(활어) ㎏당 값',
  'origin': 'no_salmon_fresh', 'ccy': 'NOK', 'div': 1, 'org_desc': '노르웨이 통계청 신선 연어 수출가(크로네/㎏ → 원/㎏, 주간)', 'note': '횟감 자리를 두고 겨루는 두 어종. 연어가 상대적으로 싸지면 넙치 수요가 밀립니다.'},
 {'id': 'yellowtail_salmon', 'name': '방어(활어) ↔ 노르웨이 연어', 'sector': '수산', 'item': '방어', 'dom': lambda: wipan_series(r'^방어\(활어\)'), 'dom_desc': '수협 산지 위판 방어(활어) ㎏당 값',
  'origin': 'no_salmon_fresh', 'ccy': 'NOK', 'div': 1, 'org_desc': '노르웨이 신선 연어 수출가(원/㎏ 환산)', 'note': '겨울 방어 철에는 연어 대신 방어로 수요가 옮겨 갑니다.'},
 {'id': 'seabream_salmon', 'name': '참돔(활어) ↔ 노르웨이 연어', 'sector': '수산', 'item': '참돔', 'dom': lambda: wipan_series(r'^참돔\(활어\)'), 'dom_desc': '수협 산지 위판 참돔(활어) ㎏당 값',
  'origin': 'no_salmon_fresh', 'ccy': 'NOK', 'div': 1, 'org_desc': '노르웨이 신선 연어 수출가(원/㎏ 환산)', 'note': ''},
 {'id': 'banana_fx', 'kind': 'fx', 'name': '바나나(도매) ↔ 원/달러', 'sector': '농산', 'item': '바나나', 'dom': lambda: wholesale_series('바나나'), 'dom_desc': '공영도매시장 바나나 정산 ㎏당 값',
  'origin': None, 'ccy': 'USD', 'div': 1, 'org_desc': '원/달러 환율(수입 바나나는 달러 결제 — 환율이 곧 수입 원가)', 'note': '필리핀산 70%. 현지 값 창구가 없어 환율만으로 봅니다(환율 갭).'},
 {'id': 'orange_fx', 'kind': 'fx', 'name': '오렌지(도매) ↔ 원/달러', 'sector': '농산', 'item': '오렌지', 'dom': lambda: wholesale_series('오렌지'), 'dom_desc': '공영도매시장 오렌지 정산 ㎏당 값',
  'origin': None, 'ccy': 'USD', 'div': 1, 'org_desc': '원/달러 환율', 'note': '미국산 위주. 환율 갭.'},
]

def build_pair(P):
    dom = P['dom']()
    if len(dom) < 5: return {'id': P['id'], 'name': P['name'], 'sector': P['sector'], 'item': P['item'], 'ok': False, 'why': f'국산 자료 {len(dom)}일 — 5일 넘게 쌓이면 계산'}
    dates = sorted(dom)
    if P['origin']:
        og, meta = gl(P['origin'])
        if not og: return {'id': P['id'], 'name': P['name'], 'sector': P['sector'], 'item': P['item'], 'ok': False, 'why': '현지 계열 없음 ' + P['origin']}
        ogf = ffill(og, dates)
    else: ogf = {d: 1.0 for d in dates}; meta = {'name': '원/달러', 'unit': '원', 'freq': '일', 'date': max(USDKRW) if USDKRW else ''}
    fx = krw_per(P['ccy'], dates)
    rows = []
    for d in dates:
        if not ogf.get(d) or not fx.get(d) or not dom.get(d): continue
        o_krw = ogf[d] / P['div'] * fx[d]   # 현지 값 → 원/㎏(환율 갭 짝은 환율 자체)
        rows.append((d, dom[d], o_krw, dom[d] / o_krw))
    if len(rows) < 5: return {'id': P['id'], 'name': P['name'], 'sector': P['sector'], 'item': P['item'], 'ok': False, 'why': f'환율·현지 값과 겹치는 날 {len(rows)}일'}
    cut = (TODAY - datetime.timedelta(days=365)).isoformat()
    base = [r[3] for r in rows if r[0] >= cut]
    cur = rows[-1]; ratios = sorted(base)
    pct = round(sum(1 for x in ratios if x <= cur[3]) / len(ratios) * 100)
    med = statistics.median(ratios); sd = statistics.pstdev(ratios) if len(ratios) > 2 else 0
    z = round((cur[3] - med) / sd, 2) if sd else 0.0
    dev = round((cur[3] / med - 1) * 100, 1)   # 평소(중앙값) 대비 %
    hi, lo = ('국산 상대 고평가', '국산 상대 저평가') if P.get('kind') != 'fx' else ('도매가 수입 원가 대비 높음', '도매가 수입 원가 대비 낮음')
    state = hi if (pct >= 85 and dev >= 5) else lo if (pct <= 15 and dev <= -5) else '평소 범위'
    strong = abs(z) >= 1.5 and len(base) >= 60
    # 4주 변화 분해: ln(비율) = ln(국산) − ln(현지) − ln(환율)
    def at(k):
        d0 = (datetime.date.fromisoformat(cur[0]) - datetime.timedelta(days=k)).isoformat()
        prev = [r for r in rows if r[0] <= d0]
        return prev[-1] if prev else None
    p4 = at(28)
    decomp = None
    if p4:
        d_dom = (cur[1] / p4[1] - 1) * 100; d_org = (cur[2] / p4[2] - 1) * 100
        fx0 = fx.get(p4[0]); fx1 = fx.get(cur[0]); d_fx = ((fx1 / fx0 - 1) * 100) if fx0 and fx1 else None
        d_orgloc = ((ogf[cur[0]] / ogf[p4[0]] - 1) * 100) if ogf.get(p4[0]) and P['origin'] else None
        decomp = {'ratio': round((cur[3] / p4[3] - 1) * 100, 1), 'dom': round(d_dom, 1), 'org_krw': round(d_org, 1), 'org_local': (round(d_orgloc, 1) if d_orgloc is not None else None), 'fx': (round(d_fx, 1) if d_fx is not None else None), 'from': p4[0]}
    m = metrics([(r[0], r[3]) for r in rows])
    # 참고 행동(거래 권유 아님)
    if P.get('kind') == 'fx':
        if state == hi: acts = {'수입·유통': '도매가가 수입 원가(환율)보다 많이 올라 있음 — 수입 물량 늘릴 유인, 다만 갭은 되돌아옴', '급식·가공': '값이 비싼 구간 — 매입을 나누거나 미루기', '국산 생산자': '대체 과일(국산)에 수요가 옮겨 올 수 있는 구간'}
        elif state == lo: acts = {'수입·유통': '도매가가 수입 원가 대비 낮음(마진 압박) — 신규 수입 줄이기, 재고 소진', '급식·가공': '싸게 살 구간', '국산 생산자': '수입 과일이 싸져 국산 과일 수요가 눌릴 수 있음'}
        else: acts = {'수입·유통': '평소 범위', '급식·가공': '평소대로', '국산 생산자': '평소대로'}
    elif state == hi:
        acts = {'수입·유통': '수입 비중을 늘리거나 장기 계약을 당겨 잡을 때 — 갭은 평균으로 되돌아오는 경향', '급식·가공': '같은 용도면 수입으로 바꾸기 유리한 구간', '국산 생산자': '상대 가격이 유리할 때 출하를 서두르는 쪽 — 갭이 닫히면 국산 값이 눌림'}
    elif state == lo:
        acts = {'수입·유통': '수입을 미루고 국산 매입을 늘릴 구간 — 수입 단가가 상대적으로 비쌈', '급식·가공': '국산으로 바꾸거나 국산 비중을 올릴 때', '국산 생산자': '출하를 늦출 여지(갭이 닫히면 국산 값이 받쳐짐)'}
    else: acts = {'수입·유통': '평소 범위 — 통상 비율대로', '급식·가공': '평소대로', '국산 생산자': '평소대로'}
    stale = (TODAY - datetime.date.fromisoformat(cur[0])).days > 10   # 국산 쪽 자료가 열흘 넘게 묵으면(위판 달 파일 대기) 오늘의 갭으로 세지 않음
    return {'id': P['id'], 'kind': P.get('kind', 'origin'), 'name': P['name'], 'sector': P['sector'], 'item': P['item'], 'ok': True, 'date': cur[0], 'stale': stale, 'dom': round(cur[1]), 'org_krw': round(cur[2]), 'org_local': round(ogf[cur[0]], 2) if P['origin'] else None,
            'org_unit': (meta or {}).get('unit', ''), 'org_date': (meta or {}).get('date', ''), 'fx': round(fx[cur[0]], 2), 'ccy': P['ccy'], 'ratio': round(cur[3], 3), 'median': round(med, 3), 'pct': pct, 'z': z, 'dev': dev,
            'state': state, 'strong': strong, 'n_base': len(base), 'base_from': rows[0][0] if rows[0][0] >= cut else cut, 'decomp': decomp, 'acts': acts, 'dom_desc': P['dom_desc'], 'org_desc': P['org_desc'], 'note': P['note'],
            'series': [[r[0], round(r[3], 3)] for r in rows[-130:]], 'dom_series': [[r[0], round(r[1])] for r in rows[-130:]], 'org_series': [[r[0], round(r[2])] for r in rows[-130:]], 'band': [round(med - 2 * sd, 3), round(med + 2 * sd, 3)], 'metrics': m}

pairs = [build_pair(P) for P in PAIRS]
ok = [p for p in pairs if p.get('ok')]
# 기록·채점: 갭(|z|≥1 이고 평소 범위 밖)이던 날의 4주 뒤 |z| 가 줄었나(되돌림)
snap = {'date': TS, 'pairs': {p['id']: {'ratio': p['ratio'], 'z': p['z'], 'pct': p['pct'], 'state': p['state'], 'median': p['median']} for p in ok}}
jsave(os.path.join(GAP_DIR, TS + '.json'), snap)
SC = []; HOR = 28
by_id = {p['id']: p for p in ok}
for f in sorted(glob.glob(os.path.join(GAP_DIR, '2*.json'))):
    d0 = os.path.basename(f)[:10]
    if (TODAY - datetime.date.fromisoformat(d0)).days < HOR: continue
    try: s0 = json.load(open(f, encoding='utf-8'))
    except Exception: continue
    due = (datetime.date.fromisoformat(d0) + datetime.timedelta(days=HOR)).isoformat()
    for pid, v in (s0.get('pairs') or {}).items():
        if v.get('state') == '평소 범위' or pid not in by_id: continue
        p = by_id[pid]; after = next(((d, r) for d, r in p['series'] if d >= due), None)
        if not after: continue
        z_after = (after[1] - v['median']) / ((p['band'][1] - p['band'][0]) / 4) if p['band'][1] > p['band'][0] else 0
        SC.append({'d': d0, 'pair': pid, 'state': v['state'], 'z0': v['z'], 'z1': round(z_after, 2), 'closed': abs(z_after) < abs(v['z']) * 0.5, 'to': after[0]})
score = {'n': len(SC), 'closed': sum(1 for x in SC if x['closed']), 'rate': round(sum(1 for x in SC if x['closed']) / len(SC) * 100) if SC else None, 'rows': SC[-40:], 'n_days': len(glob.glob(os.path.join(GAP_DIR, '2*.json')))}
jsave(os.path.join(GAP_DIR, 'score.json'), score)
out = {'at': stamp(), 'date': TS, 'pairs': pairs, 'n_ok': len(ok), 'n_gap': sum(1 for p in ok if p['state'] != '평소 범위'), 'score': score,
       'fx_err': FX_ERR, 'fx': {'usdkrw': USDKRW.get(max(USDKRW)) if USDKRW else None, 'eur_usd': EUR.get(max(EUR)) if EUR else None, 'nok_usd': NOK.get(max(NOK)) if NOK else None, 'brl_usd': BRL.get(max(BRL)) if BRL else None},
       'method': '비율 = 국산 원/㎏ ÷ (현지 값 × 환율). 최근 1년 비율의 백분위 ≥85 이고 중앙값보다 5% 넘게 높으면 「국산 상대 고평가」, ≤15 이고 5% 넘게 낮으면 「국산 상대 저평가」. 기록 60일 넘고 |z|≥1.5 면 강한 갭. 4주 뒤 |z| 가 절반 아래로 줄면 「되돌림」으로 채점.'}
jsave(os.path.join(DATA, 'gap.json'), out)
os.makedirs(os.path.join(HERE, '_debug'), exist_ok=True); jsave(os.path.join(HERE, '_debug', 'gap_debug.json'), {'at': out['at'], 'fx_err': FX_ERR, 'fx': out['fx'], 'pairs': [(p['id'], p.get('state') or p.get('why'), p.get('n_base')) for p in pairs]})
status('gap', len(ok) >= 2, f'짝 {len(ok)}/{len(pairs)} 계산 · 갭 {out["n_gap"]} · 되돌림 채점 {score["n"]}건' + (f'({score["rate"]}%)' if score['rate'] is not None else ''))
print('갭 기회', [(p['id'], p.get('state'), p.get('pct'), p.get('n_base')) if p.get('ok') else (p['id'], p.get('why')) for p in pairs])
