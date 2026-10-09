# 박씨팜 — 농장·어장·동물농장 한 지도

전국 시군별 가축 사육(35개 축종, 2018~2026), 양식 어장 면허 구역(11,486곳), 지리적표시 대표 품목(204건)을 한 지도에서 보고,
공판장·가축시장·수협 위판장·공영도매시장 위치와 경락가, 사료·자재 공동구매 모집판을 함께 둔 사이트입니다.

- 주소: https://thecloudstay.github.io/bakssifarm/ (깃허브 페이지, main 에 밀어 넣으면 자동으로 올라감). 넷리파이 프로젝트 bakssine(49a1aa45-…)은 토큰을 넣으면 함께 올라감. 나중에 도메인을 붙이면 저장소 변수 `SITE_BASE_URL` 만 바꾸면 됨
- 원칙: 개별 농가·어가 핀은 싣지 않음(가장 작은 단위는 리·읍면동). 예시 숫자는 「예시」, 확인 전 위치는 「위치 근사」로 표시.

## 폴더
- `site/` — 올라가는 폴더 전체(지도 `index.html`·`app.js`·`style.css`, 글 화면 `price/ gongu/ pro/ about/ console/ p/`, 자료 `data/`, 미리보기 그림 `og/`)
- `tools/` — 가공·수집·생성 스크립트
  - `build_livestock.py` 사육규모 묶음 → `data/livestock.json`
  - `build_aqua.py` 어장정보도 구역 → `data/aqua.json`, `data/aqua/*.json`
  - `build_crops.py` 지리적표시 → `data/crops.json`
  - `build_pins.py` 위판장·도매시장 핀 → `data/places.json`
  - `collect_ekape.py` 축산물품질평가원 경락가(열쇠 필요) → `data/price/`
  - `collect_license.py` 행정안전부 인허가(열쇠 필요) → `data/biz/`, `private/license/`
  - `sync_forms.py` 넷리파이 양식 접수 → `data/gongu.json`
  - `build_pages.py` 글 화면·사이트 지도·새 소식·robots·상태
  - `og.py` 미리보기 그림 165장
  - `indexnow.py` 색인 알림, `report.py` 텔레그램 아침 보고
- `raw/` — 원본 묶음(사육규모 35축종, 시군 경계)
- `private/` — 공개하지 않는 가공 자료(리 단위 집계)
- `.github/workflows/pages.yml` main 에 밀어 넣으면 깃허브 페이지에 올리기(처음 한 번 페이지를 자동으로 켬)
- `.github/workflows/daily.yml` 매일 06:17 수집→생성→기록→올리기→색인 알림, `report.yml` 매일 09:00 텔레그램 보고

## 다시 만들기
```
python3 tools/build_pages.py && python3 tools/og.py
```
자료를 바꾸면 해당 `build_*.py`를 먼저 돌립니다(저장소 뿌리에서 실행).

## 저장소 비밀값(설정 → Secrets)
| 이름 | 쓰임 | 없으면 |
|---|---|---|
| (변수) `SITE_BASE_URL` | 사이트 주소. 도메인 붙이면 여기만 바꿈 | 깃허브 페이지 주소 사용 |
| (변수) `FORM_ENDPOINT` | 접수함(구글 앱스 스크립트 웹앱 /exec, `tools/gas/접수함.gs`) | 양식이 넷리파이로 감(넷리파이가 멈추면 접수 안 됨) |
| `NETLIFY_AUTH_TOKEN` | 넷리파이에도 올리기(선택) | 넷리파이 단계 건너뜀 |
| `NETLIFY_SITE_ID` | `49a1aa45-e2be-40c1-8eeb-6e3c3a8dd7dc`(선택) | 넷리파이 단계 건너뜀 |
| `DATA_GO_KR_KEY` | 공공데이터포털 일반 인증키(축평원·인허가) | 경락가·인허가 「대기」 |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | 아침 보고 | 보고 안 보냄 |
| `INDEXNOW_KEY` | 색인 알림(아무 영숫자 8~128자) | 알림 건너뜀 |
| `GA_ID` | 구글 애널리틱스 측정 아이디 | 집계 안 함 |
| `NAVER_SITE_VERIFICATION` | 네이버 서치어드바이저 확인값 | 확인 메타 없음 |
| `KAKAO_JS_KEY` | 카카오 지도 자바스크립트 키(바탕지도) | 흰 바탕만 |

로컬에서는 `tools/config.json`(비공개)에 `ga_id`, `naver_verification`, `kakao_js_key`를 적어도 됩니다.

## 자료 출처
- 가축위생방역지원본부 전국 시군별 사육규모 현황(공공데이터포털, 공공누리 제1유형)
- 국립해양조사원 어장정보도 2025(개방해)
- 지리적표시 등록부(국립농산물품질관리원·산림청·국립수산물품질관리원)
- 통계청 통계지리정보서비스 시군 경계(2018)
- 축산물품질평가원 등급판정정보, 행정안전부 지방행정 인허가(연동창구)
