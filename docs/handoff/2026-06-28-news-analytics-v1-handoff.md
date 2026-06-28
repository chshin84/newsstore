# news-analytics 위임 — newsstore가 요구하는 것 (계약 + 동작 보증)

_작성: 2026-06-28 · 성격: 요구자(newsstore) → 수행자(news-analytics) 위임서 · 회신(§E)을 받으면 이 문서를 갱신한다._

> **핵심 입장:** newsstore는 news-analytics의 **내부 구현을 지시하지 않는다.** 어떻게 만들든(현 코드 포팅·재작성·내부 재설계 무엇이든) 그건 news-analytics의 자유다. newsstore가 요구하는 것은 단 둘 — **(A) 인터페이스 계약 준수**와 **(B) 동작 보증**이다. 이 둘만 지켜지면 내부는 "어떻게든 돌아가든" 상관없다.
>
> **쓰는 법:** 아래 "전달 본문"을 그대로 복사해 news-analytics 세션에 전달한다. 계약의 SSOT는 `docs/firestore-contract.md`이며, 본문 §A는 그 요약이다.

---

## 전달 본문 (복사해서 news-analytics 세션에 전달)

### 0. 너의 정체성·관계
너는 **news-analytics** 라는 별개 repo에서 일한다. 자매 프로젝트 **newsstore**가 뉴스 **수집·저장·호스팅(웹 UI)**을 담당하고, **너는 분석/인리치 계층**(LLM 태깅·임베딩·스토리 클러스터·요약·점수)을 담당한다.

**두 repo는 코드로 결합하지 않는다. 유일한 이음새는 Firestore다.** 너는 newsstore를 import하지 않고 너의 Firestore 클라이언트로 직접 읽고 쓴다. GCP `daily-recap-498506`, 리전 `asia-northeast3`, Firestore `(default)` Native.

**내부 구현은 전적으로 너의 자유다.** newsstore는 아래 §A(계약)와 §B(보증)만 요구한다. 그 둘을 깨지 않는 한, 어떤 코드·알고리즘·구조로 만들지는 네가 정한다.

### A. 하드 계약 — Firestore 스키마 (이건 인터페이스라 못 바꾼다)
> SSOT: newsstore `docs/firestore-contract.md`. 아래는 자기완결 요약.

**컬렉션·소유권**

| 데이터 | 누가 쓰나 | 너의 동작 |
|---|---|---|
| `items` (raw: id, feed_id, source, asset_hint, language, url, title, body, published_at, fetched_at) | newsstore | **읽기만** |
| `items.processed=false, processed_at=null, tags=[]` (raw에 박혀 옴) | newsstore | "인리치 필요" 신호 |
| `items` 인리치 필드: `kind, tags[], embedding[768], story_id, processed=true, processed_at` | **너 (merge 쓰기)** | raw 필드 절대 덮어쓰지 마라 |
| `stories/{id}`: `title, centroid_sum[], count, member_ids[], entities[], first_seen, last_seen, status(open\|closed)` + 요약필드 `summary, latest, developments[{text,time,source_count}], summary_count, summary_at` | **너** | 생성·갱신 |
| `feed_state` | newsstore | **건드리지 마라** |
| `meta` (sources, source tier) | newsstore | **읽기만** |

- **핸드오프**: newsstore가 `processed=false`를 박는다 → 너는 미처리분을 읽어 인리치 → `processed=true, processed_at` **merge** 기록.
- **비파괴 merge**: 인리치 필드만 merge. raw 필드는 절대 덮어쓰지 마라.
- **스키마 안정**: 위 필드명(`tags`, `story_id`, `stories.*`)은 **newsstore 웹 UI가 그대로 읽는다.** 이름을 바꾸면 사이트가 깨진다. 바꿔야 한다면 §E로 newsstore와 합의 먼저.
- **임베딩 차원 768 고정.** 인덱스는 newsstore가 적용 — 필요한 인덱스는 §E로 요청.

### B. 동작 보증 — newsstore가 진짜 요구하는 것 (결과)
1. **연속성·무회귀** — 공개 사이트가 **지금만큼**(태그 필터·스토리 타임라인·요약) 끊김 없이 계속 동작한다. 전환으로 사용자가 보는 품질이 떨어지지 않는다.
2. **완결성** — 현재 라이브로 돌고 있는 기능을 **전부** 인수하고 스케줄대로 계속 돈다(클러스터·태깅/임베딩·스토리 요약). 일부가 조용히 멈추는 상태를 남기지 않는다.
3. **스무스 컷오버** — 현재 newsstore가 돌리는 인리치 Job에서 news-analytics로 **무중단 전환** + **롤백 경로**. 전환 중 이중 처리·데이터 손상 없음.
4. **Fail-soft + 관측** — 분석이 장애·중단되면 사이트는 raw 뉴스로 **우아하게 강등**(빈 화면 금지). 실패는 조용히 삼키지 말고 로그·지표로 **시끄럽게** 드러난다.
5. **비용** — 무료/소액($0 기조) 유지. 비용 늘면 §E로 보고.

### C. 참고 — 현재 동작 (강제 아님, 출발점일 뿐)
지금 인리치 파이프라인은 **newsstore 이미지에서 라이브로 돈다**(Cloud Run Job#2 cluster 10분 / Job#3 summary 시간당). 동작 결과를 빠르고 안전하게 재현하려면 **현 구현을 그대로 포팅하는 것이 가장 짧은 길**이다 — 레퍼런스 코드는 newsstore repo(예: `D:\projects\newsstore`)의 `src/newsstore/enrich/`, `entrypoints/run_enrich.py`, `config/taxonomy.yaml`, `tests/`, 인프라는 `Dockerfile`/`infra/cloudbuild.processor.yaml`/`docs/operations.md §E·§F`, 설계 근거는 `docs/superpowers/`의 step2·modular·story-summary 문서에 있다.

**하지만 포팅할지·다시 짤지·내부를 개선할지는 너의 결정이다.** §A·§B만 지키면 된다. (권장: 분리를 안전하게 하려면 v1은 동작 보존으로 가고, 개선은 컷오버 후 v2로. 단 이 순서도 강제 아님.) 상수·모델명은 코드가 SSOT다 — 특히 **Gemini 모델명은 `gemini.py`에서 읽어라**(README/roadmap엔 드리프트 있음).

### D. 검수 (Definition of Done)
1. **계약(§A) 일치** — Firestore 입출력 필드·핸드오프·비파괴가 계약대로. 검증 가능한 테스트로.
2. **보증(§B) 충족 증거** — 연속성(사이트 실측), 완결성(스케줄 동작 로그), 컷오버(무중단+롤백 시연), fail-soft(장애 주입 시 사이트 정상)를 **증거로** 보인다(주장만 금지).

### E. newsstore(요구자)에 회신할 것
1. **§A 스키마 합의 여부** — 그대로 가능한가? 불가피한 편차가 있으면 무엇·왜.
2. **newsstore에 필요한 작업** — 추가 Firestore 인덱스 목록, `meta`에 source **tier** 발행 필요 여부(현재 싣는지 불확실 — 미포함이면 newsstore가 추가).
3. **컷오버 계획** — 언제 전환 가능, 롤백 방법.
4. **막힌 점·질문**.

---

## 회신 로그 (news-analytics → newsstore)
_§E 회신을 받으면 여기 기록하고, newsstore 반영(인덱스 추가·tier 발행·모델명 교정 등)을 추적한다._

- (대기 중)
