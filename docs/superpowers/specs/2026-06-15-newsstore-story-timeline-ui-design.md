# newsstore 스토리 타임라인 UI + 스토리 요약 — 설계

> ⚠️ **부분 분할 (2026-06-28):** **백엔드 스토리 요약 패스는 `news-analytics` 소유**(경계·계약: **`docs/firestore-contract.md`**). **스토리 타임라인 UI(`web/index.html`)만 newsstore에 유효** — UI는 `stories`/`tags`를 Firestore에서 읽는 소비자다(Fail-soft 가드 필요).

_작성: 2026-06-15 · 상태: 설계(검토중) · Visual Companion으로 인터랙션 확정(목업 `.superpowers/brainstorm/.../content/`)_

## 1. 목표 / 범위
백엔드에 이미 쌓인 **스토리(centroid 클러스터)**를 사이트에서 **내러티브 타임라인**으로 보여준다. 핵심 인터랙션: 가로 스토리 카드 스트립 → 하나를 펼치면 그 스토리의 **전개(development) 타임라인 + 실제 기사 카드들**.

이 설계 문서는 **두 독립 서브시스템**을 묶는다. 백엔드가 먼저 요약 필드를 채워야 프론트가 읽을 게 생기므로 **구현은 별도 2개 플랜으로 분리**(공유 상태는 stories 문서 필드뿐 — 계약만 맞추면 독립 진행/배포 가능):
- **플랜 A — 백엔드 요약 패스(선행):** §3 신규 Store 계약 + §5 summary 패스 + §6 스케줄러. 에뮬레이터/라이브 스모크로 검증.
- **플랜 B — 프론트 스토리 뷰(후행):** §4 탭 토글 + 스트립 + 펼침 디테일. A가 채운 필드를 읽음. 눈 검증(`run`/`verify`).
- **범위 밖:** 중요도(importance) 랭킹(보류 — 로직 필요), 모바일 전용 레이아웃 정밀화(반응형 기본만), Pass-2 아이템 태깅(폐기 — §6 참조), 요약 내용-정합성 자동검증(후속 advisor-correctness — §8).

## 2. 확정된 결정 (대화로)
- **배치:** 기존 사이트에 **탭 토글 (피드 | 스토리)**. 평면 피드는 그대로 유지.
- **스토리 카드:** **멤버 2+ 스토리만**, **최신 ~15~20개**(last_seen 내림차순, 왼쪽=최신). 중요도 랭킹 보류.
- **스크롤:** 가로. **휠→가로 매핑** + **‹ › 화살표** + 모바일 터치 스와이프.
- **펼침:** 카드 호버 → 부드럽게 확대 + **오른쪽 스토리 카드를 밀어** 공간 확보 + 디테일 표시(부드러운 transition).
- **디테일 레이아웃:** **[왼쪽 슬림 세로 타임라인(전개) | 오른쪽 기사 카드]**. 기사 카드는 **여러 장 겹친 스택(~600~900px)**, 전개당 대표 **≤2장 + "+N개 더"**. 전개는 위=최신(맥동 강조).
- **요약 모델/주기:** **gemini-3.1-flash-lite-preview**(코드 GeminiClient 기본값과 일치), **1시간 스케줄러**, **새 멤버 생긴 스토리만**(최신 ~30 중).
- **델타(latest)·dedup:** "최근창 재독 + 의미 dedup"(naive 증분 폐기). `latest` = 가장 최근의 진짜 *전개*(뒤따르는 반복은 무시).

## 3. 데이터 / 스키마 (기존으로 충분)
현 컬렉션 그대로 + 스토리에 요약 필드만 추가:
- **`items`**(기존): raw + `embedding`·`story_id`·`published_at`·`source`·`title`·`body`·`tags`. 변경 없음.
- **`stories`**(필드 추가):
  ```
  기존: title, centroid_sum, count, member_ids[], entities[], first_seen, last_seen, status
  추가: summary(str), latest(str),
        developments(array<{text, time(ISO ts, 그 전개를 처음 연 기사의 published_at), source_count(int)}>),
        summary_count(int, 요약 만든 시점에 *실제로 읽은* 멤버 수 스냅샷), summary_at(ts),
        title(LLM 캐노니컬로 갱신 — 초기 1번째 기사 제목을 덮어씀. validator가 비어있음·길이만 보증)
  ```
  - **`time`은 상대문자열이 아니라 절대 타임스탬프**(저장 후 시간이 흘러도 안 썩음). UI가 "N시간 전"으로 렌더.
- **신규 Store 계약(contracts/ports.py `Store`에 추가):**
  - `save_story_summary(story_id, title, summary, latest, developments, summary_count, now)` → merge 업데이트.
  - `get_stories_needing_summary(limit)` → 최신 `last_seen` 중 `count > summary_count`인 스토리(대상 선정). 부등호 제약은 §4·§5 참조(코드측 필터).
  - 둘 다 에뮬레이터 테스트로 계약 검증.
- **인덱스(이미 선언/READY):** `items(story_id ASC, published_at ASC)`(스토리의 기사 조회), `stories(status, last_seen DESC)`(스트립 정렬). `firestore.indexes.json` SSOT + 계약 가드 테스트.
- **규칙:** `stories` 공개 read 이미 배포됨(Phase D). 브라우저가 `stories` + `items where story_id==X` 직접 읽음.

## 4. 프론트 (web/index.html — 탭 + 스토리 뷰)
- **탭 토글**: 헤더에 `피드 | 스토리`. 기존 피드 코드 유지, 스토리 뷰 추가(같은 파일 또는 `web/stories.js` 분리 — 파일 비대화 시 분리).
- **스토리 스트립**: `stories where status=='open' order by last_seen desc limit ~40` 한 쿼리(인덱스 `stories(status,last_seen)` 그대로) → **`count>=2`는 클라이언트에서 필터**(상위 ~20 취함). *Firestore는 한 필드 부등호 + 다른 필드 order_by를 한 쿼리에서 못 하므로*(부등호·정렬 충돌, factual 렌즈 지적) 별도 인덱스 추가 대신 코드측 필터로 간다(YAGNI). 카드 = 캐노니컬 title + summary(2~3줄) + `🔵 최신: {latest}`(있을 때) + 건수 + 토픽(있으면) + 소스 다양성 색점(멤버들의 source 색). 색 = 기존 `srcColors`(소스명 해시 기반 — `meta/sources` 순서와 무관한 결정적 해시라 별도 SSOT 불필요).
- **스크롤**: `overflow-x:auto` + `wheel`(deltaY→scrollLeft) + ‹ › 버튼.
- **호버 펼침(단일 메커니즘으로 확정):** 카드 호버(~120ms 딜레이로 스침 방지) → 호버 카드가 부드럽게 확대되고 **오른쪽 스토리 카드들을 한 칸 옆으로 밀어** 생긴 공간에 디테일을 인라인 표시(아래로 떨어뜨리지 않음). CSS transition ~.3s. **호버가 모바일/트랙패드에서 취약하면 클릭 토글로 폴백**(구현 시 한 메커니즘만 선택, 둘 다 노출 금지).
- **디테일**: 선택 스토리의 `items where story_id==X order by published_at`를 읽어 → **전개별 그룹핑** → 왼쪽 슬림 세로 타임라인(developments, 위=최신) + 오른쪽 기사 카드 겹친 스택(~600~900px, 전개당 ≤2 + "+N개 더"로 펼침). 기사 카드 = 기존 피드 카드 스타일(소스색·제목링크·발췌·소스칩·시간).
- **전개↔기사 매핑 규칙(명시):** developments는 article id를 갖지 않는다(토큰 절약). 프론트가 각 기사를 **그 published_at 이하(≤)이면서 가장 가까운 develop​ment.time**의 전개로 버킷팅(다음 전개 time 전까지가 그 전개의 구간). 가장 이른 전개보다 더 과거 기사는 가장 이른 전개에 귀속. 근사 매핑임(완전 정확 원하면 후속에서 LLM 출력에 멤버 인덱스 포함 — v1 범위 밖).
- **dedup 2종**: ① 뷰 기사중복(제목 정규화, 기존) ② 표시 상한(전개당 ≤2).

## 5. 백엔드 — 스토리 요약 패스 (`enrich`)
- **엔트리:** `run_enrich --mode summary`(신규 — 현재 run_enrich는 `cluster|tag`만, `tag`는 폐기되고 `summary`로 대체). 별도 1시간 Scheduler가 트리거(아래 비용 참조).
- **대상 선정:** `get_stories_needing_summary(limit)` — 최신 `last_seen` 중 **`count > summary_count`**(새 멤버 생긴 것)만(코드측 필터, §4와 동일 이유). 변화 없으면 스킵. 런당 상한(예: 10).
- **입력(절단 금지):** 해당 스토리의 **전체 멤버 기사**(published_at asc)를 제목 + 본문 발췌로 넣되, **토큰 상한에 맞춰 발췌 길이를 줄여** 전부 담는다(예: 멤버 많으면 제목+80자, 적으면 +200자). *최근 15건만 넣으면 developments 타임라인이 옛 전개를 조용히 잘라먹음*(adversarial 렌즈 지적) → 전체를 보되 길이로 비용 통제. 너무 큰 스토리(예 >120멤버)는 상한 + "(외 N건 생략)" 표기.
- **모델:** `gemini-3.1-flash-lite-preview`(기존 `GeminiClient` 래퍼 — timeout/retry/None가드/비용상한). 코드 기본 모델 상수와 일치 유지(드리프트 시 라이브 스모크가 잡음).
- **프롬프트(요지):**
  - system: "한국어 금융 뉴스 스토리 추적 에디터. 시간순 기사로 전체 흐름+현재 상황 요약. 최근 가중. 사실만, 추측·출처 밖 내용 금지."
  - user: 위 입력(각 기사에 번호 부여) + "기사를 전개(development) 단위로 묶어라(출처 달라도 실질 같으면 한 전개). 각 전개의 first_idx=그 전개를 처음 보도한 기사 번호. 아래 JSON만."
  - 출력 JSON(LLM): `{ "title": "캐노니컬(≤40자)", "summary": "2~3문장, 최근가중", "developments": [{"text":"전개 1줄","first_idx":N,"source_count":M}, ...] }`
  - **`time`·`latest`는 LLM이 만들지 않고 코드가 도출**(플랜 A D1/D2): `time = members[first_idx].published_at`(절대 ts), `latest = time 내림차순 정렬 후 첫 전개.text`. LLM이 ISO 시각·latest를 지어내지 않게 해 §3 스키마(time=ISO)와 일치시킨다.
- **검증(disciplined-coder advisor-fit):** 코드 validator 먼저 — JSON 파싱·필수 키·title 길이·developments 배열. 실패 시 재시도(generate_json 내장). critical(파싱불가)은 스킵+로그(해당 스토리 요약 보류, 다음 런 재시도).
- **저장:** `save_story_summary(story_id, title, summary, latest, developments, summary_count, now)` → stories 문서 **필드 한정 merge**(member_ids·centroid 등 cluster 패스 소유 필드는 건드리지 않음 → 비파괴·동시쓰기 안전) + `summary_at = now`. **`summary_count`는 "이번에 실제로 읽은 멤버 수" 스냅샷을 넘긴다**(현재 count를 새로 읽지 않음). 그래야 cluster 패스가 사이에 멤버를 더해도 다음 런이 `count > summary_count`로 재요약(silent skip 방지, adversarial 렌즈 레이스 지적). (에뮬레이터 테스트.)
- **태깅 폐기/흡수:** 별도 아이템/스토리 태깅 패스는 제거. 토픽이 필요하면 위 요약 콜에 `topics`를 한 필드 더 받아 흡수(선택).

## 6. 인리치 파이프라인 최종형
```
cluster pass (10분, 기존):  get_unprocessed → classify → embed(병렬) → VectorIndex 클러스터 → save_enrichment + mark
summary pass (1시간, 신규): 최신30·새멤버만 → 최근창 재독 → flash-lite 1콜 → title/summary/latest/developments → save_story_summary
```
- 각 스토리당 요약 콜은 "처음 카드로 뜰 때 1회 + 크게 자랄 때만"이라 LLM 비용 묶임.
- **인프라 비용/배포:** 새 잡을 만들지 않고 **기존 enricher 이미지를 그대로** 쓰되 **별도 Cloud Scheduler(1시간) → 같은 Cloud Run Job을 `--args=--mode=summary`로 트리거**. 시간당 실행(720/월)은 10분 cluster(4320/월)보다 *드물어* 증분 비용 작음(분 단위 과금 ~월 $1~2 수준 추정 — 배포 후 콘솔 실측으로 확인). Scheduler는 무료 3개 한도 내(현재 1개 사용). **operations.md에 요약 스케줄러 생성/갱신 절차를 추가**(현재 enrich-10min만 문서화됨).

## 7. 테스트 / 견고성
- **순수 로직:** 요약 입력 빌더(최근창 선택·시간 라벨), JSON validator, 전개 그룹핑(시간근접) → DB 없이 단위테스트.
- **store:** `save_story_summary` + 대상 선정 쿼리 → 에뮬레이터.
- **LLM:** 실 flash-lite 라이브 스모크(소량) — 모델명·JSON 출력·한국어 품질 확인(검증 후 주장).
- **프론트:** `run`/`verify`로 실제 사이트 띄워 인터랙션 눈 검증(가로 스크롤·호버 펼침·타임라인). 단위테스트 아님.

## 8. 리스크 / 오픈
- **요약 환각/사실오류(금융 뉴스라 무게 둠)** — flash-lite가 출처 밖 내용 생성 가능 → 코드 validator는 형식만 잡음. **v1 완화(능동적):** ① "사실만, 출처 밖·추측 금지" 프롬프트 ② summary/latest/전개를 **항상 출처 기사 카드와 함께** 노출(사용자가 즉시 대조 가능 — 요약이 1차 진입점이되 검증 경로가 한 화면에) ③ 본문 발췌를 입력으로 줘 grounding. **수용 리스크 명시:** 내용-정합성 자동검증(핵심 엔티티/숫자/날짜를 출처와 대조)은 **후속 advisor-correctness 레이어**로 미룸 — v1은 위 완화로 출시하되, 사용자가 투자판단 시 출처 기사 확인을 전제. 고위험 신호(오정보 보고) 발생 시 우선순위 상향.
- **전개 타임라인 절단(해소)** — §5에서 **전체 멤버를 입력**(발췌 길이로 비용 통제)하므로 developments가 옛 전개까지 포함. "최근 15건만" 안이 야기하던 silent 절단 제거.
- **전개↔기사 매핑** — §4 규칙(published_at ≤ 가장 가까운 development.time 버킷)으로 근사. 완전 정확은 후속(LLM 출력에 멤버 인덱스).
- **동시쓰기 레이스** — cluster 패스(member_ids/count)와 summary 패스(요약 필드/summary_count)가 **서로 다른 필드만** merge → 필드 클로버 없음. summary_count 스냅샷(§5)으로 skip-누락도 방지.
- **호버 vs 스크롤 충돌** — §4에서 단일 메커니즘(호버+딜레이, 폴백 클릭)으로 확정. 겹친 스택(~600~900px)은 v1 타깃이되, 구현서 호버가 취약하면 클릭 토글로 전환(YAGNI: 더 단순한 폴백을 명시해 둠).
- **모바일** — 호버 없음 → 탭으로 펼침. 가로 스트립은 터치 스와이프.

## 9. 연결
- 백엔드 토대: 2026-06-14 리스트럭처(contracts/enrich/store, VectorIndex, Cloud Run 인리치). 스토리 데이터 라이브.
- 후속(별도): 중요도 랭킹, advisor-correctness 요약 정합성 리뷰(고위험 시).

---
_리뷰 이력: 3렌즈 독립 리뷰(factual/consistency/adversarial)가 각각 단독 critical 검출 → regenerate 1회로 §1~§6,§8 반영(모델명 -preview, 신규 Store 계약 명시, strip 부등호→클라이언트 필터, 인터랙션 단일화, 전개 입력 절단 해소, 비용/스케줄러 명확화, 환각 v1 완화). 잔존 critical 0._

<!-- spec-review: passed lenses=3 date=2026-06-15 -->
