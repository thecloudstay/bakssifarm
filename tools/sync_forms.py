# 넷리파이 양식 접수(모집 열기·참여 신청·업체 등록·가격 알림) → 모집판 자료(site/data/gongu.json)와 접수 집계
# 열쇠: NETLIFY_AUTH_TOKEN, NETLIFY_SITE_ID. 연락처는 공개 파일에 넣지 않음.
import sys, os, json, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
TOKEN = env('NETLIFY_AUTH_TOKEN'); SITE_ID = env('NETLIFY_SITE_ID')
if not TOKEN or not SITE_ID:
    status('forms', None, '넷리파이 열쇠 없음'); print('열쇠 없음'); sys.exit(0)
H = {'Authorization': 'Bearer ' + TOKEN, 'User-Agent': 'bakssine/1.0'}
try:
    forms = json.loads(get(f'https://api.netlify.com/api/v1/sites/{SITE_ID}/forms', headers=H))
    subs = {}
    for f in forms:
        page = 1; rows = []
        while True:
            r = json.loads(get(f'https://api.netlify.com/api/v1/forms/{f["id"]}/submissions', {'per_page': 100, 'page': page}, headers=H))
            rows += r
            if len(r) < 100: break
            page += 1
        subs[f['name']] = rows
    opens = sorted(subs.get('gongu-open', []), key=lambda s: s['created_at'])
    joins = subs.get('gongu-join', [])
    items = []
    for i, s in enumerate(opens, 1):
        d = s.get('data', {}); gid = f'공구-{i:04d}'
        got = 0.0
        for j in joins:
            jd = j.get('data', {})
            if (jd.get('모집번호') or '').strip() == gid:
                try: got += float(jd.get('수량') or 0)
                except ValueError: pass
        try: goal = float(d.get('목표수량') or 0)
        except ValueError: goal = 0
        due = d.get('마감일') or ''
        st = '성립' if goal and got >= goal else ('마감' if due and due < now().date().isoformat() else '모집 중')
        items.append({'id': gid, 'kind': d.get('종류', ''), 'item': d.get('품목규격', ''), 'area': d.get('지역', ''), 'goal': int(goal) if goal.is_integer() else goal, 'got': int(got) if got.is_integer() else got, 'due': due, 'status': st, 'note': (d.get('설명') or '')[:140], 'opened': s['created_at'][:10]})
    items = [it for it in items if it['status'] != '마감' or (now().date() - datetime.date.fromisoformat(it['opened'])).days < 60]
    jsave(os.path.join(DATA, 'gongu.json'), {'at': stamp(), 'items': items[::-1]}, indent=1)
    # 구입가 제보 집계: 종류·품목·단위·시군별 중위값(5건 이상), 개별 제보·연락처는 공개하지 않음
    import statistics
    groups = {}
    for s in subs.get('buy-report', []):
        d = s.get('data', {})
        try: price = float(d.get('단가') or 0)
        except ValueError: continue
        if price <= 0: continue
        key = (d.get('종류', ''), (d.get('품목규격') or '').strip(), d.get('단위', ''), d.get('지역', ''))
        groups.setdefault(key, []).append((price, s['created_at'][:10]))
    rows = []
    for (kind, item, unit, area), vals in groups.items():
        if len(vals) < 5: continue
        rows.append({'kind': kind, 'item': item, 'unit': unit, 'area': area, 'median': int(statistics.median(v[0] for v in vals)), 'n': len(vals), 'last': max(v[1] for v in vals)})
    rows.sort(key=lambda r: (-r['n'], r['kind'], r['item']))
    jsave(os.path.join(DATA, 'buyprice.json'), {'at': stamp(), 'n': len(subs.get('buy-report', [])), 'items': rows}, indent=1)
    cnt = {k: len(v) for k, v in subs.items()}
    p = os.path.join(DATA, 'status.json'); st = jload(p, {}); st.setdefault('counts', {})['forms'] = ' · '.join(f'{k} {v}' for k, v in cnt.items()) or '0'; jsave(p, st, indent=1)
    status('forms', True, f'모집 {len(items)}건 · 접수 {sum(cnt.values())}건')
    print('양식', cnt)
except Exception as e:
    status('forms', False, str(e)[:200]); print('실패', e)
