# 수집 대시보드 설계 (collection dashboard)

## 목적·범위

newsstore가 수집하는 각 데이터 종류가 **최근 정상적으로 들어오고 있는지 한 화면에서 확인**하는 정적 웹 페이지를 만든다. 목적은 두 가지다.

1. **수집 상태(건강)** — 각 데이터 종류가 마지막으로 언제 수집됐는지, 수집이 조용히 멈추지 않았는지.
2. **종목 드릴다운(스팟체크)** — 종목 하나를 골라 그 종목의 각 컬렉션 최신 값을 훑어 "값이 말이 되는지" 확인.

이것은 분석 도구가 아니다 — 분석은 다운스트림 몫이다. newsstore는 수집 전용이고, 이 대시보드는 그 수집이 잘 되는지 보는 **내부 확인용**이다.

**비목표(하지 않는 것):** 차트/지표 계산, 팩터 랭킹, 백테스트, 시계열 재구성(PIT 유니버스 역산 등 — 다운스트림), 데이터 편집.

## 배경·제약 (합의된 결정)

- **읽기 경로 = Firebase Auth(구글 로그인) + 이메일 허용목록 게이트 + 클라이언트 직접 쿼리(바운드).** 완전 공개가 아니다 — **허용목록에 오른 이메일로 로그인한 사용자만** read. "이메일로 링크를 받은 사람만 접근"을 이렇게 구현한다(사용자 선택). 이 결정이 앞선 공개-read 스크래이핑 리스크(무인증 FMP 벌크 미러)를 **해소**한다.
- **접근 통제 구현:** ① Firebase 콘솔에서 구글 로그인 provider 활성화. ② 허용 이메일을 `config/allowlist` 문서(`{emails:[...]}`)에 둔다 — 비공개(클라이언트 read 금지), 규칙이 `get()`으로 서버측에서만 읽는다. 사람 추가/취소 = 이 목록 한 줄(규칙 재배포 불요). ③ `firestore.rules`가 데이터 read를 `request.auth != null && request.auth.token.email in allowlist`로 게이트. **write는 전부 금지 유지**(Admin SDK만). 백엔드·서버 없음.
- **잔여 리스크(정직히):** 허용된 소수는 여전히 데이터를 볼·긁을 수 있다(신뢰 그룹). 그러나 공개 노출(비가역)이 아니고 **개별 부여·취소 가능**하다. 전제: 방문자는 허용된 이메일의 구글 계정으로 로그인해야 한다(구글 계정 없는 수신자는 이메일 링크 방식으로 대체 — 설정 더 듦).
- **비용(실측):** 이 대시보드가 호스팅·읽기에 더하는 비용은 사실상 $0이다. Firebase Hosting은 정적 파일 서빙이라 데이터량과 무관(페이지 ~150 KB, 무료 전송 360 MB/일 = 하루 ~2,400 로드). Firestore 읽기는 바운드 설계로 세션당 ~100~150회(무료 50,000회/일). 비용이 드는 곳은 수집 레이어의 저장·쓰기이고 그건 TTL이 잡는다 — 대시보드 소관 아님.
- **컬렉션 규약 SSOT:** `docs/firestore-contract.md`. 모든 문서에 `fetched_at`(수집 시각)이 있고, 팩터/재무 문서 id는 `{symbol}__{YYYYMMDD}` 결정론 키다. 이 두 성질이 대시보드 쿼리의 토대다.

## 구조

- **별도 페이지 `web/dashboard.html`.** 기존 `index.html`(뉴스 리더)은 손대지 않는다. 관심사가 다르고(`FOCUSED`) index.html은 이미 크다.
- Firebase 설정은 기존 `web/config.js`를 재사용한다(웹 apiKey는 비밀 아님 — 규칙이 데이터를 보호). Firestore JS SDK(모듈, CDN) 직접 사용, 기존 index.html과 동일 패턴.
- **접근 게이트:** 대시보드는 Firebase Auth 구글 로그인을 요구한다 — 진입 시 미로그인이면 "구글로 로그인" 화면만, 로그인(허용목록 통과) 후 데이터를 렌더한다. Auth SDK(모듈 CDN)만 추가하고 백엔드는 없다. index.html(공개 뉴스 리더)은 로그인 불요 — 게이트는 이 페이지에만.
- 순수 로직(신선도·지연 판정·포맷·그룹핑)은 테스트 가능한 함수로 분리해 `web/dashboard.html` 안 `<script type="module">`에 두되, node 테스트가 import할 수 있게 `web/dashboard_logic.mjs`로 뽑는다(기존 `web/*.js` 로직 분리 관행과 동일). index.html은 이 파일을 쓰지 않는다.

## 화면 1 — 수집 상태 카드

데이터 종류별 카드를 세로로 나열한다. 계약의 17개 컬렉션을 주기·주제로 **7개 카드**로 빠짐없이 묶는다(아래 표의 컬렉션 합집합 = 계약 전 컬렉션 — 하나도 감시에서 빠지지 않게).

| 카드 | 묶는 컬렉션 | 기대 주기 | 카드에 보이는 것 |
|---|---|---|---|
| 뉴스 | `items` | 5분 | 마지막 수집 상대시각 · 최근 소스·제목 1줄 |
| 시세(5분봉) | `price_bars`, `prices` | 5분(장중) | 마지막 바 시각 · 심볼 수(12) |
| 배당조정 EOD | `prices_eod` | 일(장마감 후) | 마지막 수집 · 샘플 종목 최근 adjClose |
| 재무제표 | `income`·`balance`·`cashflow` | 주 | 마지막 수집(가장 오래된 것 기준) · 샘플 종목·회계일 |
| 프로파일·비율·시총·등급이력 | `profiles`·`ratios`·`market_cap`·`grades_history` | 주 | 마지막 수집 · 샘플 (grades_history=§1 백필 가능) |
| 컨센서스 | `estimates`·`price_targets`·`grades_consensus` | 주 | 마지막 수집(as-of) · 샘플 (§2 백필 불가 3종) |
| 유니버스 | `index_members`·`index_changes`·`delisted` | 주 | 현재 구성 N종목(3개 지수 합집합) · 최근 변경 로그 몇 건 |

각 카드 공통:
- **"마지막 수집: N시간 전 · 기대: 주기"** 텍스트. 상대시각(예: `3일 전`)과 기대 주기(예: `주간`)를 나란히.
- **`⚠️ 지연`** 은 기대 주기를 한참 넘겼을 때만(아래 §지연 로직). 정상은 아무 장식 없음.
- 카드가 여러 컬렉션을 묶으면 **가장 오래된(=가장 뒤처진) 컬렉션의 최신 수집 시각**을 카드 신선도로 삼는다(하나만 멈춰도 카드가 잡는다). 펼치면 컬렉션별 상세.
- 뉴스·시세 카드는 "상세는 index.html에서" 링크.

상단에 페이지 로드 시각(KST)과 "새로고침" 버튼.

### 지연 로직 (주기 인지 · 순수함수)

`web/dashboard_logic.mjs`의 순수함수로 구현하고 node 테스트로 검증한다. 문턱은 매직넘버가 아니라 **계약(주기·30일 데드라인)에서 도출**한 값을 불변식으로 둔다(`market-data-integrity`). 판정은 **표시만**(비파괴).

- **기대 간격 테이블**(카드별, 초): 5분·일·주. 이 테이블은 클라이언트가 Cloud Scheduler를 읽을 수 없어 실제 스케줄(`docs/operations.md §8`·`setup.md §8`의 cron/cadence)의 **UI측 사본**이다 — 불가피한 두 번째 출처다. 그래서 (a) 테이블을 이 파일 한 곳에만 두고(SSOT), (b) 실제 스케줄을 나타내는 선언 상수와 어긋나면 터지는 드리프트 테스트를 둔다. 스케줄을 바꾸면 이 테이블도 바꾼다(주석·계약에 명시). 매직넘버 금지를 cadence에도 적용.
- **빈 컬렉션 = '정상' 절대 금지(FAIL-LOUD — 핵심):** `orderBy(fetched_at desc).limit(1)`이 빈 결과면(최초 미수집 **또는** TTL로 전량 만료) `lastFetchedAt`이 없다. 이때 `isOverdue(null, …, now)`는 **항상 경보**(`⚠️ 데이터 없음/기한 초과`)를 반환한다 — NaN 비교로 조용히 '정상'이 되지 않게. TTL(30일)과 결합하면 "오래 멈출수록 컬렉션이 비어 더 건강해 보이는" 역설이 생기므로, 이 뒤집기가 대시보드의 존재 이유다. 불변식 테스트: `isOverdue(null)` → 경보.
- **§1(백필 가능) 문턱:** `now - lastFetched > OVERDUE_FACTOR × 기대간격`. `OVERDUE_FACTOR`는 보수적(예: 3) — 한 번 걸러도 바로 빨개지지 않게. 유실돼도 재수집 복구 가능이라 느슨해도 된다.
- **§2(백필 불가) 문턱은 데드라인에서 도출(더 타이트):** `estimates`·`price_targets`·`grades_consensus`는 계약상 **30일 하드 데드라인**(다운스트림 적재 지연 > 30일 = 영구 유실)이 있다. 그래서 이들의 지연 문턱은 기대주기가 아니라 **데드라인에서 도출**한다 — `now - lastFetched > DEADLINE_DAYS × LEAD_FRACTION`(예: 30일 × 0.4 ≈ 12일). 21일에야 빨개지면 복구창이 ~9일뿐이라 늦다. 불변식 테스트: "§2 지연 문턱 < 30일 데드라인 − 충분한 리드타임".
- **주말만 완화(휴장은 미커버 — 정직히 축소):** 5분·일 주기(시장 데이터)는 `now`가 주말이면 지연 판정을 완화한다(토요일에 EOD가 오탐 안 나게). **미국 증시 평일 휴장(독립기념일·추수감사절 등)은 완화하지 않는다** — 그날은 시세 카드가 오탐할 수 있으나, 내부 도구라 휴일 캘린더까지는 두지 않는다(YAGNI). 뉴스(24/7)·주간 팩터는 완화 없음.

## 화면 2 — 종목 드릴다운

- 상단에 **검색창**. 유니버스(`index_members` 3개 지수 합집합, ~600)에서 심볼/이름으로 후보를 좁힌다. 후보 목록은 페이지 로드 시 `index_members` 3문서만 읽어 메모리에 둔다(추가 읽기 없음).
- 종목 선택 시 그 종목의 각 컬렉션 최신 값을 한 패널에:
  - `profiles/{symbol}` — 이름·섹터·산업·시총·현재가(1 doc get).
  - `ratios` 최신 — P/E·P/S·P/B·EV/EBITDA + 회계일.
  - `income`·`balance`·`cashflow` 최신 — 매출·순이익·총자산·잉여현금흐름 + 회계일.
  - `estimates` 최신 스냅샷 — 포워드 FY EPS·매출.
  - `price_targets` 최신 — consensus/high/low.
  - `grades_consensus`(또는 `grades_history`) 최신 — buy/hold/sell 카운트.
  - `prices_eod` 최근 — 최근 adjClose + 작은 스파크라인(최근 N개).
- 값은 "말이 되는지" 눈으로 확인하는 용도라 원값 그대로 표시한다(파생·계산 없음).
- **빈 결과(empty-state):** 방금 유니버스에 편입돼 아직 한 번도 수집 안 된 종목이나, 해당 컬렉션에 문서 0건이면 각 패널은 **"데이터 없음(미수집)"** 을 명시적으로 렌더한다 — '값 없음'과 '쿼리 오류'를 구분해 표시하고, 아무 신호 없는 빈 화면을 두지 않는다.

## 읽기 전략 · 인덱스 · 규칙

**바운드 쿼리 (추가 복합 인덱스 0개가 목표):**
- **상태 신선도** — 컬렉션당 `orderBy("fetched_at","desc").limit(1)`. `fetched_at`은 단일필드 자동 인덱스라 별도 설정 불필요.
- **드릴다운** — 문서 id가 `{symbol}__{YYYYMMDD}`(날짜 zero-pad, 사전순=시간순)라, **doc-id 범위 쿼리**로 종목별 최신 N건을 뽑는다. 내림차순 범위라 **상한 sentinel을 명시**해야 한다(둘 다 `symbol+"__"`로 두면 정확일치 문서가 없어 0건 — sentinel은 화면에 안 보이게 쓰지 말고 escape로 명시): `orderBy(documentId(),"desc").startAt(symbol + "__\\uf8ff").endAt(symbol + "__").limit(N)`. 여기서 `"\\uf8ff"`(높은 유니코드 sentinel)는 `symbol+"__"` 접두의 모든 날짜 문서보다 위에 오고(desc의 상한), `endAt`는 하한이다. `__` 구분자가 접두 충돌을 막는다(`_`=0x5F가 영숫자보다 커서 `AAPL__`로 시작하는 문서는 `AAP__` 범위 밖). 자동 doc-id 인덱스만 쓰므로 복합 인덱스가 필요 없다. 경계식은 `dashboard_logic.mjs`의 순수함수 `idRange(symbol)`로 뽑아 "상한 sentinel 없으면 빈 결과" 불변식을 테스트로 강제한다.
- `profiles`·`index_members`·`delisted`는 doc id가 `{symbol}`·`{index}`라 `doc(id).get()` 단건.
- **샘플**은 상태 카드용으로 컬렉션당 최신 1~2건이면 충분(전체 스캔 금지).
- `count()` 집계는 쓰지 않는다(대용량에서 read가 누적) — 신선도+유니버스 크기+샘플로 수집상황을 판단.

**`firestore.rules` 변경(2층 — 공개 + 인증 게이트):**
- **공개 유지:** `items`·`meta`·`prices`는 기존 공개 read 그대로. 공개 뉴스 리더 `index.html`이 읽고, RSS·시세 스냅샷이라 FMP 재배포 제약 밖이다.
- **인증+허용목록 게이트(FMP 데이터):** 팩터/스트림 컬렉션(`price_bars`·`prices_eod`·`income`·`balance`·`cashflow`·`ratios`·`market_cap`·`grades_history`·`profiles`·`estimates`·`price_targets`·`grades_consensus`·`index_members`·`index_changes`·`delisted`)은 `allow read: if request.auth != null && request.auth.token.email in get(/databases/$(db)/documents/config/allowlist).data.emails`. 허용목록에 오른 이메일로 로그인해야만 read. `config/allowlist` 자체는 클라이언트 read 금지(규칙 `get()`만 접근 — 이메일 PII 비노출).
- **레거시 `fundamentals` 규칙 제거**(컬렉션 폐기 — income/balance/cashflow가 대체).
- **write는 전부 금지**(Admin SDK만).
`firestore-contract.md`의 reader/공개read 항목도 이 2층 모델로 갱신한다(팩터=인증 게이트, 레거시 `fundamentals` 행 정리).

**인덱스:** 위 전략상 신규 복합 인덱스는 없다. `firestore.indexes.json`은 무변경. (단일필드·doc-id 자동 인덱스만 사용.)

## 테스트

기존 `tests/web/*.test.mjs`(node) 관행을 따른다 — 순수 로직만 검증(브라우저·Firestore 불요).
- `dashboard_logic.mjs`의 `isOverdue`(주기 인지·주말 완화·§2 데드라인 문턱), 상대시각 포맷, 카드 신선도(=가장 오래된 컬렉션) 도출, 드릴다운 `idRange(symbol)`(상·하한 sentinel), 유니버스 합집합·검색 필터.
- **불변식으로 검증**(매직넘버 금지):
  - "정상 주기 내면 지연 아님", "§1은 OVERDUE_FACTOR배 초과면 지연", "주말엔 시장데이터 지연 완화".
  - **빈 컬렉션 = 경보**: `isOverdue(null, …)` → 항상 경보(정상 아님) — TTL 만료/미수집이 '건강'으로 오탐 안 되게.
  - **§2 데드라인 리드타임**: §2(estimates·price_targets·grades_consensus) 지연 문턱 < 30일 데드라인이고, 남는 복구창이 충분함(예: 문턱 ≤ 데드라인의 절반).
  - **범위 sentinel**: `idRange(symbol)`의 상한이 하한보다 크고(상한 sentinel 존재), 인접 접두(`AAP` vs `AAPL`)를 안 물어들인다.

## 비기능 (항상)

- **비밀:** 새 비밀 없음. FMP_API_KEY는 백엔드 전용이라 이 페이지엔 안 온다. 웹 apiKey는 비밀 아님.
- **인증·접근:** Firebase Auth 구글 로그인은 무료 구간(월 수만 활성 인증까지 무료). `config/allowlist`는 이메일(PII)이라 클라이언트 read 금지 — 규칙 `get()`만 접근. 로그인 상태 유지·로그아웃 버튼 제공. 허용목록에서 이메일을 지우면 즉시 접근 취소(다음 규칙 평가부터).
- **비용:** 위 실측대로 무료 구간. `count()` 회피·바운드 쿼리로 유지.
- **드리프트 가드:** 카드 그룹핑·기대 주기 테이블은 `dashboard_logic.mjs` 한 곳(SSOT). 계약에 컬렉션이 늘면 이 테이블과 `firestore.rules` read 목록을 함께 늘린다(스펙에 명시).
- **스타일:** 기존 `index.html`의 다크 테마·카드 룩을 따른다(구현 시 frontend-design 참조).

## 미결·후속 (범위 밖 — 링크만)

- **티커 조인 키**(`firestore-contract.md` gotcha #3): 뉴스 items에 `tickers[]` + alias 사전 복원은 별도 소과제. 이 대시보드는 그것과 무관하게 동작한다(드릴다운은 팩터 컬렉션의 `symbol`로만 조인).
- PIT 시계열 재구성(유니버스 역산)은 다운스트림 몫 — 대시보드는 현재 구성 + 변경 로그만 보여준다.

<!-- 공개 read → Firebase Auth 이메일 허용목록 게이트로 전환(사용자 결정, escalate 해소). 인증 게이트는 리뷰어 선호 방향. -->
<!-- spec-review: passed -->


---

# 후속 설계(아침 검토 대기) — 공개-접근 전환

사용자 결정(2026-07-14): 대시보드 **최근 데이터를 누구나** 볼 수 있게(로그인 없이, 종목 드릴다운 포함). 앞서 만든 인증 게이트를 이 부분에서 뒤집는다. **다만 배포는 수동이라, 이 설계는 사용자 확인 후 구현·배포한다**(공개 노출은 비가역 — 캐시·크롤 회수 불가).

핵심 긴장: "최근 데이터 공개"는 좋으나, 게이트 컬렉션을 통째 공개하면 **10년 일봉·1년 5분봉·팩터 전량이 무인증 벌크 스크래이핑** 대상이 된다(FMP 재배포 최대 노출). "최근"만 공개하는 게 의도에 맞다.

## 두 방식

- **A. 블런트 공개(단순, 위험 큼):** `firestore.rules`의 게이트 컬렉션을 `allow read: if true`로. 대시보드 로그인 화면 제거. 구현 최소지만 **아카이브 전량 공개 스크래이핑** 노출.
- **B. 공개-최근 surface(권장):** 수집기가 컬렉션별 **최근 N개만 담은 공개 문서**(예: `recent/{key}` — 최근 며칠 값, **아카이브 없음**)를 발행. 규칙은 `recent/*`만 공개, 깊은 컬렉션은 게이트 유지. 대시보드 상태·드릴다운은 `recent/`를 로그인 없이 읽는다. → 누구나 최근 데이터를 보되, 10년 아카이브는 못 긁는다.

## B안 구현 스케치(확인 시)
- 수집기(run_prices·run_factors·run_intraday_backfill)가 심볼·컬렉션별 최신 N을 `recent/{collection}__{symbol}`(또는 `recent/{symbol}` 묶음)로 발행(비파괴, 작음).
- `firestore.rules`: `match /recent/{id} { allow read: if true; allow write: if false; }`. 게이트 컬렉션은 그대로.
- `web/dashboard.html`: 로그인 게이트 제거(또는 선택적), 상태 카드·드릴다운을 `recent/`에서 읽기. 깊은 조회가 필요하면 그때만 로그인.
- 무결성: `recent`도 `fetched_at` 유지, TTL(짧게) 가능.

**→ 아침에 A/B 중 택1(권장 B) 주시면 구현·검증·배포 절차를 진행한다.**
