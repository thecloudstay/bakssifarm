# 축산물품질평가원 등급판정정보 공통(2026-10-30) — collect_ekape.py(아침)와 backfill_ekape.py(되채움)가 같이 쓴다.
import os, sys, xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
BASE = 'http://data.ekape.or.kr/openapi-data/service/user/grade/'
ABATT = {'0513': '농협 음성', '0613': '관성', '0616': '농협 포크빌(부천)', '1005': '김해 축공', '0202': '부경 축공', '0201': '동원산업', '1201': '신흥산업', '0905': '농협 고령', '0714': '익산', '0809': '농협 나주', '1401': '삼호축산', '1101': '제주축협', '1015': '해드림(홍성)', '0717': '중앙 축산물도매시장(안성)'}
KEY = env('DATA_GO_KR_KEY')
CQ = dict(breedCd='024001', sexCd='025003', qgradeYn='Y', defectIncludeYn='Y')   # 한우 거세, 육질등급(1++·1+·1·2·3)만
def call(op, **params):
    params['serviceKey'] = KEY
    raw = get(BASE + op, params)
    root = ET.fromstring(raw)
    code = (root.findtext('.//resultCode') or '').strip()
    if code not in ('00', '0', ''): raise RuntimeError(op + ' ' + (root.findtext('.//resultMsg') or code))
    return [{c.tag: (c.text or '').strip() for c in it} for it in root.iter('item')]
def num(s):
    try: return int(float(s.replace(',', '')))
    except Exception: return None
def grade_rows(items, order):
    out = {}
    for it in items:
        g = it.get('gradeNm') or it.get('gradeCd'); amt = num(it.get('CTotAmt') or it.get('totAmt') or '')
        cnt = num(it.get('CTotCnt') or it.get('totCnt') or '')
        if g and amt: out[g] = {'g': g, 'p': amt, 'n': cnt, 'ab': {ABATT[k]: num(it.get('c_' + k + 'Amt')) for k in ABATT if num(it.get('c_' + k + 'Amt') or '')}}
    return [out[g] for g in order if g in out] + [out[g] for g in out if g not in order]
def day(d): return d.strftime('%Y%m%d')
def cattle(d): return grade_rows(call('auct/cattle', startYmd=day(d), endYmd=day(d), **CQ), ['1++', '1+', '1', '2', '3', '등외'])
def pig(d): return grade_rows(call('auct/pigGrade', startYmd=day(d), endYmd=day(d), skinYn='Y', egradeExceptYn='N'), ['1+', '1', '2', '등외'])
