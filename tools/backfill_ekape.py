# 축산물품질평가원 경락가 되채우기(2026-10-30) — 갭 기회·물가 지수의 기준 기간을 1년으로 늘리려고, 비어 있는 지난 거래일의 한우 거세·돼지 탕박 등급별 경락가를 하루씩 받아 history 에 채운다.
#   하루 호출 한도(1,000건) 안에서 한 번에 최대 BUDGET 일(일당 2건)만 채우고, 다음 아침에 이어서 채운다. 다 채워지면 아무 일도 하지 않는다.
import sys, os, datetime, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import collect_ekape_lib as EK
BUDGET = int(env('EKAPE_BACKFILL_DAYS', '110')); DAYS = 370
HIST = os.path.join(DATA, 'price', 'history'); os.makedirs(HIST, exist_ok=True)
if not EK.KEY: status('ekape_backfill', None, '열쇠 없음'); sys.exit(0)
today = now().date(); have = {f[:10] for f in os.listdir(HIST) if f.endswith('.json')}
done = 0; miss = 0; last = ''
try:
    for k in range(2, DAYS):
        d = today - datetime.timedelta(days=k)
        if d.weekday() >= 5 or d.isoformat() in have: continue
        if done >= BUDGET: break
        c = EK.cattle(d); p = EK.pig(d); done += 1
        if not any(r['g'][:1] in '123' for r in c) and not p:
            miss += 1; jsave(os.path.join(HIST, d.isoformat() + '.json'), {'date': d.isoformat(), 'ekape': [], 'empty': True, 'backfill': True}); continue   # 공휴일: 빈 표시를 남겨 다시 묻지 않음
        jsave(os.path.join(HIST, d.isoformat() + '.json'), {'at': stamp(), 'date': d.isoformat(), 'ekape': [{'title': '한우 거세', 'rows': c, 'date': d.isoformat()}, {'title': '돼지 탕박', 'rows': p, 'date': d.isoformat()}], 'backfill': True, 'source': '축산물품질평가원 등급판정정보(되채움), 원/㎏'})
        last = d.isoformat()
    left = sum(1 for k in range(2, DAYS) if (today - datetime.timedelta(days=k)).weekday() < 5 and (today - datetime.timedelta(days=k)).isoformat() not in have) - done
    status('ekape_backfill', True, f'이번에 {done}일 채움(빈 날 {miss}) · 남은 거래일 {max(0, left)}' + (f' · 마지막 {last}' if last else ''))
    print('되채움', done, '빈 날', miss, '남음', max(0, left))
except Exception as e:
    status('ekape_backfill', False, f'{done}일 채운 뒤 실패: {str(e)[:120]}'); print('실패', e)
