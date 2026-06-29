# Phase 2 — 델타 모델: 2-타임스탬프 + milestone 판정 (설계 spec)

_작성: 2026-06-29 · 상태: 설계(spec) · 소유: newsstore · 상위 SSOT: `docs/analysis-design.md` §6_

> 이 spec은 `docs/analysis-design.md` §6(델타 모델)의 **Phase 2 구현 설계**다. 설계 결정의 상위 근거는 analysis-design이 SSOT이고, 본 문서는 *그것을 어떻게 코드로 옮기는가*를 확정한다. 스키마 계약은 `docs/firestore-contract.md`와 동기화한다.

## 1. 목표 (무엇을·왜)
요약 패스가 산출하는 각 development(전개)에 **두 번째 타임스탬프 `delta_time`** 을 부여하고, **새 기사가 기존 스토리의 알려진 전개를 단지 재탕(recap)하는 경우 새 델타로 올리지 않도록** LLM milestone 게이트를 끼운다.

- **문제**: 발행시각(`published_at`)만 믿으면, 오늘 발행됐지만 옛 사건을 다시 꺼내는 기사가 *새 일*처럼 타임라인 상단에 올라온다(§6). 재요약 모델에서는 원본 기사가 피드 창에서 밀려난 뒤 recap이 들어오면 요약기가 그 전개를 *새 전개*처럼 다시 만들 수 있다.
- **해법**: development마다 "우리 스토어에 새 정보로 처음 편입된 시각"을 뜻하는 `delta_time`을 둔다. 진짜 새 전개는 자기 발행시각으로, recap은 기존 프런티어로 귀속시켜 *새 델타를 만들지 않는다*.

**비목표(범위 밖, §13)**: 본문에서 진짜 역사적 이벤트 날짜를 추출하는 것(LLM 환각 위험 — 후순위). risk/impact 점수(Phase 3). UI 렌더(Phase 4).

## 2. 핵심 설계 결정

> **참고(prospective)**: 본 절이 기술하는 `delta_time` 필드·`is_new` 신호·`assign_delta_times`·`milestone.py`·시그니처 변경은 **Phase 2에서 신규로 추가**되는 것이며 현재 코드에는 없다(spec = 미래 청사진). §3은 현 코드 대비 *추가/변경분*이다.

### 2.1 `delta_time` 의미와 기본값 (grounding)
| 필드 | 의미 | 출처 |
|---|---|---|
| `time` (기존) | 그 전개를 **처음 보도한 기사의 발행시각** (`first_idx` 기사의 `published_at`) | 기사 원본 |
| `delta_time` (신규) | 그 전개가 **우리 스토어에 새 정보로 처음 편입된 시각** | 코드가 도출 |

- **기본값(진짜 새 전개) = 그 전개의 `time`.** grounding: 항상 실제 기사 발행시각이라 환각 불가. `time`은 `first_idx` 기사에서 매 패스 새로 도출되는데, **원본 기사가 피드 창에 남아 있는 한 같은 전개는 같은 `first_idx`→같은 `published_at`→같은 `time`** → `delta_time=time`이 재요약에 흔들리지 않음(안정성이 grounding에서 공짜로 따라옴, 별도 carry-forward 불필요). 원본이 창에서 밀려나면 `time`을 완벽 보존할 수 없는데, 그때가 바로 milestone 게이트(recap 검출)가 *새 일처럼 올라오는 것*을 막는 지점이다. 완벽 보존은 per-development 안정 id 영속이 필요해 §6이 명시적으로 피한 "별도 구조 신설"이라 Phase 2 범위 밖(근사 허용).
- **legacy 폴백 + 멱등 백필**: `delta_time` 없는 구 development은 UI/소비자가 `time`으로 폴백(§6 마이그레이션). 별도 "phase2 완료" 플래그 없이, **성공한 요약마다 `delta_time` 누락이면 `time`으로 재계산**(idempotent backfill) → 첫 재요약에 자동 백필(additive·비파괴).

### 2.2 milestone 게이트 (LLM, recap → 새 델타 비생성)
- **요약 패스에 통합(별도 콜·별도 모드 없음)**: §6 "기존 요약 패스 재활용" + §7 "LLM 1콜". 기존 스토리에 **이미 알려진 전개(prior developments)** 가 있을 때만, build_summary_prompt에 "이미 알려진 전개" 섹션을 추가하고 각 development에 `is_new`(이 전개가 알려진 전개의 재탕이 아니라 진짜 새 전개인가) 불리언을 함께 출력하도록 요청한다. → **추가 LLM 콜 0**(요약 콜에 편승).
- **프롬프트 비대화 방지(bound)**: prior 섹션엔 prior development **텍스트만**, **최신순 상한 `MILESTONE_PRIOR_MAX`(상수, 기본 12)** 까지만 먹인다(토큰 통제). 지시문은 간결히. **prior 없는 경로는 기존 프롬프트와 100% 동일**(하위호환 — 기존 first_idx/source_count 품질 회귀 테스트가 보호).
- **결정론 validator**: `is_new`는 development dict의 키. 값이 정확히 bool `True`가 아니면(누락·null·비-bool 포함) **보수적 기본 = recap**으로 취급. (§6 "불확실 시 보수적: 새 델타 비생성".)
- **delta_time 배정(순수·결정론, `assign_delta_times`)** — carry-forward 없이 2분기:
  - `prior_frontier` = prior developments의 `delta_time` 중 **max**(없거나 모두 None이면 `None`).
  - **`is_new == True` 또는 `prior_frontier is None`** → `delta_time = time`(진짜 새 전개, 또는 비교할 프런티어가 없음=첫 요약/legacy → 발행시각에 grounding).
  - **그 외(recap이고 프런티어 존재)** → `delta_time = prior_frontier`. recap은 프런티어를 전진시키지 않음 = 새 델타 비생성. grounding: 실제로 저장됐던 prior 값.
- **recap development은 드롭하지 않고 보존**(비파괴) — 요약문의 유효한 한 줄로 남되 `delta_time`이 프런티어라 *새 milestone으로 앞서지 않는다*. (§6 "기존에 귀속, 피드엔 잔류"의 development-레벨 해석.)
- **프런티어 근사 한계(명시·🔴)**: 모든 recap을 `max(prior delta_time)`으로 귀속하므로, *옛 전개*만 되짚는 recap도 최신 프런티어에 붙는다(정밀 귀속 아님). 트레이드오프: "새 일로 앞서지 않게"라는 목표는 만족(프런티어를 안 넘김), 정밀 시점 귀속은 포기. §7.1에서 정밀 매핑 대안과 함께 사용자 결정.

### 2.3 Fail-soft 2단계 (코드베이스 관습 일치 — 모순 해소)
- **콜 전체 실패/검증 None**: 기존 `summarize_story`가 `None` 반환 → 그 스토리 **전체 스킵**(아무것도 안 씀, 기존 동작 그대로). developments도 delta_time도 미기록 → **타임라인 stall 없음**(이전 저장본 유지), 다음 런 재시도. 패스 안 죽임.
- **per-item 모호(콜 성공, 특정 항목 `is_new` 누락)**: 그 항목만 보수적 recap. **단 recap 강등은 `prior_frontier`가 존재할 때만** delta_time을 프런티어로 내린다. **프런티어가 없으면(첫 요약/legacy) → `time`** (새 전개로 포함). → "is_new 전부 누락 + prior 없음"이 모두 recap이 돼 **타임라인이 영영 안 나아가는 파국을 구조적으로 차단**(no-prior는 항상 time).
- **비파괴·원자성(명시)**: 성공한 요약 1회는 developments 리스트 전체를 **한 번의 merge set**으로 쓰므로, 그 안의 모든 development가 delta_time을 갖는다(write 내 부분 누락 없음). delta_time의 *부재*는 오직 legacy(Phase 2 전) 또는 미실행 스토리뿐이고 폴백(=time)이 안전하게 처리 → "additive(부재가 안전)"와 모순 없음.

## 3. 영향 받는 구성요소 (작은 단위로)

### 3.1 `src/newsstore/enrich/summarizer.py`
- `build_summary_prompt(members, *, omitted=0, prior_developments=None)` — prior 있을 때만 "이미 알려진 전개" 섹션 + `is_new` 요청 추가(없으면 기존 프롬프트 그대로 = 하위호환).
- `validate_summary(raw, *, n_members)` — development별 `is_new` 통과(값이 `True`가 아니면 `False`로 정규화 = 보수적 recap). 기존 키 유지.
- `summarize_story(members_all, client, *, now, prior_developments=None, max_members=...)` — `assign_delta_times` 호출해 출력 development에 `delta_time` 추가. 정렬은 기존대로 `time` DESC 유지(UI 안정), `delta_time`은 데이터 필드.
- `run_summary_pass(...)` — store에서 prior developments를 받아 `summarize_story`에 전달.

### 3.2 `src/newsstore/enrich/milestone.py` (신규, 순수 로직)
- `MILESTONE_PRIOR_MAX = 12` — prior development을 milestone 프롬프트에 먹이는 상한(상수, 토큰 통제. 매직넘버 금지 — 명명 상수).
- `assign_delta_times(developments, *, prior_developments) -> list[dict]` — 2.2의 결정론 배정. 입력 development은 `{text,time,source_count,is_new}`, 출력은 `is_new` 제거 + `delta_time` 추가. carry-forward 없음(2.2). 단위 테스트가 쉬운 순수 함수(LLM·store 의존 없음).
- `prior_texts(prior_developments) -> list[str]` (선택) — 프롬프트용 prior 텍스트 추출(최신순 `MILESTONE_PRIOR_MAX`개). build_summary_prompt가 사용.
- 작은 단위 분리 이유: 요약기의 잘 검증된 코어를 건드리지 않고 milestone 배정 로직을 독립 테스트.

### 3.3 store (`firestore_store.py` + `ports.py` + `firestore-contract.md`)
- `get_stories_needing_summary(limit)` 반환에 **`developments`(prior)** 추가(additive 키). 이미 story 문서를 읽으므로 **추가 read 없음**.
- `save_story_summary(...)` — developments 리스트를 그대로 저장(각 dict에 `delta_time` 포함). merge=True 유지(비파괴). 시그니처 불변.
- `ports.Store` Protocol·`firestore-contract.md §stories` 갱신(`developments[].delta_time`, `get_stories_needing_summary` 반환 형태).

## 4. 데이터 흐름
```
run_summary_pass
  └ get_stories_needing_summary → [{id, count, developments(prior)}]
      └ get_story_members(id) → members(published_at asc)
          └ summarize_story(members, client, prior_developments=prior)
              ├ build_summary_prompt(members, prior_developments=prior)  # prior 있으면 is_new 요청
              ├ client.generate_json → validate_summary  # is_new 통과
              ├ time 도출(기존: first_idx.published_at)
              └ assign_delta_times(devs, prior_developments=prior)  # delta_time 배정
          └ save_story_summary(... developments=[{text,time,delta_time,source_count}] ...)
```

## 5. 테스트 전략 (TDD, 실패 먼저)
- **순수 단위 (`tests/test_milestone.py`, fake 없이)**:
  - 첫 요약(prior 없음) → 모든 `delta_time == time`.
  - `is_new=True` 새 전개(prior 존재) → `delta_time == time`.
  - `is_new=False` recap + prior 존재 → `delta_time == max(prior delta_time)`(프런티어, 새 델타 비생성 불변식).
  - **프런티어 근사(🔴)**: recap이 옛 전개만 되짚어도 프런티어로 귀속됨을 명시 테스트(근사 수용 — 프런티어를 넘지 않음 불변식).
  - legacy prior(`delta_time` 없음, 모두 None) → `prior_frontier is None` → 모든 `delta_time=time` 백필.
  - `is_new` 누락/null/비-bool → 보수적 recap(프런티어 존재 시 frontier, 없으면 time).
  - **stall 방지 불변식**: prior 없는데 `is_new` 전부 누락 → 모두 `time`(타임라인 전진).
- **summarizer 단위 (`tests/test_summarizer.py` 확장, FakeLLM)**:
  - prior 전달 시 프롬프트에 "이미 알려진 전개" + `is_new` 요청 포함; prior 없으면 미포함(하위호환).
  - `validate_summary`가 `is_new` 통과/기본값.
  - `summarize_story` 출력 development에 `delta_time` 존재 + 위 불변식.
  - 기존 테스트 전부 green 유지(정렬·latest·summary_count·None 가드).
- **store 계약 (`tests/test_store_summary.py` 확장, 에뮬레이터)**:
  - `get_stories_needing_summary`가 prior `developments` 반환.
  - `save_story_summary`가 `delta_time` 포함 development 저장 + 기존 필드 비파괴.
- **검증**: `MSYS_NO_PATHCONV=1 docker compose run --rm test` FAIL=0, 증거 후 주장.

## 6. 비파괴·계약 불변식 (Fail-Loud)
- `delta_time`은 **additive 필드**. 구 데이터·구 UI 안 깨짐(폴백=`time`).
- `save_story_summary`는 merge=True로 cluster 소유 필드(member_ids/centroid_sum/count) 보존.
- `delta_time` 값은 **항상 grounding된 실제 시각**(전개 `time` 또는 저장됐던 prior delta_time) — 코드가 임의 시각을 만들지 않음.

## 7. 🔴 사용자 결정 필요 (메인이 검토)
1. **recap의 delta_time = `max(prior delta_time)`(프런티어)** 로 귀속하는 선택. 대안: (a) milestone LLM이 "recap-of-j"로 특정 prior를 가리키게 해 그 prior의 delta_time을 정확히 상속(더 정밀, 프롬프트·validator 복잡↑), (b) recap development을 아예 드롭(정보 손실). 현 선택은 단순·보수·grounding 우선. 정밀 매핑이 필요하면 (a)로 승격.
2. **milestone을 요약 콜에 편승(현 선택)** vs **별도 콜**. 편승은 추가 콜 0(비용↓, §7 "1콜")이나 요약 프롬프트가 커짐. 별도 콜은 관심사 분리가 깨끗하나 재요약 스토리마다 +1콜($3/일 예산 영향). 현 선택은 비용·analysis-design 정합 우선.
3. **degrade 시맨틱**: 콜 전체 실패는 스토리 스킵(milestone 미적용, delta_time 미기록 → 다음 런 재시도). per-item 모호만 보수적 recap(프런티어 존재 시). "콜 실패 시에도 무조건 보수 suppress"는 택하지 않음(grounding·fail-soft 관습 우선).

---
_spec-review(2026-06-29, 3렌즈): grounding·consistency의 "코드 미존재" 지적은 spec 본질(미래 청사진)이라 비결함 처리. adversarial 실질 지적 반영 — 시간-앵커 carry-forward 제거(중복·충돌 위험), fail-soft 모순 해소(no-prior는 항상 time → stall 방지), 원자성 명시, 멱등 백필, 프롬프트 bound(MILESTONE_PRIOR_MAX). 프런티어 근사·편승 vs 별도콜은 §7 🔴로 사용자 결정 잔존._

<!-- spec-review: passed lenses=3 date=2026-06-29 -->
