# newsstore 본문 채우기 — 화이트리스트 한국 헤드라인 소스 body 인리치 — 설계

_작성: 2026-06-28 · 상태: 설계(승인) · 성격: 자기완결 기능(수집 레이어, newsstore 범위)_

## 1. 목표 / 범위 / 정책 근거
헤드라인만 들어오는 소스의 **기사 본문을 개별 기사 페이지 fetch로 채운다.** 우선 대상 = **한경(한국경제) 6개 피드**(`hankyung`·`hk_economy`·`hk_realestate`·`hk_it`·`hk_intl`·`hk_society`) — 전부 `body_mode: headline`, `source: 한국경제`. 2026-06-28 라이브 프로빙: 기사 페이지 `HTTP 200`, `.article-body`로 본문 ~2,300자 추출(인포맥스 동일 CMS). *(추출 수치는 단일 프로빙 증거 — 선택자/임계는 테스트 픽스처로 고정, §6.)*

**정책 근거(사용자 명시 승인 2026-06-28):** `operations.md`의 기존 "기사 페이지 스크래핑은 안 함"을 **오버라이드**한다 — 사용자가 "크롤링으로 소스 확보가 *메인*은 아니지만, **RSS + 주요 뉴스는 화이트리스트 기반 개별 기사 본문 fetch를 한다**(임팩트 뉴스일수록 풀본문이 완성도를 높임)"로 결정. operations.md의 *기술적 우려(Cloud Run IP 차단 등)는 유효* → **무차별이 아니라 도달성·추출이 실증된 소스만 화이트리스트**(한경)로 켜고, 바운드(상한·타임아웃·스로틀)로 IP-차단 위험을 억제하며, 배포 스모크로 RSS 수집까지 정상인지 확인 후 안 되면 롤백(§7). **operations.md 정책 줄은 본 작업에서 함께 갱신**(SSOT 드리프트 방지).

**범위 밖:** Investing(기사 403)·Bloomberg(본문 403)·FT(페이월)·Reuters/GN(리다이렉트) · 풀텍스트 외부서비스 · 선택자 config 파일화(소스 다수화 시) · 임팩트 기반 동적 본문(분석 레이어 = news-analytics 소관).

## 2. 확정된 결정
1. **수집기 인라인(A)**: `collect_once`의 피드별 루프 안, 파싱 직후·upsert 전.
2. **새 항목에만 fetch**(`store.filter_new_ids`, **신규 메서드**): 이미 저장된 기사 재-fetch 금지.
3. **바운드(리뷰 반영 — Job 타임아웃·rate-limit·IP차단 방지)**:
   - per-feed 상한 `MAX_FETCH_PER_FEED = 10`,
   - per-article 타임아웃 `ARTICLE_TIMEOUT_S = 6.0`(요청별 — 기본 90s 상속 금지),
   - 스로틀 `THROTTLE_S = 0.2`(fetch 사이),
   - **`follow_redirects=True`**(미지정 시 http→https 301→비-200→전 기능 무음 no-op).
4. **화이트리스트+선택자 = 모듈 상수** `BODY_SELECTORS = {"한국경제": ".article-body"}`(SSOT). 추가 소스 = 1줄+테스트.
5. **브라우저 UA 재사용**: `fetcher.DEFAULT_HEADERS`.
6. **폴백(비파괴)**: fetch 실패(비-200/타임아웃/예외)·선택자 미스·본문 과소(< `MIN_BODY_CHARS = 80`) → `it.body=""`(`it.title` 불변), 항목 ID와 함께 WARNING.
7. **드리프트 알람(리뷰 반영)**: per-pass **빈-본문 비율**이 `EMPTY_RATE_ALERT = 0.5` 초과면 **ERROR 로그**(선택자 깨짐 loud 감지). 정상은 INFO.

**알려진 v1 한계(명시):**
- **첫 fetch 실패/상한 초과 항목은 body=""로 저장 후 재시도 안 됨**(②+③ 상호작용). 한경은 대부분 200·정상 볼륨이라 영향 작음. 자가치유(저장된 빈-body 재fetch)는 후속 backfill(§8).
- **폴 겹침 레이스**(major①): 느린 런이 다음 런과 겹치면 같은 새 항목을 양쪽이 fetch할 수 있음 → **무해**(upsert 멱등으로 둘째는 스킵, 최악 1회 중복 fetch, 손상 없음). 별도 락 미도입(YAGNI).

## 3. 아키텍처 / 데이터 흐름
```
collect_once(client, store, feed):           # 기존 피드별 try/except 안
  res = fetch_feed(...); items = parse_feed(res.content, feed, now)
  items = enrich_bodies(client, store, items)        # ← 신규
  store.upsert_items(items)                            # 기존(이미 저장 id 스킵)

enrich_bodies(client, store, items):
  cand = [it for it in items if it.source in BODY_SELECTORS and not it.body]
  if not cand: return items
  new = set(store.filter_new_ids([it.id for it in cand]))         # 미저장만(batched)
  targets = [it for it in cand if it.id in new][:MAX_FETCH_PER_FEED]   # 상한
  empty = 0
  for it in targets:
      it.body = fetch_body(client, it.url, BODY_SELECTORS[it.source])  # "" on fail
      if not it.body: empty += 1
      sleep(THROTTLE_S)
  log_empty_rate(feed.feed_id, len(targets), empty)   # ≥EMPTY_RATE_ALERT → ERROR
  return items
```
- `RawItem` 가변(pydantic, frozen 아님) → `it.body=...` 직접. **`it.title`은 절대 미변경**(헤드라인 보존 = title 그대로, body만 채움/비움).
- 헤드라인 아닌 항목·화이트리스트 밖·이미 저장·상한 초과분은 **건드리지 않음**.

## 4. 컴포넌트
### 4.1 `src/newsstore/collect/body_fetch.py` (신규)
- 상수: `BODY_SELECTORS={"한국경제":".article-body"}`, `MIN_BODY_CHARS=80`, `MAX_FETCH_PER_FEED=10`, `ARTICLE_TIMEOUT_S=6.0`, `THROTTLE_S=0.2`, `EMPTY_RATE_ALERT=0.5`.
- `fetch_body(client, url, selector) -> str`:
  - `client.get(url, headers=DEFAULT_HEADERS, follow_redirects=True, timeout=ARTICLE_TIMEOUT_S)`; `status!=200` → `""`.
  - `BeautifulSoup(r.text,"lxml").select_one(selector)`; 없으면 `""`. `get_text(" ",strip=True)`+공백정규화; `len<MIN_BODY_CHARS` → `""`.
  - **모든 예외 잡아 `""` 반환(절대 raise 안 함)**.
- `enrich_bodies(client, store, items) -> list[RawItem]`: §3 로직(상한·스로틀·집계로그·항목별 격리).
- 의존: `httpx`·`bs4`(둘 다 기존), `fetcher.DEFAULT_HEADERS`, `time.sleep`.
### 4.2 Store 계약 — **신규 메서드** `filter_new_ids`
- `contracts/ports.py` `Store`에 `filter_new_ids(ids: list[str]) -> list[str]`(미저장 id만) 추가.
- `store/firestore_store.py` 구현: 후보 id 존재확인 → 미존재만 반환. **`get_all`(batched)로 1라운드트립**(upsert와의 읽기 중복 비용 최소화 — 리뷰 반영). `upsert_items`와 *판정 기준은 같으나 별도 메서드*(reuse 아님 — 문구 정정). 에뮬레이터 계약 테스트.
### 4.3 `collect/collector.py` 배선
- 상단 `from .body_fetch import enrich_bodies` **import 추가**. `collect_once`에서 `parse_feed(...)` 다음 줄에 `items = enrich_bodies(client, store, items)`. 기존 피드별 try/except가 본문 단계도 격리.

## 5. 에러처리 / Fail-loud
- `fetch_body` 예외 전파 안 함 → `""`(헤드라인 보존, title 불변). 항목 ID를 WARNING에.
- **집계 신호(§2.7)**: per-pass 빈-본문 비율 ≥`EMPTY_RATE_ALERT` → **ERROR**(드리프트 loud). 개별 실패 WARNING.
- 상한·타임아웃·스로틀로 Job 타임아웃·rate-limit·NAT IP 차단(→RSS 수집 마비) 위험 차단.
- `collect_once` 피드별 try/except 최후 격리.

## 6. 테스트 (TDD, Docker 전용; 라이브 네트워크 없음)
- **`tests/test_body_fetch.py`**:
  - 추출: `.article-body` 샘플 HTML→기대 본문; 선택자 없음/과소(<80)→`""`; **광고·구독유도 블록이 `.article-body` 밖인 픽스처로 본문만 잡힘**.
  - `httpx.MockTransport`: 비-200→`""`; **301→follow하여 최종 200 본문**(follow_redirects 회귀 가드); 예외→`""`; 타임아웃 인자 전달.
  - `enrich_bodies`: 화이트리스트 밖 미변경·`it.title` 불변; 이미 저장(mock `filter_new_ids`) 미fetch; 신규>상한이면 **정확히 `MAX_FETCH_PER_FEED`건만**; 빈-본문 비율≥임계 시 ERROR(caplog).
- **`tests/test_collector.py` 확장**: mock client RSS+기사 HTML → `collect_once` 후 한경 새 항목 body 채워짐, 비-화이트리스트 그대로.
- **Store 계약(에뮬레이터)**: `filter_new_ids`가 미저장 id만(batched).
- 불변식 **FAIL=0**. `MSYS_NO_PATHCONV=1 docker compose run --rm test`.

## 7. 배포
수집기 코드 변경 → `operations.md §A`(재빌드→Job 갱신→실행). **배포 스모크(사용자 게이트)**: 1패스 후 한경 항목 body 채워졌는지 + 빈-본문 비율 로그 + **RSS 수집까지 정상**인지 확인(IP 차단 안 됐는지). 안 되면 롤백. Job 실행시간 = 최악 상한10×6피드×(6s+0.2s) ≈ 6분 < 기본 타임아웃 10분(여유 확인).

## 8. 범위 밖 / 후속
- 비한국 헤드라인 소스(차단·리다이렉트) 본문.
- **자가치유 backfill**: 저장된 빈-body 한경 항목 재-fetch(첫 실패/상한초과 복구) — 별도 패스.
- 인포맥스 풀본문 업그레이드(선택, 동일 `.article-body`) · 화이트리스트 확장(매경 등 도달 실증 시).
- 임팩트 기반 동적 풀본문(분석 레이어 = news-analytics 소관).

<!-- spec-review: passed lenses=3 date=2026-06-28 note=정책 오버라이드 사용자 명시 승인(2026-06-28); review criticals(operations.md framing·unbounded fetch)+majors(redirects·drift alert·timeout·race·dup-reads) 전부 반영; prior escalated 해소 -->
