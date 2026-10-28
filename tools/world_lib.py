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
def world_adjust(sector, item, cap=None):
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
            rows.append((sgn * w, e['id'], f'세계 요인: {e["name"]}' + ('(경보)' if e['level'] == 2 else '') + ' — ' + (a.get('why') or e.get('why') or '')[:60] + f' [{"+" if sgn > 0 else "−"}{w}]'))
            break
    rows.sort(key=lambda r: -abs(r[0]))
    tot = max(-cap, min(cap, sum(r[0] for r in rows)))
    why = [r[2] for r in rows[:3]] + ([f'세계 요인 외 {len(rows) - 3}건 (합계 {tot:+} — 갈래 상한 ±{cap} 적용)'] if len(rows) > 3 else ([f'세계 요인 합계 {tot:+} (갈래 상한 ±{cap})'] if rows and abs(sum(r[0] for r in rows)) > cap else []))
    return round(tot, 2), why, [r[1] for r in rows]
