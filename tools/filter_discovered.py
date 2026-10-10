# 더 찾은 연동창구 중 박씨팜(가축·어장·농장·유통)과 맞는 것만 골라 후보에 붙일 목록을 만듦
import json, os, re, collections
ROOT = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(ROOT, 'api_discovered.json'), encoding='utf-8'))
ANI = r'축산|가축|한우|육우|젖소|돼지|양돈|한돈|닭|가금|계란|산란계|육계|오리|염소|양봉|곤충|원유|낙농|사료|도축|도계|식육|축산물 ?이력|쇠고기|등급판정|구제역|조류인플루엔자|돼지열병|가축방역|동물용 ?의약품|동물약품|가축분뇨|축사|퇴비|액비|동물병원|수의사'
SEA = r'수산|양식|어업|어선|어항|어촌|어장|수협|위판|수온|적조|해파리|패류|전복|넙치|광어|우럭|뱀장어|새우|해삼|미역|다시마|멸치|오징어|꽃게|조위|조석|파고|해양관측|해양환경|면세유|갯벌|어획|해황'
CROP = r'농산물|과수|과일|채소|화훼|버섯|인삼|원예|스마트팜|농작물|병해충|비료|농약|농기계|농지|친환경농|지리적표시|임산물|표고|작황|로컬푸드|농협|농가|귀농|토양|농업기상|농업'
TRADE = r'가격|시세|경락|경매|도매시장|공판장|수출입|수입|검역|관세|무역|유통|물가'
NO = r'반려|유기동물|구조동물|동물등록|동물보호|안심식당|경마|경주|마권|승마|말진료|관광|채용|장학|도서관|체육|버스|주차|자전거|약국|의료기관|어린이|학교|급식|음식점|모범음식|위생등급|대기오염|미세먼지|아파트|부동산|전기차|충전소|문화재|축제|숙박|캠핑|등산|휴양림|수목원|해수욕장|낚시터|요트|여객|항공|철도|레시피|법령해석|연구관리|건강기능|의료기기|화장품|의약품 ?허가|낚시어선|폐기물|침적|화물처리|REC|SMP|지수시세|증권|주식|채권|보훈|청소년|고용동향|재산|가스사고|붕괴|특허|KIPRIS|출원|100문|교육|컨설팅|발간|연보|요리|사전|공통코드|메타데이터|분양|학자금|사격|시운전|에너지개발|해무|해수면|격자|특성평가|수심|공유수면|연안정비|환경영향|게시글|종자대|ROMS|수치|용어|표본관|시험연구|유전자원|기본수준점|해도|항로|등대|선박위치|AIS|지명|전원마을|안내|소개|홍보|행사|공지'
ORG = r'농림축산식품부|농촌진흥청|해양수산부|농림수산식품교육문화정보원|축산물품질평가원|한국농수산식품유통공사|농수산식품공사|산림청|수산업협동조합|수협|한국농어촌공사|국립수산과학원|해양환경공단|국립해양조사원|관세청|식품의약품안전처|기상청|축산환경|농업기술실용화재단|한국농업기술진흥원|농업정책보험금융원|축산경제|농협'
keep = []
for x in D:
    t = re.sub(r'^[^_]*_', '', x['title'])
    if re.search(NO, t, re.I): continue
    dom = '동물농장' if re.search(ANI, t) else '어장' if re.search(SEA, t) else '농장' if re.search(CROP, t) else None
    org_ok = bool(re.search(ORG, x['org']))
    tr = bool(re.search(TRADE, t))
    if not dom and not (tr and org_ok and x['cat'] == '농축수산'): continue
    if dom and not org_ok and x['cat'] not in ('농축수산', '식품건강', '환경기상', '재난안전'): continue
    if x['org'].startswith('식품의약품안전처') and dom is None: continue
    cat = '시세·거래' if re.search(r'가격|시세|경락|경매|도매시장|공판장|위판|거래', x['title']) else '수출입' if re.search(r'수출|수입|관세|무역|검역', x['title']) else \
          '질병·이상' if re.search(r'방역|구제역|조류인플루엔자|돼지열병|질병|적조|해파리|패류|병해충|재해', x['title']) else \
          '환경·관측' if re.search(r'수온|조위|조석|파고|관측|기상|수질|해양환경|토양', x['title']) else \
          '업체·인허가' if re.search(r'업체|업소|허가|신고|인증|지정|현황', x['title']) else '사육·생산'
    keep.append({'id': x['id'], 'title': x['title'], 'cat': cat, 'dom': dom or '공통', 'host': '', 'paths': [], 'fields': [], 'org': x['org'], 'kind': x['kind'], 'src': '더 찾기'})
json.dump(keep, open(os.path.join(ROOT, 'api_more.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(keep), collections.Counter(k['dom'] for k in keep), collections.Counter(k['cat'] for k in keep))
