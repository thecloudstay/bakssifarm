# 텔레그램 아침 보고(매일 9시) · 월요일은 주간 요약을 덧붙임
# 열쇠: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
import sys, os, json, datetime, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
TOKEN = env('TELEGRAM_BOT_TOKEN'); CHAT = env('TELEGRAM_CHAT_ID'); keyflag('telegram', TOKEN and CHAT)
st = jload(os.path.join(DATA, 'status.json'), {}); price = jload(os.path.join(DATA, 'price', 'latest.json'), {}); gongu = jload(os.path.join(DATA, 'gongu.json'), {'items': []})
NAMES = {'ekape_price': '경락가', 'license': '인허가', 'forms': '양식', 'pages': '글 화면', 'og': '미리보기', 'indexnow': '색인 알림', 'deploy': '올리기'}
lines = [f'🌱 박씨네 아침 보고 {now().strftime("%m월 %d일")}']
cols = st.get('collectors', {})
okl = [NAMES.get(k, k) for k, v in cols.items() if v.get('ok')]; bad = [f'{NAMES.get(k, k)}({v.get("msg", "")[:40]})' for k, v in cols.items() if v.get('ok') is False]; wait = [NAMES.get(k, k) for k, v in cols.items() if v.get('ok') is None]
lines.append('수집 정상: ' + (', '.join(okl) or '없음'))
if bad: lines.append('⚠️ 실패: ' + ', '.join(bad))
if wait: lines.append('대기(열쇠 없음): ' + ', '.join(wait))
if price.get('ekape'):
    for sec in price['ekape']:
        top = sec['rows'][:3]
        lines.append(f'{sec["title"]}({price.get("date", "")}): ' + ' · '.join(f'{r["g"]} {r["p"]:,}' + (f'({r["d"]:+,})' if r.get('d') is not None else '') for r in top))
items = gongu.get('items', [])
if items:
    lines.append(f'공동구매 모집 {len(items)}건: ' + ' · '.join(f'{i["id"]} {i["item"]} {i["area"]} {i["status"]}' for i in items[:3]))
if st.get('counts', {}).get('forms'): lines.append('양식 접수: ' + str(st['counts']['forms']))
lines.append(f'글 화면 {st.get("counts", {}).get("pages", "–")}쪽 · https://bakssine.netlify.app/console/')
if now().weekday() == 0:
    hist = sorted(os.listdir(os.path.join(DATA, 'price', 'history'))) if os.path.isdir(os.path.join(DATA, 'price', 'history')) else []
    wk = [jload(os.path.join(DATA, 'price', 'history', f)) for f in hist[-5:]]
    if wk:
        def avg(title, g):
            vs = [r['p'] for w in wk for s in w.get('ekape', []) if s['title'] == title for r in s['rows'] if r['g'] == g]
            return f'{sum(vs) / len(vs):,.0f}' if vs else '–'
        lines.append(f'📅 주간: 한우 거세 1+ 평균 {avg("한우 거세", "1+")} · 돼지 탕박 1+ 평균 {avg("돼지 탕박", "1+")} (지난 {len(wk)}거래일)')
    lines.append('주간 할 일: 위치 근사 핀 확인, 모집판 정리, 열쇠 상태 점검')
msg = '\n'.join(lines)
print(msg)
if not TOKEN or not CHAT: status('report', None, '텔레그램 열쇠 없음'); sys.exit(0)
try:
    data = urllib.parse.urlencode({'chat_id': CHAT, 'text': msg, 'disable_web_page_preview': 'true'}).encode()
    with urllib.request.urlopen(urllib.request.Request(f'https://api.telegram.org/bot{TOKEN}/sendMessage', data=data), timeout=30) as r: r.read()
    status('report', True, '보냄')
except Exception as e:
    status('report', False, str(e)[:160]); print('실패', e)
