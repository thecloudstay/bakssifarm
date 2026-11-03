# 세계 요인을 구매 신호·판단 점수에 더하는 공통 함수 — collect_world.py 가 만든 site/data/world.json 을 읽는다.
#   world_adjust('수산', '꽃게') → (더할 점수, 근거 문장들, 맞은 요인 id들). 갈래별 상한(caps)으로 자른다.
import os, re, json
_W = None
def _load():
    global _W
    if _W is None:
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'site', 'data', 'world.json')
        try: _W = json.load(open(p, encoding='utf-8'))
        except Exception: _W = {'events': [], 'caps': {}}
    return _W
def lag_min_days(e, a):
    # 영향이 나타나기까지 가장 짧은 시차(일). 영향 문장의 「(시차 3~6개월)」이 있으면 그것, 없으면 요인의 시차(괄호 앞).
    m = re.search(r'시차\s*([0-9~]+\s*(?:개월|주|일))', a.get('why') or '')
    t = m.group(1) if m else re.sub(r'\(.*\)', '', e.get('lag') or '')
    m = re.match(r'\s*(\d+)\s*(?:~\s*\d+)?\s*(개월|주|일)', t)
    if not m: return None   # 「10월 말~12월 초」처럼 달력으로 적힌 것은 거르지 않음
    return int(m.group(1)) * {'개월': 30, '주': 7, '일': 1}[m.group(2)]
def world_adjust(sector, item, cap=None, horizon_days=None):
    # horizon_days: 신호의 예측 기간. 가장 짧은 시차가 이보다 긴 요인(예: 비료 원가 3~6개월)은 그 신호에 더하지 않음
    W = _load(); caps = W.get('caps') or {}
    cap = cap if cap is not None else caps.get(sector, 0.5)
    rows = []
    for e in W.get('events') or []:
        if not e.get('level'): continue
        for a in e.get('affects') or []:
            if a.get('sector') != sector: continue
            pat = a.get('item') or '.'
            try: ok = pat == '.' or re.fullmatch('(?:' + pat + ')', (item or '').strip())   # 품목 이름 전체가 맞아야 함('무'가 '무화과'에 걸리지 않게)
            except re.error: ok = False
            if not ok: continue
            w = a.get('w') or 0; sgn = 1 if a.get('dir') == '오름 쪽' else -1 if a.get('dir') == '내림 쪽' else 0
            if not sgn or not w: continue
            if horizon_days is not None:
                lm = lag_min_days(e, a)
                if lm is not None and lm > horizon_days: continue   # 같은 요인의 다른(시차 짧은) 영향은 계속 봄
            rows.append((sgn * w, e['id'], f'세계 요인: {e["name"]}' + ('(경보)' if e['level'] == 2 else '') + ' — ' + (a.get('why') or e.get('why') or '')[:60] + f' [{"+" if sgn > 0 else "−"}{w}]'))
            break
    rows.sort(key=lambda r: -abs(r[0]))
    tot = max(-cap, min(cap, sum(r[0] for r in rows)))
    why = [r[2] for r in rows[:3]] + ([f'세계 요인 외 {len(rows) - 3}건 (합계 {tot:+} — 갈래 상한 ±{cap} 적용)'] if len(rows) > 3 else ([f'세계 요인 합계 {tot:+} (갈래 상한 ±{cap})'] if rows and abs(sum(r[0] for r in rows)) > cap else []))
    return round(tot, 2), why, [r[1] for r in rows]
