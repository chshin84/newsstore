# 플랜 A — 스토리 요약 패스 (백엔드) · 구현 계획

> 🔀 **DEPRECATED (분할 · 2026-06-28):** 이 문서가 다루는 인리치/분석은 별개 repo **`news-analytics`** 소유다. newsstore에선 히스토리로만 보존한다. 경계·계약과 소유권 인덱스는 **`docs/firestore-contract.md`** 참조.

_근거 설계: `docs/superpowers/specs/2026-06-15-newsstore-story-timeline-ui-design.md` (3렌즈 리뷰 통과). 이 플랜은 그 §3·§5·§6의 백엔드 절반만 구현한다(프론트=플랜 B). TDD — 실패 테스트 먼저, Docker 에뮬레이터로 green._

## 0. 목표 한 줄
`stories`에 새 멤버가 생긴 스토리만 골라 flash-lite로 **title·summary·developments**를 만들어 stories 문서에 merge 저장하는 `run_enrich --mode summary` 패스. 프론트가 읽을 필드를 채운다.

## 1. 결정 (스펙에서 구체화 — 리뷰 대상)
- **D1. developments의 time을 LLM이 직접 만들지 않는다.** LLM은 각 전개에 대해 **그 전개를 처음 연 기사의 인덱스(`first_idx`)**만 반환. 코드가 `members[first_idx].published_at`를 읽어 절대 타임스탬프 `time`을 채운다(grounding — LLM이 ISO를 지어내지 않게). 범위 밖 인덱스는 검증에서 드롭.
- **D2. `latest`를 LLM에 따로 묻지 않고 도출한다.** developments를 `time` 내림차순 정렬 후 `latest = developments[0].text`(가장 최근 전개). LLM의 latest와 developments가 어긋나는 모순을 원천 제거. developments가 비면 `latest=""`.
- **D3. summary_count = "이번에 fetch한 전체 멤버 수"(= `len(get_story_members)`).** LLM에 먹인 수가 아니라 **읽은 멤버 총수**를 기록한다. 두 가지를 동시에 만족:
  - cluster 패스가 read↔save 사이에 멤버를 더하면 다음 런 `count > summary_count`로 재요약(놓침 방지).
  - cap된 대형 스토리(>cap)도 `summary_count=전체수`라 새 멤버가 없으면 `count == summary_count` → **재요약 안 함**(무한 재요약 누수 차단 — consistency/adversarial 렌즈 지적).
- **D4. 입력은 멤버 전체**(published_at asc), 발췌 길이 적응(많으면 80자, 적으면 200자). 멤버가 `SUMMARY_MAX_MEMBERS=200` 초과면 **최신 200건만** LLM에 먹이고(토큰·출력품질 상한) "(외 N건)" 표기 — 단 **summary_count는 전체수**(D3)라 재요약 루프 없음. LLM이 보는 인덱스 공간 = 먹인 리스트(`members_fed`)이고 `first_idx`·time grounding·validator의 `n_members`는 모두 `members_fed` 기준(경계 일치 — consistency 렌즈 지적).
- **D5. 저장은 필드 한정 merge**(`save_story_summary`) — cluster 패스 소유 필드(member_ids/centroid_sum/count/...)는 건드리지 않음.
- **D6. validator는 결정론(코드)만** — JSON 파싱·필수키·타입·title 길이·first_idx 범위. 내용 정합성(환각)은 v1 비검증(스펙 §8 수용 리스크). 파싱 불가 스토리는 스킵+로그(다음 런 재시도, fail-soft).

## 2. 신규 Store 계약 (contracts/ports.py `Store`)
```python
def get_stories_needing_summary(self, limit: int) -> list[dict]:
    """last_seen desc 상위에서 count>summary_count(새 멤버)인 것만. [{'id','count'}]. 코드측 필터."""
def get_story_members(self, story_id: str) -> list[dict]:
    """items where story_id==X order by published_at asc. [{'title','body','source','published_at'}]."""
def save_story_summary(self, story_id, *, title, summary, latest, developments,
                       summary_count, now) -> None:
    """summary 필드만 merge 저장(+ summary_count, summary_at=now). 다른 필드 보존."""
```
- `FirestoreStore` 구현:
  - `get_stories_needing_summary`: `collection('stories').order_by('last_seen', direction='DESCENDING').limit(limit)` 스트림 → 파이썬에서 `count > summary_count(기본 0)`만. (**`direction=` 키워드 문자열 — `firestore.DESCENDING` 상수/위치인자 아님**, factual 렌즈 지적. 부등호+정렬 한 쿼리 불가 → 코드 필터. 단일필드 정렬은 복합 인덱스 불필요.)
  - `get_story_members`: `collection('items').where('story_id','==',sid).order_by('published_at')` → dict 매핑. 인덱스 `items(story_id,published_at)` 이미 READY. **published_at이 null인 멤버는 맨 뒤로/또는 제외**(정렬·grounding 깨짐 방지) — 정렬 키 None 가드.
  - `save_story_summary`: `doc.set({summary,latest,developments,title,summary_count,summary_at}, merge=True)`.

- **D7(하드닝). `append_to_story`를 필드 한정 merge로 변경(레이스 차단).** 현재 `ref.set(d)`(풀-doc 덮어쓰기)는 cluster의 read↔set 사이에 summary 패스가 쓴 필드를 되돌릴 수 있다(adversarial 렌즈, 비가역 silent 손실). centroid_sum 누적은 여전히 read해 계산하되 **쓰기는 자기 소유 필드만 `merge=True`**로:
  ```python
  ref.set({"centroid_sum": csum, "count": ..., "member_ids": members,
           "entities": ents, "last_seen": now}, merge=True)   # 풀-doc set → 필드 merge
  ```
  기존 `test_create_append_centroid` 그대로 green(centroid 계산 불변) + 신규 테스트: "append 후에도 사전 기록된 summary 필드 보존".

## 3. 신규 모듈 `src/newsstore/enrich/summarizer.py` (순수 로직 + 오케스트레이션)
```python
SUMMARY_MAX_MEMBERS = 200

def build_summary_prompt(members: list[dict], *, omitted: int = 0) -> str:
    # members: published_at asc. 발췌 길이 = members 수에 따라 80~200자.
    # 각 줄: "{idx}. [{source}] {title} :: {body[:n]}" + 상대시간은 넣지 않음(LLM이 시간 안 지어내게; time은 코드가 채움)
    # omitted>0이면 "최신 N건, 이전 M건 생략" 주석(D4 절단 인지)
def validate_summary(raw: dict, *, n_members: int) -> dict | None:
    # 필수키(title,summary,developments). title 비어있지 않고 ≤80자(초과는 자름). developments=list.
    # 각 dev: text(str, 비어있지 않음), first_idx(0<=int<n_members 아니면 그 dev 드롭),
    #         source_count(int, 1..n_members로 클램프).
    # 유효 dev 0개면 developments=[] 허용(latest=""). 파싱/필수키 실패면 None(그 스토리 스킵).
def summarize_story(members_all: list[dict], client: LLMClient, *, now,
                    max_members=SUMMARY_MAX_MEMBERS) -> dict | None:
    # members_fed = members_all[-max_members:] (최신 cap건, asc 유지). n = len(members_fed).
    # build_prompt(members_fed) → client.generate_json → validate_summary(raw, n_members=n)
    #   → 각 dev.time = members_fed[first_idx].published_at (None이면 그 dev 드롭 — 가드)
    #   → developments를 time DESC 안정정렬 → latest = developments[0].text if developments else ""
    # 반환 dict(명세): {"title","summary","latest","developments",
    #                  "summary_count": len(members_all)}   # ← fed수 아닌 '전체 fetch수'(D3)
    # 파싱 실패(validate None)면 None 반환.
def run_summary_pass(store, client, *, limit, now, max_members=SUMMARY_MAX_MEMBERS) -> dict:
    # get_stories_needing_summary(limit) → 각 스토리 members=get_story_members(id)
    #   → summarize_story(members) → None이면 skip / 아니면 save_story_summary(... summary_count=res['summary_count'])
    # totals={'summarized','skipped'}. LLMError·예외는 그 스토리만 스킵(fail-soft, 로그). 멤버 0개 스토리도 skip.
```
- **LLM 출력 JSON 계약(프롬프트에 명시):**
  `{"title":"≤40자 캐노니컬","summary":"2~3문장 최근가중","developments":[{"text":"1줄","first_idx":N,"source_count":M}]}`
  - 지시: "시간순 기사로 전체 흐름을 전개(development) 단위로 묶어라. 의미상 같은 전개의 다른 표현은 하나로 합쳐라(출처 달라도). 각 전개의 first_idx=그 전개를 처음 보도한 기사 번호. 사실만, 출처 밖·추측 금지. JSON만."

## 4. run_enrich 배선
- `--mode` choices에 `summary` 추가. `tag`는 유지하되 더 이상 스케줄되지 않음(스펙: 폐기 — 코드 제거는 별도 정리 커밋, 이 플랜 밖).
- `args.mode == "summary"`: `run_summary_pass(store, client, limit=SUMMARY_BATCH, now=...)`. `SUMMARY_BATCH = int(os.environ.get("NEWSSTORE_SUMMARY_BATCH", "10"))`(기존 `NEWSSTORE_*` 접두 관례).
- 기존 `cluster` 경로 불변.

## 5. 테스트 (TDD — 먼저 빨강)
- **순수 로직(에뮬레이터 불필요, fake LLMClient):**
  - `test_summarizer.py`:
    - `build_summary_prompt`: 멤버 순서(asc)·인덱스 번호·발췌 길이 적응(많을 때 짧게)·소스 포함.
    - `validate_summary`: 정상 / 필수키 누락(None) / first_idx 범위초과(드롭) / title 과길이(잘림 or 무효) / source_count 클램프 / developments 비었을 때 허용.
    - `summarize_story`: fake LLM이 first_idx 주면 time이 members[first_idx].published_at로 채워지고 desc 정렬, latest=최신 dev.text. 불변식: developments time은 비증가(desc).
    - `run_summary_pass`: fake store(또는 에뮬레이터) — count>summary_count인 것만 호출, LLMError 스토리는 skip 카운트.
- **store(에뮬레이터):** `test_store_summary.py`:
  - `get_stories_needing_summary`: summary_count 없는/낮은 스토리만, last_seen desc, limit. **불변식: 반환된 모든 스토리가 `count>summary_count`**.
  - `get_story_members`: story_id 필터 + published_at asc 정렬. null published_at 멤버 가드.
  - `save_story_summary`: merge로 summary 필드 기록 + member_ids 등 기존 필드 **보존**(불변식: 저장 후 count/member_ids 그대로).
  - **D7 레이스 가드**: summary 저장 → `append_to_story` 호출 → summary 필드(summary/developments)가 **여전히 존재**(append가 안 지움).
  - **D3 재요약 사이클**: save_story_summary(summary_count=N) 후 append로 count→N+1 → `get_stories_needing_summary`가 그 스토리 **포함**. 반대로 새 멤버 없으면(count==summary_count) **미포함**(>cap 무한루프 없음).
- **계약 가드:** 신규 메서드가 `Store` Protocol에 있는지(module boundary/계약 테스트가 이미 도는지 확인, 필요 시 보강).
- **라이브 스모크(선택, 돈 안 듦 — GEMINI_API_KEY 있을 때만, 기본 skip):** 실제 flash-lite 1콜로 JSON 형식·한국어 확인. CI/에뮬레이터 기본 런에서는 skip.
- **불변식으로 검증(매직넘버 금지):** "FAIL=0", "저장 후 기존필드 불변", "developments time desc" 같은 불변식. 기대 개수 하드코딩 금지.

## 6. 실행/검증 절차
```
MSYS_NO_PATHCONV=1 docker compose run --rm test    # 전체 그린(신규 포함)
```
- 통과 증거(로그) 확보 후에만 "됐다". 배포(이미지 재빌드·Scheduler 생성)는 **이 플랜 밖** — operations.md에 §F로 절차만 추가(돈 쓰는 실행은 사용자 확인).

## 7. operations.md 추가(문서만, 실행 X)
- **§F. 요약 패스 스케줄러**: 기존 `newsstore-processor` 이미지 재사용, 새 Scheduler `newsstore-summary-hourly`(`5 * * * *`)가 같은 Job을 `--args=...,--mode=summary`로 트리거. 비용 ~월 $1~2(실측 확인). Scheduler 무료 3개 한도(현재 2개) 내.
  - 주의: Cloud Run Job의 `--args`는 생성 시 고정 → mode별로 **두 번째 Job**(`newsstore-summarizer`, 같은 이미지, args=`--mode=summary`)을 만들거나, 하나의 Job에 Scheduler가 `--update-args`로 오버라이드. 더 단순한 쪽=**별도 Job**(이미지 공유, 비용은 실행시간만). 이 결정은 배포 시 확정.

## 8. 리스크 / 경계
- **append_to_story 레이스**: D7에서 필드 한정 merge로 **닫음**(요약 필드 revert 불가). 회귀 테스트로 가드.
- **>cap(200) 대형 스토리**: LLM에 최신 200건만 → 아주 오래된 전개는 developments에서 빠질 수 있음(디테일 뷰의 기사 목록은 프론트가 items 전체를 읽으므로 영향 없음). summary_count=전체수라 재요약 루프는 없음. 희소 케이스, "(외 N건)" 표기로 정직.
- **first_idx grounding 실패**: 범위 밖/ null published_at dev는 드롭(로그). 다수 드롭 시 developments 축소되나 파싱 자체는 성공 → fail-soft.
- **latest 도출**: 안정정렬 + time DESC[0]. 동일 published_at 충돌은 안정정렬로 결정적. LLM 의미 dedup 오류는 v1 비검증(스펙 §8 수용).
- **환각**: v1 비검증(스펙 §8). 후속 advisor-correctness.
- **비용**: limit(10)×시간당 = 240콜/일, 콜당 입력 ≤200멤버×적응발췌(≈ 수천 토큰) → flash-lite 월 ~$2~4 추정(배포 후 실측). 토큰 킬스위치 별도 없음 — 적응발췌+cap이 입력 상한. 운영 모니터링은 후속.
- 비파괴: 기존 필드 불변 테스트로 가드.

<!-- spec-review: passed lenses=3 date=2026-06-15 -->
