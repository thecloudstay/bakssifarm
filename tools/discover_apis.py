# 연동창구 더 찾기: 공공데이터포털 검색 화면을 낱말별로 훑어 기존 후보(api_candidates.json)에 없는 오픈API·표준데이터를 모음
# 결과 → tools/api_discovered.json (번호·제목·기관·형식·낱말). 작업 공간에서는 포털이 막혀 깃허브 작업 흐름에서 돌림.
import json, os, re, time, urllib.request, urllib.parse, html as H
ROOT = os.path.dirname(os.path.abspath(__file__))
cands = {c['id'] for c in json.load(open(os.path.join(ROOT, 'api_candidates.json'), encoding='utf-8'))}
WORDS = ('축산 가축 한우 육우 젖소 돼지 양돈 한돈 닭 가금 계란 산란계 오리 염소 사슴 말 양봉 꿀 곤충 우유 낙농 사료 조사료 동물약품 동물용의약품 수의 동물병원 '
         '도축 도계 축산물 이력 등급판정 경락 경매 도매시장 공판장 가축시장 송아지 위판 수협 수산 양식 어업 어선 어촌 어항 수온 적조 해파리 패류독소 '
         '수산물 김 전복 굴 넙치 광어 우럭 뱀장어 새우 해삼 미역 다시마 멸치 오징어 꽃게 농산물 과수 사과 배 감귤 포도 딸기 채소 고추 마늘 양파 배추 '
         '화훼 버섯 인삼 특용작물 시설원예 스마트팜 농업기상 병해충 비료 농약 농기계 가격 시세 물가 수출입 수출 수입 관세 무역 검역 방역 구제역 '
         '조류인플루엔자 아프리카돼지열병 재해보험 농작물재해 농지 귀농 유통 로컬푸드 친환경 우수농산물 지리적표시 산림 임산물 표고 밤 '
         '면세유 어업인 농업인 농업경영체 축산농가 가축분뇨 퇴비 액비 악취 축사 양식장 어장 해역 갯벌 해양환경 기상 날씨 관측 예보').split()
JAR = urllib.request.HTTPCookieProcessor(); OP = urllib.request.build_opener(JAR)
def get(url, to=60):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36', 'Accept-Language': 'ko-KR,ko;q=0.9',
                                               'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8', 'Referer': 'https://www.data.go.kr/tcs/dss/selectDataSetList.do'})
    with OP.open(req, timeout=to) as r: return r.read().decode('utf-8', 'replace')
try: get('https://www.data.go.kr/')
except Exception as e: print('첫 화면 실패', e)
PER = int(os.environ.get('DISC_PER', '40'))
found = {}
if os.environ.get('DISC_WORDS'): WORDS = os.environ['DISC_WORDS'].split(',')
T0 = time.time(); LOG = []
def save():
    json.dump(sorted(found.values(), key=lambda x: -len(x['words'])), open(os.path.join(ROOT, 'api_discovered.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(LOG, open(os.path.join(ROOT, 'api_discover_log.json'), 'w', encoding='utf-8'), ensure_ascii=False)
DEBUG = os.environ.get('DISC_DEBUG')
for w in WORDS:
    if time.time() - T0 > 1500: LOG.append('시간 초과로 멈춤'); break
    for dtype, pat in (('API', r'/data/(\d+)/(openapi|standard)\.do'),):
        for page in range(1, 6):
            q = urllib.parse.urlencode({'dType': dtype, 'keyword': w, 'perPage': PER, 'currentPage': page, 'sort': ''})
            t1 = time.time()
            try: h = get('https://www.data.go.kr/tcs/dss/selectDataSetList.do?' + q)
            except Exception as e: LOG.append([w, page, '실패', str(e)[:80], round(time.time() - t1, 1)]); print('실패', w, e, flush=True); break
            if DEBUG and w == '축산' and page == 1:
                os.makedirs(os.path.join(ROOT, '_debug'), exist_ok=True); open(os.path.join(ROOT, '_debug', 'search.html'), 'w', encoding='utf-8').write(h)
            n = 0
            for li in re.split(r'<li[ >]', h):
                m = re.search(pat, li)
                if not m: continue
                i = m.group(1)
                t = re.search(r'<span class="title">(.*?)</span>', li, re.S)
                title = re.sub(r'\s+', ' ', H.unescape(re.sub(r'<[^>]+>', '', t.group(1)))).strip() if t else ''
                org = re.search(r'제공기관</span>\s*<span[^>]*>(.*?)</span>', li, re.S)
                n += 1
                if i in cands: continue
                e = found.setdefault(i, {'id': i, 'title': title, 'org': re.sub(r'<[^>]+>|\s+', ' ', org.group(1)).strip() if org else '', 'kind': m.group(2), 'words': []})
                if w not in e['words']: e['words'].append(w)
            LOG.append([w, page, n, len(h), round(time.time() - t1, 1)]); print(w, page, n, len(h), flush=True)
            time.sleep(0.4)
            if n < PER: break
    save()
save()
print('새로 찾은 연동창구', len(found))
