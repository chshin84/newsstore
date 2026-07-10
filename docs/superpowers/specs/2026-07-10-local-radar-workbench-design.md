# 로컬 레이더 작업장 전환 — 설계 스펙

> 2026-07-10 · 브레인스토밍(실효성 실험 → 방안 12종 렌즈 검증 → 종목 스테이션 디벨롭) 수렴 결과.
> 사용자 전권 위임("전부 진행하라")에 따라 열린 결정은 본문의 확정값으로 배선했다.
> 본문에서 ○숫자 방안 번호는 채택 보드의 방안(④가격 동기화·⑤수급·⑦카나리아·⑨관심-가격 괴리 신호·⑩백테스트·⑫프레임 시드 등)을 가리키고, "결정①~⑪"은 이 스펙의 결정 블록을 가리킨다 — 혼동을 피하기 위해 본문에서는 가급적 이름을 병기한다.

## 0. 요지

실효성 통제 실험(2026-07-07 아티팩트)의 판정 — 종목 분석 입력으로서 파이프라인의 한계가치는 0~음수이고, 스토어의 유일한 구조 우위는 종단 코퍼스(피드만이 시간을 기억한다는 것 — 아티팩트 원문 "스토어의 11,502건 종단 데이터가 여기서 유일하게 이긴다") — 에 따라 시스템을 둘로 가른다.

- **클라우드 = 피드 저장소**: collector + Firestore + 정적 Hosting만 남기고, Gemini 콜을 유발하는 모든 잡을 일시정지한다(가역 스위치).
- **로컬 = 작업장**: Firestore를 로컬 SQLite로 증분 동기화하고, 그 위에서 레이더 신호와 종목 스테이션을 **신규 LLM 콜 0의 순수 산수**로 계산해 일일 마크다운 한 장을 산출한다. 판단·프레임 재심은 구독 정액의 Claude 세션이 맡는다(한계비용 0).

우선순위는 사용자 정의를 따른다: **1차 = 종목 뷰**(특정 종목의 시각에서 세상을 받아들이는 수신), **2차 = 필드 뷰**(세상 변화의 프론티어 발굴). 두 뷰는 같은 레이더 커널의 두 절단면이며(1차=노드 고정 조건부, 2차=전역 순위), 임계는 커널이 아니라 뷰 계층에 둔다.

## 1. 결정 블록

- **결정① 클라우드 전면 컷** — Cloud Scheduler 5개(enrich·summary·lens·score·article) 일시정지. frames/report 잡은 만들지 않는다(미배포 유지). 코드·Job·테스트는 보존 — 재개는 resume 한 번(REVERSIBLE). 이 머신은 gcloud 무인증이므로 컷 실행은 §8의 절차 문서로 집에서 수행한다.
- **결정② 로컬 작업장 3커맨드** — `docker compose run --rm sync | prices | radar`. 전부 Docker 전용(이 호스트에 로컬 Python 없음), 전부 멱등. radar는 sync·prices가 적재한 로컬 DB만 읽는다(네트워크 접근 없음 — FOCUSED·실패 격리).
- **결정③ 레이더 4신호(필드 뷰)** — 테마 속도·동시등장 그래프 드리프트·어휘 창발·크로스렌즈 확산. 계산 정의는 §5. 관심-가격 괴리(방안⑨)의 발동 조건은 결정⑪이 SSOT다.
- **결정④ 커널 무임계·뷰 임계 분리** — 커널 함수는 임계 없이 원값(카운트·z-점수)을 반환한다. 필드 뷰는 유의 임계(z≥2.0)와 최소 빈도 필터로 상위만 표시하고, 종목 뷰는 무임계 피드-상대 전수를 표시한다. 같은 커널을 쓰되 실패 모드가 반대(필드=소음 회피, 종목=누락 회피)이기 때문이다.
- **결정⑤ 종목 스테이션(1차 뷰)** — `radar_out` 일보 안에 watchlist 종목당 한 블록. v1 구획: 커버리지 계기(필수 머리)·상태판(가격)·오늘의 게이트·활성 플랜·도착 뉴스(가설 구획 — 독립 기각 게이트 등록)·프레임 참조. 연결 변화 구획은 도착 뉴스 검증 후 추가. 스테이션은 판단하지 않는다 — 매수/스킵·극성 해석은 Claude 세션+웹.
- **결정⑥ 프레임 로컬 전환** — 프레임 상태를 Firestore가 아니라 `radar/frames.json`으로 옮기고, 갱신 주체를 Gemini 배치에서 Claude 세션(이월 재심)으로 바꾼다. 검증은 기존 순수 함수 계약(축 3종·축당 극 5 상한·무효 극 드롭)을 로컬 확장 스키마(status:"active"|"retired")로 이식해 재사용한다 — 클라우드 `frames.py` 계약은 건드리지 않고 로컬 검증기를 별도 모듈로 둔다(휴면 중인 클라우드 경로와의 계약 충돌 격리). 시드는 §7. git 커밋 이력이 frames_history를 대체한다. **복귀 방향 선언**: 이 결정 이후 프레임의 SSOT는 로컬 frames.json이며, 훗날 클라우드 프레임 패스를 재가동하려면 로컬→Firestore 이식이 선행 조건이다(절차는 그때 설계 — YAGNI).
- **결정⑦ 판단 원장 2종 + 추출 관례** — `radar/gates.yaml`(날짜 판정 조건의 유일한 홈)과 `journal/journal.jsonl`(플랜·트리거). 기계 참조는 frames→gates 단방향(gate_id)만 허용하고, gates의 on_confirm/on_refute는 사람용 액션 서술이다(기계 해석 금지 — 극 id를 적더라도 참조 무결성 검증 대상이 아니다). 공급은 "표준 추출 블록" 관례(§6.4) — 스킬화(/market-close)는 두 원장의 소비가 실측된 뒤 2차에서 한다(단일 실패점 방지).
- **결정⑧ 백테스트 러너** — 커널 신호를 기존 코퍼스에 소급 실행하는 `radar --backtest`. 신호3(어휘 창발) 캘리브레이션 + 신호1(테마 속도) 평시 오탐률 채점 + 신호2(간선) 산출량 실측을 겸한다. 성공 기준 사전 등록(§9). 프로덕션 신호 함수를 임포트하고 `--as-of`만 주입한다(로직 복제 금지 — SSOT).
- **결정⑨ 구조 방어 2건** — (a) 자기기만 루프 차단: 저널 채점(review)의 근거는 구조화 필드 `verdict_basis: {kind: price|flow|event, metric, value, source}`로만 기록 가능하며(enum·수치 — 기계 검증), 자유 서술 평가는 `user_approved: true`가 있어야 통과한다. gates의 상태 전이(pending→confirmed/refuted/void)도 `judged_by: user` 필드가 필수다 — 판정 주체가 사용자임을 스키마가 강제한다. (b) 죽은 기각 조건 차단: 모든 채택 층의 기각 판정일을 gates.yaml의 날짜 이벤트로 등록한다.
- **결정⑩ 사이트 = 피드 리더** — 피드 탭을 기본 탭으로 승격하고 스토리·리포트 탭은 숨긴다(코드 보존 — 표시만 제거). 갱신이 멈춘 탭을 신선한 것처럼 보여주는 조용한 드리프트 방지(FAIL-LOUD의 표시 변형).
- **결정⑪ 2차 항목과 발동 게이트 (SSOT)** — 방안⑤수급(pykrx)·방안⑦카나리아는 발동 게이트 "④가격 동기화 가동 개시 +7일 무장애 확인 즉시 착수"(사용자 승인 완료). 방안③원칙집+⑥플레이북·방안⑨신호5·추출 의식 스킬화는 "1차 세트 4주 소비 리뷰 통과" 게이트. 방안⑧알람 배선은 보류 — 재검토 여부는 4주 소비 리뷰 게이트에서 함께 판정한다(알람 누락이 실측 비용이었는지 확인).

## 2. 스코프

**포함(v1)**: watchlist.yaml, sync·prices·radar 커맨드(+backtest), 필드 뷰 4신호, 종목 스테이션(초기 3종목+지수·환율), gates.yaml·journal.jsonl·frames.json 시드와 검증기, radar_out 일보, 사이트 탭 조정, 컷 실행 절차 문서, 테스트 일습.

**제외(v1)**: 신호5(관심-가격 괴리), 수급·카나리아 구현체, 원칙집·플레이북 파일, /market-close 스킬, 알람 배선, 형태소 분석기, 분봉·재무 데이터, 클라우드 코드 변경(잡·패스 코드는 무수정 보존).

## 3. 데이터·파일 계약

### 3.1 `config/watchlist.yaml` — 종목·티커 SSOT
```yaml
# 종목·지수·환율의 단일 출처. sync/prices/radar/스테이션이 전부 여기서 도출.
entries:
  - id: sk_hynix
    label: SK하이닉스
    ticker: "000660.KS"          # yfinance 심볼
    role: stock                   # stock | index | fx
    station: true                 # 종목 스테이션 블록 생성 여부
    aliases: ["SK하이닉스", "하이닉스", "SK hynix"]   # 단어경계 매칭 어휘
  - id: samsung_elec
    label: 삼성전자
    ticker: "005930.KS"
    role: stock
    station: true
    aliases: ["삼성전자"]
  - id: sk_square
    label: SK스퀘어
    ticker: "402340.KS"
    role: stock
    station: true
    aliases: ["SK스퀘어"]
  - id: kospi
    label: 코스피
    ticker: "^KS11"
    role: index
    station: false
    aliases: ["코스피", "KOSPI"]
  - id: usdkrw
    label: 원달러
    ticker: "KRW=X"
    role: fx
    station: false
    aliases: []
```
역할 경계: **종목 매칭 어휘는 watchlist.yaml 단일**이고, 렌즈 정의는 기존 `config/topics.yaml`을 재사용한다(보존·무수정 — 두 어휘 집이 다시 생기는 것을 막는 경계 선언). 검증(fail-loud): id 중복, ticker 결측, station=true인데 aliases 빈 배열이면 로드 시 에러.

### 3.2 로컬 DB 2종 (분리 — 수명 정책이 다르다)

**`data/local.db` — Firestore 캐시.**
- 테이블 `items(id TEXT PK, feed_id, source, asset_hint, language, url, title, body, published_at, fetched_at, kind)` — 필드명은 Firestore 실계약(`firestore_store._to_doc`: feed_id·source·asset_hint·language·url·title·body·published_at·fetched_at·kind 등)을 그대로 따른다. `tags`는 동기화하지 않는다(클라우드 태깅이 꺼져 있어 신규 항목은 전부 빈 배열 — 렌즈 분류에 미치는 영향은 §5·§10에 명시).
- 워터마크는 **`fetched_at`**(collector가 전 문서에 필수 세팅 — 결측 누락 없음)이며, `published_at`은 nullable이라 워터마크로 부적합하다. `sync_state(key PK, value)`에 저장한다.
- 증분 pull: Firestore REST `runQuery`(공개 읽기·무인증)를 `fetched_at` 오름차순 정렬 + 페이지 크기 제한(예: 300)으로 **커서 페이지네이션**하고, **페이지 단위 체크포인트**로 워터마크를 "마지막 완결 페이지의 max(fetched_at)"까지만 전진시킨다 — 부분 적재가 항상 시간축 prefix가 되어 왜곡 유형이 단순해진다. 재시작 겹침은 24h.
- fail-loud: **초회 백필 결과가 0건이면 크래시**(필드명 드리프트·rules 변경이 "빈 동기화 성공"으로 조용히 통과하는 경로 차단). HTTP 오류·권한 거부(403)는 빈 결과와 구분해 즉시 크래시한다 — 가짜 0 금지.

**`data/prices.db` — 외부 소스 캐시.**
- 테이블 `prices(ticker, date, open, high, low, close, adj_close, volume, source, fetched_at, PK(ticker,date))`. yfinance 단일 소스(Stooq는 2026-07-10 세션 내 curl 실측에서 JS 봇차단으로 기각 — 방안④ 디벨롭 기록).
- 증분: 티커별 `MAX(date) − 5영업일`부터 겹쳐 받아 upsert(사후 정정 자가 치유·멱등). 빈 테이블이면 전체 이력 부트스트랩.
- sanity 경계(둘을 구분한다): **배치 수준** — 특정 티커의 신규 행 0건은 1일차엔 "결측: 사유"로 일보에 표기만 하고(한국 공휴일·대체휴일·티커별 캘린더 차이 — 거래일 판정기를 만들지 않는다, YAGNI), **3일 연속 0건이면 크래시**. **행 수준** — high<low·close≤0인 개별 행은 크래시가 아니라 `flagged` 마크로 격리한다(비파괴 — 계산에서 제외하되 보존).
- 첫 구현 단계에서 **컨테이너 내 yfinance 실호출을 role(stock|index|fx)별 각 1회** 실측하고, 테스트 픽스처는 그 실측 응답 캡처에서 도출한다(손제작 금지 — 오답노트의 "fake가 실계약을 약화" 재발 방지).

### 3.3 `radar/gates.yaml` — 날짜 판정 조건의 유일한 홈
```yaml
gates:
  - id: gate-0729-hynix-call
    date: 2026-07-29
    test: "SK하이닉스 Q2 콜에서 capex 지속성·HBM 가격 균열 신호 확인"
    on_confirm: "프레임 kr_equity의 사이클 피크아웃 테제 극(cycle-peak-thesis)을 승격 재심"   # 사람용 서술
    on_refute: "동 극 강등 재심, 하방 편향 플랜(plan-2026-07-10-hynix-entry) 재채점"
    status: pending
  - id: gate-adr-pin-release
    date: 2026-07-17
    test: "ADR 상장 첫 주 경과 — $149 앵커 핀 해제·본주 자율 가격 발견 여부"
    on_confirm: "카나리아 재검증 유효화, 프레임 premiums의 adr-book-conviction 극(시한부) retire 재심"
    on_refute: "핀 지속 — 판정 1주 연장"
    status: pending
  - id: gate-price-sync-stability
    date: 2026-07-17          # 기산: ④가격 동기화 가동 개시 +7일. 가동이 늦으면 첫 재심에서 날짜 재설정.
    test: "prices 커맨드 가동 개시 후 1주 무장애 확인"
    on_confirm: "수급(방안⑤)·카나리아(방안⑦) 착수 — 결정⑪"
    on_refute: "yfinance 지속성 재평가 후 게이트 재설정"
    status: pending
  - id: gate-workbench-adoption-review
    date: 2026-08-07          # 기산: 일보 가동 개시 +4주. 가동이 늦으면 첫 재심에서 날짜 재설정.
    test: "1차 세트 4주 소비 리뷰 — §9 운용 성공 기준 충족 여부 + 알람 누락(보류한 방안⑧)의 실측 비용 여부"
    on_confirm: "2차 세트(원칙집·플레이북·신호5·추출 스킬화) 착수"
    on_refute: "미소비 층 드롭(구획별 독립 판정)"
    status: pending
  - id: gate-arrival-news-verdict
    date: 2026-08-07
    test: "스테이션 '도착 뉴스' 가설 구획 — 4주 내 딥다이브 착수/스킵 기여 1회 이상"
    on_confirm: "구획 유지, 연결 변화 구획 착수"
    on_refute: "도착 뉴스 구획만 드롭(다른 구획 무영향)"
    status: pending
```
계약: status는 pending → confirmed|refuted|void로 반드시 닫히며, **전이 시 `judged_by: user` 필드 필수**(검증기 강제 — 결정⑨a). 판정일 3일 경과 pending은 radar 실행이 일보 머리에 경고로 올린다. 기계 참조는 frames→gates 단방향(gate_id)만이며 검증기는 frames의 gate_id가 gates.yaml에 실재하는지 검사한다. on_confirm/on_refute는 사람용 액션 서술이다(기계 해석·참조 무결성 검사 대상 아님). 게이트에는 선택 필드 targets(watchlist id 리스트)를 둘 수 있다 — 종목 스테이션의 "오늘의 게이트" 구획이 이 필드로 필터한다(스키마 검증: 리스트 타입).

### 3.4 `journal/journal.jsonl` — 판단 원장 (append-only)
```jsonl
{"type":"plan","id":"plan-2026-07-10-hynix-entry","date":"2026-07-10","target":"sk_hynix","thesis":"가격상태 하락장 확정·사이클 테제 미입증 — 7/29 전까지 하방 편향, 신호 확인 후 하단 진입","band":[2100000,2200000],"invalidation":"210만 종가 이탈 (주: 대화 원문은 구간 하단 210만 언급뿐 — 종가 기준은 시드가 도출한 제안, 첫 재심 대상)","triggers":[{"cond":"외국인 순매수 프린트 복귀 + SK스퀘어 비례 유지","action":"구간 상향 재설정 후 진입(신호를 사는 것이므로 220 위 허용)","by":"2026-07-29"}],"by":"2026-07-29"}
```
계약: plan은 `invalidation`·`by` 필수 — 검증기가 결측 시 append를 거부한다(시한 없는 판단은 채점 불가). review 타입은 plan id 참조 + `verdict_basis: {kind: "price"|"flow"|"event", metric, value, source}` 구조화 필드로만 기록하며(결정⑨a — enum·수치라 기계 검증 가능), 자유 서술 평가는 `user_approved: true`가 있어야 통과한다. 원본 수정 금지 — 정정도 append.

### 3.5 `radar/frames.json` — 로컬 프레임 (스키마 v2-local)
축 3종(risks/premiums/watchpoints), 축당 **active 극 ≤5**. 극 필드: `{id, label, evidence, test, retire_when, status: "active"|"retired", gate_id?}`. retired 극은 상한 비산입·다음날 이월 제외(비파괴 — 삭제 금지). 무효 극(id/label 결측)은 드롭. watchpoint의 날짜 판정은 본문에 적지 않고 gate_id로 gates.yaml을 참조한다(gate_id 실재 검증). 검증기는 신규 모듈로 두고 클라우드 `enrich/frames.py`는 무수정.

### 3.6 `radar_out/YYYY-MM-DD.md` — 일보 (유일한 산출물)
순서: ① 머리 — 경고(만기 pending 게이트, 데이터 결측은 생략이 아니라 "결측: 사유" 명시) ② 오늘의 게이트(±2일) ③ 필드 뷰 — 신호 4종 상위 항목(뷰 임계 적용)+근거 기사 표본 ④ 종목 스테이션 블록 × station=true 종목 ⑤ 부록 — 커버리지 총계. prices 실패는 radar를 막지 않는다 — 해당 섹션 결측 명시 후 진행(우아한 축소 — 일보 전체 신뢰를 지킨다).

## 4. 종목 스테이션 블록 (1차 뷰)

블록 구조(종목당):
1. **커버리지 계기(머리, 필수)** — 창 내 매칭 기사 수·본문 보유율·소스 다양성 + 고정 문구 "이 페이지는 피드가 본 세계다 — 판단 전 웹 확인". 스테이션의 약속은 **피드-상대 전수**이지 세상-전수가 아니다(실측: 부인 기사류 미도착은 어떤 계기에도 안 뜬다).
2. **상태판** — 종가, 전고점 대비 드로다운, MDD(기준 자산을 행마다 명시 — 지수/현물 혼동 방지), 원달러. 수급 행은 방안⑤ 착수 후 추가.
3. **오늘의 게이트** — 이 종목 관련 게이트의 날짜 필터.
4. **활성 플랜** — 저널의 미만료 plan + 현재가와의 결정론 비교. 현재가가 band 밖이면 "구간 밖" 경고를 자동 표기(추격 방지 — 실전 대화의 드리프트 사례를 구조로 이식).
5. **도착 뉴스(가설 구획)** — aliases 단어경계 매칭 기사: 카운트는 전수 표기, 나열은 최신순 20건+접기(표시 규칙이지 임계가 아니다 — 접힌 것도 카운트·파일에 남는다). 각 행에 **매칭 근거 병기**(어느 alias가 어디에 매칭됐는지) — 오탐(IREN→사이렌 류)을 사람이 즉시 식별. 24h 밀도 vs 7d 기준선 스파크 병기. 존속은 gate-arrival-news-verdict가 결정.
6. **프레임 참조** — 이 종목 id를 인용하는 frames 극 목록(참조 나열, 비용 0).

## 5. 계산 정의 (커널 — 전부 무임계 원값 반환, 임계·필터는 뷰 계층)

공통 전처리: 제목 정규화(공백·기호 정리) 후 완전 일치 dedup(신디케이트 중복 제거). 어휘 매칭은 **단어경계** 기준 — 한글은 토큰 경계(공백·기호), 영문은 `\b` — 부분문자열 매칭 금지.

- **신호1 테마 속도** — 렌즈별 24h 기사 수를 직전 28일 일별 분포의 평균·표준편차로 z-정규화(원값 반환). 표준편차 0이면 z 대신 "신규" 표기. 렌즈 분류는 기존 `classify_stage1` 결정론을 기사 단위로 재사용하되, **로컬 입력은 asset_hint·language·keyword_text(제목+본문 앞부분)뿐이고 tickers/entities/topics는 공집합**이다(태깅 컷 — 분류 해상도가 "피드 asset_hint+키워드" 수준으로 약화됨을 §10에 리스크로 명시, 유의미성은 §9 백테스트로 실측). 단, classify_stage1 내부의 키워드 매칭은 기존 계약대로 부분문자열이다(재사용·무수정 — §5 머리의 단어경계 규칙은 watchlist aliases·radar_vocab 매칭에 적용되는 것이지 이 함수의 예외까지 바꾸지 않는다). 뷰 필터: 필드 뷰는 24h 3건 미만 제외+z≥2.0, 종목 뷰는 전수.
- **신호2 그래프 드리프트** — watchlist aliases + `config/radar_vocab.yaml`(초기 = taxonomy entities 11종에서 도출 + 수동 추가) 어휘의 동일 기사 동시등장 = 간선(주 단위 집계, 원값 반환). 산출: (a) 신규 간선 — 직전 8주에 없던 쌍 (b) 허브 접속 — 볼륨 상위 노드에 새로 붙은 노드. **알려진 한계**: 어휘가 닫혀 있어 신규 개체는 신호3 창발→사용자 승격을 거쳐야 노드가 된다(후행 구조). 초기 어휘 ~20노드에서 산출량이 희소할 수 있으므로 §9 백테스트에서 8주 소급 산출량을 실측하고, 신규 간선이 월 3건 미만이면 필드 뷰에서 빼고 스테이션 절단만 남긴다(판정은 4주 리뷰 게이트).
- **신호3 어휘 창발** — 제목 토큰·바이그램(공백 분리, 1글자 토큰·불용어 제외)의 직전 W=3일 빈도와 기준선 B=30일 대비 z를 **원값으로 반환**한다. 뷰 필터: 필드 뷰는 최소 빈도 m≥3·z≥2.0(파라미터는 §9 백테스트로 재캘리브레이션, 채택 근거를 config 주석에 기록), 종목 뷰(종목 기사군 내 급등 어휘)는 전수. 상위 항목은 radar_vocab 승격 후보로 일보에 표기(승격은 사용자). 단, '1글자 토큰·불용어 제외'는 유니그램에만 적용한다 — 바이그램은 필터 전 원시 토큰열로 조립한다(1글자 토큰이 구 성분에서 선탈락하면 "변동성 덫" 류가 구조적으로 검출 불가가 되기 때문).
- **신호4 크로스렌즈 확산** — 개체·창발 어휘가 걸치는 서로 다른 렌즈 수의 주간 변화(원값 반환, 필드 뷰는 확대 상위만).
- **베이스라인 커버리지 가드** — 어느 신호든 기준선 창 안에 데이터가 있는 날이 창 길이의 2/3 미만이면(부분 백필 등) 그 신호를 계산하지 않고 "결측: 데이터 부족"으로 표기한다 — 구멍 난 코퍼스로 틀린 z를 조용히 내는 것 방지.
- **신호1 요일 왜곡 가드** — 주말 저볼륨이 z를 왜곡하면(§9 평시 오탐률 채점으로 실측) 기준선을 같은 요일 매칭 또는 7일 합산으로 교체한다.
- **스테이션 절단** — 위 커널을 노드 고정으로 재집계(신호1→종목 매칭 밀도, 신호2→종목 노드 간선, 신호3→종목 기사군 내 급등 어휘). 추가 계산 없음 — 집계 방향만 다르다.

## 6. 운영 의식 (사람·세션 절차)

1. **데일리**: `docker compose run --rm sync && docker compose run --rm prices; docker compose run --rm radar` (래퍼 `radar-daily` 하나로 묶는다. prices 실패가 radar를 막지 않는다 — 해당 섹션 결측 명시 후 진행).
2. **트리아지 세션**: Claude 세션이 `radar_out/최신.md` + `radar/frames.json` + 미만료 저널을 로드하고 시작한다. 프레임 재심(이월·승격·retire)은 세션이 수행하고 검증기 통과 후 커밋한다. 게이트 status 전이는 사용자 판정(`judged_by: user`) 없이는 기록할 수 없다.
3. **딥다이브**: 스테이션·필드 뷰가 촉발하면 웹+적대 대심(기존 Layer 1 방식) — 스토어는 트리아지까지만.
4. **표준 추출 블록(관례)**: 레포 밖 투자 대화를 마칠 때 고정 3섹션 마크다운(게이트/플랜/메커니즘 — 각 항목에 근거 인용 한 줄 필수)을 출력받아 레포 세션에 붙여넣고, 세션이 gates·journal에 반영한다(검증기 통과 필수). 메커니즘 섹션은 2차의 플레이북 채택 전까지 커밋 메시지·이슈 코멘트로만 보존한다.

## 7. 시드 (초기 데이터 — 전부 첫 재심 대상이지 확정판이 아님)

- **frames.json**: kr_equity — risks[lev-etf-reflexivity(레버리지 ETF 반사성 레짐), cycle-peak-thesis(2028 capex 벽·HBM 균열, gate_id: gate-0729-hynix-call), sell-on-best-print(호재 선반영)] / premiums[forced-flow-rebound(저PER 강제매도 반등 여력), adr-book-conviction(북빌딩 수요의 조용한 강세, gate_id: gate-adr-pin-release, 시한부)] / watchpoints[hynix-q2-call(gate_id: gate-0729-hynix-call), adr-pin-watch(gate_id: gate-adr-pin-release), foreign-flow-turn(외국인 수급 전환 — 판정식은 방안⑤ 착수 시 코드로), canary-sksquare(카나리아 재검증)]. risk — risks[mdd-basis-confusion(레버리지 MDD 오독·상시), llm-herding(LLM 동의를 센서로 쓰는 군집 편입·상시)] / watchpoints[bear-threshold(코스피 -20%=7,232 통과 여부)]. 편향 주의: 폭락 직후 시드라 risks 과체중·반도체 협착 — 첫 주 재심에서 레이더 산수와 대조해 소급 검증한다. 게이트 날짜도 첫 재심에서 가동 개시일 기준으로 재설정할 수 있다.
- **gates.yaml**: §3.3의 5건.
- **journal.jsonl**: §3.4의 plan 1건.
- **radar_vocab.yaml**: taxonomy entities 11종 도출 + 대화 유래 후보 수동 소량(엔비디아, HBM, ADR 등).

## 8. 클라우드 컷 실행 절차 (집에서 — 이 머신 gcloud 무인증)

1. `gcloud scheduler jobs pause newsstore-enrich-10min | newsstore-summary-hourly | newsstore-lens-10min | newsstore-score-10min | newsstore-article-10min` (5건 — collector `newsstore-5min`은 유지).
2. frames/report 잡·스케줄러는 애초에 만들지 않는다(기존 미배포 상태 유지 — 이전 배포 체크리스트의 해당 항목 폐기).
3. `web/index.html` 변경분(피드 탭 기본·스토리/리포트 탭 숨김) Hosting 재배포.
4. firestore.rules는 무변경(items·stories·meta 공개 읽기 — sync가 사용).
5. 재개 절차(전 단계 가역): pause한 잡 resume + Hosting 롤백 + **로컬 local.db 전체 재동기화**(정지 기간 밖 문서 갱신이 증분 창을 벗어나므로 — 캐시라 재구축이 안전하다).

## 9. 성공 기준·검증 (사전 등록 — TDD)

**테스트(구현 게이트, 전부 Docker)**:
- sync: 에뮬레이터를 **프로덕션과 동일한 REST 코드 경로**로 친다(SDK 대체 금지). ① 초회 전체 백필 ② 증분(신규만) ③ 두 번 연속 실행 = 동일 행수(멱등) ④ 페이지 중간 실패 시 워터마크가 마지막 완결 페이지까지만 전진 ⑤ 초회 백필 0건이면 크래시 ⑥ 403/HTTP 오류를 빈 결과와 구분해 크래시.
- prices: role별 실측 응답 캡처에서 도출한 픽스처로 upsert·겹침 자가치유·행 수준 flagged·배치 0행 1일 결측/3일 크래시 검증. 컨테이너 내 yfinance 실호출 role별 각 1회 실측 로그.
- radar 커널: 고정 픽스처 DB로 신호별 결정론 검증 — z-점수 수치, 단어경계(**"IREN"이 "사이렌"에 매칭되지 않음**을 명시 케이스로), 신규 간선 검출, 바이그램 급등, dedup, 베이스라인 커버리지 가드(부족 시 결측 표기).
- 계약 검증기: watchlist(중복 id·결측 ticker·station인데 빈 aliases), gates(status 어휘·만기 경고·전이 시 judged_by 필수·frames gate_id 실재), journal(invalidation·by 결측 거부, verdict_basis 구조 강제, user_approved 경로), frames(축 3종·축당 active 5 상한·retired 비산입·무효 극 드롭) — 각각 위반 픽스처가 크게 실패하는 테스트.
- 스테이션·일보: 픽스처로 "구간 밖" 경고·커버리지 계기·매칭 근거 병기·표시 규칙(전수 카운트+20건 접기)·prices 실패 시 결측 표기 진행을 검증.

**백테스트 성공 기준(사전 등록)**: 타깃 용어 10종을 고정한다 — 엔드게임, 사이드카, 서킷브레이커, 변동성의 덫, 반사성, 레버리지, ADR, 북빌딩, 디레버리징, HBM. 실행 전 코퍼스 실재를 grep으로 확인하고(10개 중 2개 미만 실재 시 제목-only 입력 재설계), 실재 용어의 과반이 7/7 이전에 검출되며, 평시 구간(2026-05) 일평균 창발 후보 ≤10건. 파라미터는 평시 오탐률로 좁히고 리드타임은 채점만(과적합 방지). 전부 후행이면 신호3을 조기경보→확인 신호로 강등하고 그렇게 기록한다 — 이것도 유효한 측정 결과다. 같은 러너로 신호1 평시 오탐률(요일 왜곡 포함)과 신호2 8주 산출량도 실측한다(§5의 강등 조건 판정 근거).

**운용 성공 기준(4주, 판정 gate-workbench-adoption-review·판정 주체 사용자)**: (a) 투자 세션 과반이 일보 로드로 시작 (b) 스테이션발 실효 1회 이상(게이트 상기가 판정을 만들었거나, 구간 밖 경고가 추격을 막았거나, 도착 뉴스가 딥다이브를 촉발).

## 10. 리스크 (정직 표기)

- **yfinance 지속성** — Stooq 사망(2026-07-10 실측)이 전례. 파손 감지는 sanity가 하고, 파손 시 일보는 해당 섹션 결측 명시 후 진행(우아한 축소). 3연속 실패 시 소스 이원화 재검토.
- **렌즈 분류 해상도 약화** — 태깅 컷으로 로컬 stage1 입력은 asset_hint+키워드뿐이라 렌즈≈피드 그룹으로 퇴화할 수 있다. §9 백테스트가 신호1의 유의미성을 실측하고, 무의미하면 "렌즈별"이 아니라 "asset_hint별" 속도로 정직하게 강등해 명명한다.
- **한국어 토큰화** — 공백 기반이라 조사 붙은 구를 놓친다. 백테스트가 절반 이상 놓치면 형태소 분석기를 후속 과제로 올린다(v1 도입 금지 — YAGNI).
- **자기참조** — Claude가 시드한 프레임을 Claude가 재심한다. 완화: 재심 근거를 레이더 산수·게이트 판정(외부 사실)에 묶고, 게이트 전이·서사 채점은 사용자 승인 스키마 강제(결정⑨a).
- **커버리지** — 피드가 못 본 것은 계기에도 안 뜬다. 스테이션 머리의 고정 문구와 커버리지 계기가 유일한 방어이며, 딥다이브는 반드시 웹으로 한다.
- **갱신·삭제 미추적** — fetched_at 증분은 신규만 본다. v1(클라우드 정지 중)에는 무해하고, 재개 시 §8-5의 전체 재동기화로 해소한다.

<!-- spec-review: passed -->
