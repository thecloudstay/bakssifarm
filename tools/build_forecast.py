# 시장 예측·선매/매도 판단·조기 경보 (자가 발전 고리 포함)
#
# 거시(해외 선물·환율·운임) × 미시(경락가·위판·재고·반입량·수온)를 묶어
#   ① 사료 원가 지수(원화 기준)와 앞으로 1~3개월 배합사료 값 방향
#   ② 품목별 「선매(미리 사 두기) / 매도(팔기 서두르기) / 관망」 판단과 신뢰도
#   ③ 급변 조기 경보와 사전 대응 문구
# 를 만든다. 모든 판단은 private/forecast2/날짜.json 에 남기고, 기한이 오면 실제 값으로 채점한다.
# 채점 결과(적중률·브라이어 점수·기준선 대비)는 매주 월요일 가중치·기준을 정해진 범위 안에서 스스로 고친다(params.json).
# 기준선: 「값이 그대로」(보합) 예측. 기준선보다 못 맞히는 갈래는 화면에서 「참고」로 낮춰 보여 준다.
#
# 결과: site/data/forecast.json, private/forecast2/
import sys, os, json, math, statistics, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

FD = os.path.join(PRIVATE, 'forecast2'); os.makedirs(FD, exist_ok=True)
PP = os.path.join(FD, 'params.json')
TODAY = now().date()
DEFAULT = {
    # 배합사료 원료 비중(옥수수·대두박·소맥) — docs/예측기법_검토.md 근거로 조정
    'feed_w': {'corn': 0.55, 'soymeal': 0.25, 'wheat': 0.20},
    # 판단 갈래별 가중치(0.2~1.0) — 채점 결과로 매주 조정
    'w': {'feed': 1.0, 'hanwoo': 0.6, 'pig': 0.6, 'macro_hog': 0.3, 'macro_cattle': 0.3},
    # 경보 기준
    'alert': {'day_z_warn': 2.5, 'day_z_alarm': 3.5, 'm20_warn': 8.0, 'm20_alarm': 15.0, 'fx5_warn': 2.0, 'fx5_alarm': 3.5,
              'price_min_heads': 20, 'price_dev_warn': 7.0, 'price_dev_alarm': 12.0},
    'horizon': {'feed': 60, 'livestock': 10},     # 채점 기한(거래일)
    'calib_log': [],
}
PR = jload(PP, None) or json.loads(json.dumps(DEFAULT))
for k, v in DEFAULT.items():
    PR.setdefault(k, v)
    if isinstance(v, dict):
        for kk, vv in v.items(): PR[k].setdefault(kk, vv)

MAC = jload(os.path.join(DATA, 'macro.json'), {'series': {}}).get('series', {})
# 연결 선물(=F)은 만기 이월 날 값이 계단처럼 뛴다(예: 12월물로 넘어가며 돈육이 한 번에 -10%).
# 그날의 수익률을 0으로 보는 「이월 보정」 계열을 따로 만들어 변화율·표준점수는 보정 계열로 잰다(표시 값은 실제 마지막 값).
ROLL = collections.Counter()
def adjust(k, d):
    if k in ('usdkrw',) or len(d) < 40: return d
    r = [math.log(d[i][1] / d[i - 1][1]) for i in range(1, len(d)) if d[i - 1][1] > 0 and d[i][1] > 0]
    if len(r) != len(d) - 1: return d
    mad = statistics.median(abs(x) for x in r) or 1e-6
    out = [list(d[0])]; v = d[0][1]
    for i, x in enumerate(r, 1):
        if abs(x) > max(0.03, 7 * mad) and k not in ('oil', 'freight'):
            ROLL[k] += 1; x = 0.0
        v *= math.exp(x); out.append([d[i][0], round(v, 4)])
    # 마지막 값을 실제 값에 맞춰 비율 이동(수준은 실제, 변화율은 보정)
    f = d[-1][1] / out[-1][1] if out[-1][1] else 1
    return [[a, round(b * f, 4)] for a, b in out]
def ser(k): return [(a, b) for a, b in adjust(k, [[a, b] for a, b in (MAC.get(k) or {}).get('d', []) if b is not None])]
def pct(a, b): return round((a / b - 1) * 100, 1) if a and b else None

# ── 1. 거시 지표 요약 ─────────────────────────────────────────────
def stats(d):
    if len(d) < 30: return None
    v = [x[1] for x in d]; last = v[-1]
    rets = [math.log(v[i] / v[i - 1]) for i in range(max(1, len(v) - 61), len(v)) if v[i - 1] > 0 and v[i] > 0]
    sd = statistics.pstdev(rets[:-1]) if len(rets) > 10 else None
    dz = round(rets[-1] / sd, 2) if sd else None
    yr = v[-250:]; mu = statistics.mean(yr); s = statistics.pstdev(yr) or 1
    def ch(n): return pct(last, v[-1 - n]) if len(v) > n else None
    ma20 = statistics.mean(v[-20:]); ma60 = statistics.mean(v[-60:]) if len(v) >= 60 else None
    return {'last': last, 'date': d[-1][0], 'c1': ch(1), 'c5': ch(5), 'c20': ch(20), 'c60': ch(60), 'c250': ch(250),
            'z1y': round((last - mu) / s, 2), 'dz': dz, 'trend': '오름' if ma60 and ma20 > ma60 * 1.01 else '내림' if ma60 and ma20 < ma60 * 0.99 else '옆걸음',
            'pctl': round(sum(1 for x in yr if x <= last) / len(yr) * 100)}
tiles = []
for k, s in MAC.items():
    st = stats([list(x) for x in ser(k)])
    if st:
        st['last'] = (s.get('d') or [[0, st['last']]])[-1][1]
        tiles.append(dict(key=k, name=s['name'], unit=s['unit'], src=s.get('src', ''), stale=bool(s.get('stale')), rolls=ROLL.get(k, 0), **st))

# ── 2. 사료 원가 지수(원/㎏, 원료 가중) ──────────────────────────
#  옥수수·소맥 센트/부셸 → 달러/㎏(부셸 25.4012㎏·27.2155㎏), 대두박 달러/숏톤 → 달러/㎏(907.185㎏), × 원/달러
def ffill(d):
    return dict(d)
corn, sm, wh, fx = dict(ser('corn')), dict(ser('soymeal')), dict(ser('wheat')), dict(ser('usdkrw'))
feed = []
if corn and sm and wh and fx:
    days = sorted(set(corn) | set(sm) | set(wh))
    lc = ls = lw = lf = None
    fxd = sorted(fx)
    fi = 0
    for d in days:
        lc = corn.get(d, lc); ls = sm.get(d, ls); lw = wh.get(d, lw)
        while fi < len(fxd) and fxd[fi] <= d: lf = fx[fxd[fi]]; fi += 1
        if None in (lc, ls, lw, lf): continue
        w = PR['feed_w']
        usd = w['corn'] * lc / 100 / 25.4012 + w['soymeal'] * ls / 907.185 + w['wheat'] * lw / 100 / 27.2155
        feed.append([d, round(usd * lf, 1)])
fst = stats(feed) if feed else None

# 사료 원가 추세가 이어지는지 걸어 나가며 검증(과거 각 시점에서 그때까지 아는 값만 씀)
#  규칙: 지난 60거래일 원가 변화 ≥+3% → 「오름」, ≤-3% → 「내림」, 사이 → 「보합」. 60거래일 뒤 실제 ±3% 로 채점.
def backtest_feed(fd, H=60, th=3.0):
    v = [x[1] for x in fd]; n = hit = base = 0; brier = []
    for i in range(H, len(v) - H, 5):
        past = (v[i] / v[i - H] - 1) * 100; fut = (v[i + H] / v[i] - 1) * 100
        pred = '오름' if past >= th else '내림' if past <= -th else '보합'
        real = '오름' if fut >= th else '내림' if fut <= -th else '보합'
        n += 1; hit += pred == real; base += real == '보합'
        p_up = 0.5 + max(-0.35, min(0.35, past / 30)); brier.append((p_up - (1 if fut > 0 else 0)) ** 2)
    return {'n': n, 'hit': hit, 'rate': round(hit / n * 100) if n else None, 'base_rate': round(base / n * 100) if n else None,
            'brier': round(statistics.mean(brier), 3) if brier else None, 'rule': f'지난 {H}거래일 ±{th}% → 다음 {H}거래일 방향'}
feed_bt = backtest_feed(feed) if len(feed) > 200 else None

# ── 3. 국내 경락가(미시) ────────────────────────────────────────
HD = os.path.join(DATA, 'price', 'history')
hist = [jload(os.path.join(HD, f)) for f in sorted(os.listdir(HD))] if os.path.isdir(HD) else []
def series_ekape(title, grade='등외제외'):
    out = []
    for h in hist:
        for s in h.get('ekape', []):
            if s['title'] == title:
                for r in s['rows']:
                    if r['g'] == grade: out.append((h.get('date'), r['p'], r.get('n') or 0))
    return out
han = series_ekape('한우 거세'); pig = series_ekape('돼지 탕박', '등외제외') or series_ekape('돼지 탕박', '평균')

def dom_signal(s, min_heads):
    # 두수가 적은 날은 값이 크게 튀므로 두수 가중 평균으로 최근 3일 대 직전 5일을 비교
    ok = [x for x in s if x[2] >= 1]
    if len(ok) < 6: return None
    r3 = ok[-3:]; p5 = ok[-8:-3]
    def wavg(a): w = sum(x[2] for x in a) or 1; return sum(x[1] * x[2] for x in a) / w
    heads = sum(x[2] for x in r3)
    return {'last': ok[-1][1], 'date': ok[-1][0], 'chg': pct(wavg(r3), wavg(p5)), 'heads3': heads, 'thin': heads < min_heads, 'ndays': len(ok)}
han_s = dom_signal(han, PR['alert']['price_min_heads']); pig_s = dom_signal(pig, PR['alert']['price_min_heads'])

# ── 4. 판단 ─────────────────────────────────────────────────────
def clip(x, a, b): return max(a, min(b, x))
def conf_word(c): return '높음' if c >= 0.7 else '보통' if c >= 0.45 else '낮음'
decisions = []
if fst:
    m60 = fst['c60'] or 0; m20 = fst['c20'] or 0
    sc = clip(m60 / 5, -2, 2) * 0.6 + clip(m20 / 3, -1, 1) * 0.4
    act = '선매·가격 고정 검토' if sc >= 0.8 else '구매 늦추기·분할 구매' if sc <= -0.8 else '관망(평소대로)'
    why = [f'사료 원가 지수 3개월 {m60:+}% · 1개월 {m20:+}% (원료 선물 × 원/달러)']
    fxs = next((t for t in tiles if t['key'] == 'usdkrw'), None)
    if fxs and fxs.get('c20') is not None: why.append(f'원/달러 1개월 {fxs["c20"]:+}%')
    for k, nm in (('corn', '옥수수'), ('soymeal', '대두박'), ('wheat', '소맥')):
        t = next((t for t in tiles if t['key'] == k), None)
        if t and t.get('c60') is not None: why.append(f'{nm} 3개월 {t["c60"]:+}%')
    reli = 0.5
    if feed_bt and feed_bt['rate'] is not None:
        edge = feed_bt['rate'] - feed_bt['base_rate']
        reli = clip(0.5 + edge / 40, 0.2, 0.85)
    c = clip(abs(sc) / 2, 0, 1) * reli * PR['w']['feed'] + (1 - reli) * 0.1
    decisions.append({'id': 'feed', 'who': '농가·사료 구매', 'item': '배합사료', 'act': act, 'score': round(sc, 2), 'conf': conf_word(c), 'c': round(c, 2),
                      'horizon': '앞으로 1~3개월(국내 사료값은 원료 선물보다 몇 달 늦게 따라감)', 'why': why,
                      'expect': {'m60': m60, 'note': '원가 지수 변화가 그대로 사료값이 되지는 않습니다. 원료 비중·재고·업체 가격 정책에 따라 늦게, 덜 움직입니다.'},
                      'track': feed_bt})
def live_decision(did, item, s, macro_key, wkey, season_note):
    if not s: return None
    sc = 0.0; why = []
    if not s['thin'] and s['chg'] is not None:
        sc += clip(s['chg'] / 4, -1.5, 1.5); why.append(f'최근 3거래일 경락가 {s["chg"]:+}% (두수 {s["heads3"]})')
    elif s['chg'] is not None:
        why.append(f'최근 3거래일 두수 {s["heads3"]}두로 적어 값 변화({s["chg"]:+}%)는 판단에서 뺌')
    mt = next((t for t in tiles if t['key'] == macro_key), None)
    if mt and mt.get('c20') is not None:
        sc += clip(mt['c20'] / 8, -0.5, 0.5) * PR['w'][wkey]; why.append(f'{mt["name"]} 1개월 {mt["c20"]:+}%(세계 시세 분위기, 약한 참고)')
    if fst and fst.get('c60') is not None and fst['c60'] >= 5:
        why.append('사료 원가 오름 — 원가 부담에 출하가 몰리면 단기 값이 눌릴 수 있음')
    if season_note: why.append(season_note)
    # 값이 오를 쪽이면 출하 늦추기(더 받기), 내릴 쪽이면 출하 서두르기(매도)
    act = '출하 늦추기 검토(값 오름 쪽)' if sc >= 0.8 else '출하 서두르기·매도 검토(값 내림 쪽)' if sc <= -0.8 else '관망(평소 출하)'
    c = clip(abs(sc) / 2, 0, 1) * PR['w'][did] * (0.6 if s['ndays'] < 20 else 1.0)
    return {'id': did, 'who': '농가·출하', 'item': item, 'act': act, 'score': round(sc, 2), 'conf': conf_word(c), 'c': round(c, 2),
            'horizon': '앞으로 2주', 'why': why, 'last': s['last'], 'date': s['date'], 'ndays': s['ndays']}
mo = TODAY.month
pig_season = '계절: 돼지값은 대체로 봄~초여름에 강하고 가을~겨울에 약해지는 경향(근거 docs/예측기법_검토.md)' if mo in (9, 10, 11, 12) else ''
for d in (live_decision('hanwoo', '한우 거세 출하', han_s, 'cattle', 'macro_cattle', ''),
          live_decision('pig', '돼지 출하', pig_s, 'hog', 'macro_hog', pig_season)):
    if d: decisions.append(d)

# 수산·농산 기존 신호를 같은 판에 묶어 보여 줌(채점은 각 신호가 따로 함)
BUY = jload(os.path.join(DATA, 'buysignal.json'), {}); CROP = jload(os.path.join(DATA, 'cropsignal.json'), {})
def top_sig(js, kind, key='item'):
    out = []
    for i in (js.get('items') or []):
        if i.get('dir') in ('오름 쪽', '내림 쪽') and abs(i.get('score') or 0) >= 1:
            out.append({'kind': kind, 'item': i[key], 'dir': i['dir'], 'act': i.get('act', ''), 'why': (i.get('why') or [])[:3], 'score': i.get('score')})
    return sorted(out, key=lambda x: -abs(x['score']))[:6]
micro = top_sig(BUY, '수산') + top_sig(CROP, '농산')
def rate_of(js):
    sc = js.get('score') or {}; n = sc.get('n') or 0
    return {'n': n, 'hit': sc.get('hit') or 0, 'rate': round((sc.get('hit') or 0) / n * 100) if n else None}

# ── 5. 조기 경보 ────────────────────────────────────────────────
A = PR['alert']; alerts = []
REACT = {
    'corn': '배합사료 인상 가능성 — 사료 업체에 다음 달 단가 확인, 여유 자금이 있으면 1~2개월분 선매·고정 검토',
    'soymeal': '단백질 원료 원가 상승 — 사료 단가 변동 공지 확인, 양돈·양계는 원가 영향이 큼',
    'wheat': '소맥 원가 변동 — 사료 원가와 밀가루 쓰는 가공 업체 원가 확인',
    'usdkrw': '환율 급변 — 수입 원료(옥수수·대두박·어분)와 수입 고기 원화 값이 함께 움직임. 수입 원료는 결제 시점 분산',
    'oil': '유가 급변 — 운송·난방(하우스·축사·어선) 원가 점검',
    'hog': '세계 돼지 시세 급변 — 수입 돼지고기 값과 국내 시세 영향 점검',
    'cattle': '세계 소 시세 급변 — 수입 소고기 값 영향 점검',
    'feeder': '세계 송아지(비육우) 시세 급변 — 수입 소고기 공급 전망 점검',
    'freight': '해상운임 급변 — 수입 곡물·사료 도착 원가에 1~2개월 뒤 반영',
    'soy': '대두 원가 변동 — 대두박·식용유 원가 확인',
}
for t in tiles:
    lv = None; why = []
    if t.get('dz') is not None and abs(t['dz']) >= A['day_z_warn']:
        lv = '경보' if abs(t['dz']) >= A['day_z_alarm'] else '주의'; why.append(f'하루 변동이 평소의 {abs(t["dz"]):.1f}배(표준점수)')
    if t.get('c20') is not None and abs(t['c20']) >= A['m20_warn'] and t['key'] != 'usdkrw':
        lv2 = '경보' if abs(t['c20']) >= A['m20_alarm'] else '주의'; lv = '경보' if '경보' in (lv, lv2) else lv2; why.append(f'1개월 {t["c20"]:+}%')
    if t['key'] == 'usdkrw' and t.get('c5') is not None and abs(t['c5']) >= A['fx5_warn']:
        lv2 = '경보' if abs(t['c5']) >= A['fx5_alarm'] else '주의'; lv = '경보' if '경보' in (lv, lv2) else lv2; why.append(f'1주 {t["c5"]:+}%')
    if lv:
        alerts.append({'level': lv, 'kind': '해외 시세', 'title': f'{t["name"]} {t["last"]:,} ({"·".join(why)})', 'react': REACT.get(t['key'], ''), 'date': t['date'], 'src': t['src']})
if fst and fst.get('c20') is not None and abs(fst['c20']) >= 6:
    alerts.append({'level': '경보' if abs(fst['c20']) >= 10 else '주의', 'kind': '사료 원가', 'title': f'사료 원가 지수 1개월 {fst["c20"]:+}%',
                   'react': '오르는 쪽이면 다음 사료 주문 전 단가 확인·선매 검토, 내리는 쪽이면 장기 고정 계약 미루기', 'date': fst['date'], 'src': '시카고 선물 × 원/달러(박씨팜 계산)'})
for nm, s in (('한우 거세', han_s), ('돼지 탕박', pig_s)):
    if s and not s['thin'] and s['chg'] is not None and abs(s['chg']) >= A['price_dev_warn']:
        alerts.append({'level': '경보' if abs(s['chg']) >= A['price_dev_alarm'] else '주의', 'kind': '국내 경락가', 'title': f'{nm} 경락가 {s["chg"]:+}% (최근 3거래일 두수 {s["heads3"]})',
                       'react': '출하 예정 농가는 등급별 경락가와 출하 두수 추이 확인, 급락이면 출하 시기 분산', 'date': s['date'], 'src': '축산물품질평가원 등급별 경락가'})
RISK = jload(os.path.join(DATA, 'risk.json'), {})
nrisk = sum(1 for u, v in (RISK.get('sea') or {}).items() for r in v.get('risks', []) if r.get('lv') == '위험')
if nrisk:
    alerts.append({'level': '주의', 'kind': '수온', 'title': f'양식 폐사 위험 해역 {nrisk}곳(7일 예보)', 'react': '해당 품목 산지 공급이 줄 수 있음 — 유통 업체는 대체 산지·재고 확보 검토', 'date': TODAY.isoformat(), 'src': '오픈메테오 수온 예보 × 어장정보도'})
order = {'경보': 0, '주의': 1}
alerts.sort(key=lambda a: order.get(a['level'], 9))

# ── 6. 기록과 채점(걸어 나가며) ─────────────────────────────────
LOG = os.path.join(FD, TODAY.isoformat() + '.json')
if not os.path.exists(LOG):
    jsave(LOG, {'made': stamp(), 'items': [{'id': d['id'], 'score': d['score'], 'act': d['act'], 'base': (fst['last'] if d['id'] == 'feed' and fst else d.get('last')),
                                             'base_date': (fst['date'] if d['id'] == 'feed' and fst else d.get('date'))} for d in decisions]})
def actual(did, after_date, n_days):
    if did == 'feed':
        seq = [x for x in feed if x[0] > after_date]
        return seq[n_days - 1][1] if len(seq) >= n_days else None
    s = han if did == 'hanwoo' else pig if did == 'pig' else []
    seq = [x for x in s if x[0] and x[0] > after_date and x[2] >= 1]
    return seq[n_days - 1][1] if len(seq) >= n_days else None
SC = os.path.join(FD, 'score.json'); score = jload(SC, {'rows': []}); done = {(r['made'], r['id']) for r in score['rows']}
for f in sorted(os.listdir(FD)):
    if not f[:4].isdigit() or not f.endswith('.json'): continue
    lg = jload(os.path.join(FD, f), {})
    for it in lg.get('items', []):
        if (f[:10], it['id']) in done or not it.get('base') or not it.get('base_date'): continue
        H = PR['horizon']['feed' if it['id'] == 'feed' else 'livestock']
        a = actual(it['id'], it['base_date'], H)
        if a is None: continue
        chg = (a / it['base'] - 1) * 100; th = 3.0 if it['id'] == 'feed' else 2.0
        real = 1 if chg >= th else -1 if chg <= -th else 0
        pred = 1 if it['score'] >= 0.8 else -1 if it['score'] <= -0.8 else 0
        p_up = 1 / (1 + math.exp(-it['score'] * 1.2))
        score['rows'].append({'made': f[:10], 'id': it['id'], 'pred': pred, 'real': real, 'chg': round(chg, 1), 'hit': pred == real, 'base_hit': real == 0,
                              'brier': round((p_up - (1 if chg > 0 else 0)) ** 2, 3)})
jsave(SC, score)
track = {}
for did in ('feed', 'hanwoo', 'pig'):
    rs = [r for r in score['rows'] if r['id'] == did][-120:]
    if rs:
        track[did] = {'n': len(rs), 'rate': round(sum(r['hit'] for r in rs) / len(rs) * 100), 'base_rate': round(sum(r['base_hit'] for r in rs) / len(rs) * 100),
                      'brier': round(statistics.mean(r['brier'] for r in rs), 3)}

# ── 7. 자가 조정(매주 월요일, 정해진 범위 안에서만) ─────────────
if TODAY.weekday() == 0 and PR.get('last_calib') != TODAY.isoformat():
    changes = []
    for did, t in track.items():
        if t['n'] < 20: continue
        edge = t['rate'] - t['base_rate']; w0 = PR['w'].get(did, 0.6)
        w1 = round(clip(w0 * (0.8 if edge < -5 else 1.1 if edge > 5 else 1.0), 0.2, 1.0), 2)
        if w1 != w0: PR['w'][did] = w1; changes.append(f'{did} 가중치 {w0}→{w1}(적중 {t["rate"]}% vs 기준선 {t["base_rate"]}%, {t["n"]}건)')
    PR['last_calib'] = TODAY.isoformat()
    if changes: PR['calib_log'] = (PR.get('calib_log') or [])[-50:] + [{'date': TODAY.isoformat(), 'changes': changes}]
    jsave(PP, PR, indent=1)
elif not os.path.exists(PP):
    jsave(PP, PR, indent=1)

# 화면에 「참고」로 낮출 갈래: 채점 20건 이상인데 기준선보다 못한 것
for d in decisions:
    t = track.get(d['id']) if d['id'] != 'feed' else (track.get('feed') or (feed_bt and {'n': feed_bt['n'], 'rate': feed_bt['rate'], 'base_rate': feed_bt['base_rate']}))
    d['live_track'] = track.get(d['id'])
    if t and t.get('n', 0) >= 20 and t['rate'] is not None and t['rate'] < t['base_rate']:
        d['weak'] = True; d['conf'] = '낮음'

out = {'at': stamp(), 'tiles': tiles, 'feed': {'d': feed[-520:], 'stats': fst, 'w': PR['feed_w'], 'backtest': feed_bt},
       'decisions': decisions, 'micro': micro, 'micro_track': {'수산': rate_of(BUY), '농산': rate_of(CROP)},
       'alerts': alerts, 'track': track, 'params': {'w': PR['w'], 'alert': PR['alert'], 'calib': (PR.get('calib_log') or [])[-5:]},
       'basis': '해외 선물·환율(야후 금융·스투크·미국 연준) × 축산물품질평가원 경락가 × 수협 위판·재고 × 공영도매시장 정산 × 수온 예보'}
jsave(os.path.join(DATA, 'forecast.json'), out)
status('forecast', bool(tiles), f'지표 {len(tiles)} · 판단 {len(decisions)} · 경보 {len(alerts)}(경보 {sum(a["level"] == "경보" for a in alerts)}) · 채점 {len(score["rows"])}건'
       + (f' · 사료 원가 검증 {feed_bt["rate"]}%(기준선 {feed_bt["base_rate"]}%)' if feed_bt else ''))
print('예측', len(tiles), '지표', len(decisions), '판단', len(alerts), '경보', feed_bt)
