# 원산지 거래 정보(2026-10-30) — 국내 공급이 부족해지는 품목마다 「어디서 들여올 수 있나」를 정리한다(동해안 오징어 어획 감소 → 페루·칠레·아르헨티나).
#   부족 신호: 위판 물량 감소(어족·공급 빠듯) · 예보 오름(세기 3 이상) · 갭 고평가(국산이 현지보다 유난히 비쌈) · 축산 출하 판단 오름.
#   원산지 후보: import_matrix.json(비중·전가·시차) × 오늘 원산지 상태(world.json) × 현지 시세(global.json) × 관세청 수입 단가(trade.json).
#   박씨팜은 정보와 수요 모집까지만 — 계약·결제·통관·배송은 영업등록을 가진 수입·유통업체와 수요자 사이에서. 결과 site/data/source.json, 화면 forecast_pages.source_page.
import sys, os, re, json, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
HERE = os.path.dirname(os.path.abspath(__file__))
IM = jload(os.path.join(HERE, 'import_matrix.json'), {'items': []}); OR = jload(os.path.join(HERE, 'origin_risks.json'), {'countries': []})
W = jload(os.path.join(DATA, 'world.json'), {}); GL = jload(os.path.join(DATA, 'global.json'), {}); GAP = jload(os.path.join(DATA, 'gap.json'), {})
OP = jload(os.path.join(DATA, 'opps.json'), {}); BUYS = jload(os.path.join(DATA, 'buysignal.json'), {}); CROPS = jload(os.path.join(DATA, 'cropsignal.json'), {}); FC = jload(os.path.join(DATA, 'forecast.json'), {})
TR = jload(os.path.join(DATA, 'trade.json'), {}); M = jload(os.path.join(DATA, 'macro.json'), {})
OLV = W.get('origin_level') or {}; GS = GL.get('series') or {}
usd = ((M.get('series') or {}).get('usdkrw') or {}).get('d') or []; USDKRW = usd[-1][1] if usd else None
CSTAND = {c['ko']: c.get('standing', '') for c in OR.get('countries') or []}; CROUTE = {c['ko']: c.get('route', '') for c in OR.get('countries') or []}
# 수입 품목 → 현지 시세 계열(세계 창구)
PRICE_OF = {'쇠고기': ['us_beef_choice', 'wb_beef'], '돼지고기': ['us_hog_net', 'eu_pig_s'], '닭고기': ['br_chicken', 'eu_broiler', 'wb_chicken'], '연어': ['no_salmon_fresh'], '새우': ['wb_shrimp'], '대두박': ['wb_soymeal', 'br_soy'], '옥수수': ['wb_maize', 'br_corn'], '밀': ['wb_wheat'], '어분': ['wb_fishmeal'], '요소': ['wb_urea'], '팜유': ['wb_palm']}
# 갈래별 수입 요건(요약·일반론 — 품목번호별 세부는 관세법령정보포털·수입식품정보마루에서 확인)
REQ = {'수산': '수산물 수입신고(식약처 수입식품정보마루) · 정밀검사 대상 여부 · 원산지 표시 · 일부 어종은 수입 금지·조정관세(냉동 오징어·명태 등은 품목번호별 확인)',
       '축산': '수입위생평가를 통과한 나라·작업장만 가능(검역본부 지정) · 검역 + 식약처 수입신고 · 자유무역협정 관세율은 나라·연도별 다름',
       '농산': '식물검역(수입 금지 식물·소독) + 식약처 수입신고 · 잔류농약 검사 · 계절관세·저율관세할당 품목 확인'}

def dom_name(sector, pat):
    """경쟁 품목 정규식의 첫 이름(화면용)"""
    return pat.split('|')[0]

# ── 부족 신호 모으기(국내 품목 이름 기준) ────────────────────────
sig = collections.defaultdict(list)
for x in OP.get('tight') or []: sig[('수산', x['item'])].append(('공급 빠듯', ' · '.join((x.get('why') or [])[:2]) if isinstance(x.get('why'), list) else str(x.get('why') or '')))
for x in OP.get('wild') or []:
    kt = x.get('kg_trend')
    if kt is not None and kt <= -25: sig[('수산', re.sub(r'\(.*?\)', '', x['name']).strip())].append(('어획 감소', f'앞달 대비 위판 물량 {kt:+.0f}%'))
for i in BUYS.get('items') or []:
    if '오름' in (i.get('dir') or '') and abs(i.get('score') or 0) >= 1.5: sig[('수산', i['item'])].append(('예보 오름', ' · '.join((i.get('why') or [])[:2])))
for i in CROPS.get('items') or []:
    if '오름' in (i.get('dir') or '') and abs(i.get('score') or 0) >= 1.0: sig[('농산', i['item'])].append(('예보 오름', ' · '.join((i.get('why') or [])[:2])))
for d in FC.get('decisions') or []:
    if d.get('id') in ('hanwoo', 'pig') and ('오름' in (d.get('act') or '') or '앞당' in (d.get('act') or '') or '늦추' in (d.get('act') or '')):
        sig[('축산', '한우' if d['id'] == 'hanwoo' else '돼지')].append(('출하 판단 오름 쪽', d.get('act', '')))
for p in GAP.get('pairs') or []:
    if p.get('ok') and not p.get('stale') and '고평가' in (p.get('state') or ''):
        nm = {'한우 거세': '한우', '돼지 탕박': '돼지'}.get(p['item'], p['item'])
        sig[(p['sector'], nm)].append(('갭 고평가', f'국산이 현지 환산보다 평소 대비 {p["dev"]:+}% (백분위 {p["pct"]})'))

# ── 수입 품목마다 국내 경쟁 품목과 신호 맞추기 ───────────────────
def matches(pat, sector):
    out = []
    for (s, nm), v in sig.items():
        if s != sector: continue
        try:
            if re.fullmatch('(?:' + pat + ')', nm): out.append((nm, v))
        except re.error: pass
    return out
rows = []
for it in IM.get('items') or []:
    t = it.get('competes')
    if not t: continue
    hit = matches(t['item'], t['sector'])
    signals = [(nm, k, why) for nm, v in hit for k, why in v]
    score = sum({'공급 빠듯': 2, '어획 감소': 2, '예보 오름': 1.5, '갭 고평가': 2, '출하 판단 오름 쪽': 1}.get(k, 1) for _, k, _ in signals)
    origins = []
    for ko, share in it.get('origins') or []:
        lv = OLV.get(ko, 0)
        origins.append({'ko': ko, 'share': share, 'level': lv, 'standing': CSTAND.get(ko, ''), 'route': CROUTE.get(ko, '')})
    prices = []
    for sid in PRICE_OF.get(re.sub(r'\(.*?\)', '', it['name']).strip(), []):
        g = GS.get(sid)
        if g and (datetime.date.fromisoformat(TS := now().date().isoformat()) - datetime.date.fromisoformat(g['date'][:10])).days <= 120:
            prices.append({'id': sid, 'name': g['name'], 'last': g['last'], 'unit': g['unit'], 'date': g['date'], 'w4': (g.get('chg') or {}).get('w4'), 'y1': (g.get('chg') or {}).get('y1')})
    tr = next((x for x in TR.get('items') or [] if re.sub(r'\(.*?\)', '', x['name']).strip()[:2] == re.sub(r'\(.*?\)', '', it['name']).strip()[:2]), None)
    unit_price = None
    if tr and tr.get('rows'):
        r = tr['rows'][-1]; unit_price = {'usd_kg': r.get('usd_kg'), 'krw_kg': round(r['usd_kg'] * USDKRW) if r.get('usd_kg') and USDKRW else None, 'ym': r.get('ym'), 'name': tr['name']}
    rows.append({'import': it['name'], 'group': it.get('group', ''), 'sector': t['sector'], 'dom': dom_name(t['sector'], t['item']), 'dom_pat': t['item'], 'pt': it.get('pt'), 'lag': it.get('lag', ''), 'note': it.get('note') or '', 'export': bool(it.get('export')),
                 'signals': [{'item': nm, 'kind': k, 'why': why} for nm, k, why in signals], 'score': round(score, 1), 'origins': origins, 'prices': prices, 'unit_price': unit_price, 'req': REQ.get(t['sector'], ''),
                 'open': score >= 2 and not it.get('export')})   # 신호가 2점 넘으면 수요 모집을 연다(수출 품목은 제외)
rows.sort(key=lambda r: (-r['score'], r['import']))
out = {'at': stamp(), 'date': now().date().isoformat(), 'items': rows, 'n_open': sum(1 for r in rows if r['open']), 'n_signal': sum(1 for r in rows if r['signals']), 'usdkrw': USDKRW,
       'principle': '박씨팜은 부족 신호·원산지 후보·현지 시세·요건을 정리하고 수요를 모으는 데까지만 합니다. 계약·결제·통관·배송은 영업등록을 가진 수입·유통업체와 수요자 사이에서 이뤄지며, 박씨팜은 성사 수수료를 받지 않고 거래의 당사자가 되지 않습니다.'}
jsave(os.path.join(DATA, 'source.json'), out)
status('source', True, f'수입 품목 {len(rows)} · 부족 신호 있는 품목 {out["n_signal"]} · 수요 모집 열림 {out["n_open"]}')
print('원산지 거래 정보', [(r['import'], r['score'], [s['kind'] for s in r['signals']]) for r in rows if r['signals']][:12])
