# newsstore 스토리 클러스터러 컷오버 (news-analytics 라이브러리 import) — 설계

_작성: 2026-06-29 · 상태: **보류(SHELVED) 2026-06-29** — 사용자 전략 전환("통합 우선, 나중 1회 분리"). 이 컷오버는 지금 구현하지 않는다. 분석 레이어를 newsstore 안에서 개발하고 인터페이스 안정 시 한 번에 분리. 본 설계는 재분리 시점 참고 자료로 보존. · 성격: 자기완결 — 인리치 파이프라인의 **스토리 배정 결정**만 외부 라이브러리로 교체(인리치 레이어, newsstore 범위)_

> **이 스펙의 경계 (다른 repo와의 분리)**
> - **포함**: newsstore가 `news-analytics`(별 repo, GitHub) 라이브러리를 import 하고, `process_once`의 스토리 배정 결정을 newsstore 자체 로직(`InMemoryVectorIndex.nearest`, 단일 임계값·LLM 없음)에서 news-analytics `EventClusterer.assign`(gray-band LLM)으로 **완전 교체(cutover)**. 어댑터·LLM 갭 메꿈·store 읽기 확장·의존성 배선·라이브 Job#2 재배포·`firestore-contract.md` 정정.
> - **제외(news-analytics 소유)**: 클러스터링 알고리즘 자체, gray-band 임계값 캘리브레이션, 임베딩/LLM 모델 선택. newsstore는 *호출자*이며 알고리즘 내부를 지시하지 않는다.
> - **제외(후속 페이즈)**: 렌즈 분류·델타·risk/impact 스코어·요약 합성(news-analytics §2 미구현) — newsstore에 잔류(과도기).
> - **결합 모델 SSOT**: `docs/firestore-contract.md`(본 작업에서 "newsstore가 라이브러리 import"로 정정). 라이브러리 사용법 SSOT: news-analytics `docs/handoff/2026-06-29-phase1-status-and-usage.md`.

## 1. 목표 / 배경
newsstore는 본연의 일(수집·저장·호스팅)에 집중하고, **분석 알고리즘은 news-analytics로 분리**됐다. 두 repo는 코드로 결합하지 않는다는 초기 결정에서, **사용자 확정(2026-06-29): newsstore가 news-analytics를 import 해서 쓴다** — news-analytics는 순수 로직 + 의존성 주입(DI) 라이브러리이고 I/O·키·저장·스케줄은 newsstore가 쥔다.

첫 통합 대상 = **스토리 클러스터링**(news-analytics Phase 1에서 유일하게 구현됨). 현재 인리치 파이프라인은 newsstore 자체 `InMemoryVectorIndex.nearest`(단일 코사인 임계값, LLM 없음)로 기사를 스토리에 배정한다. 이를 news-analytics `EventClusterer.assign`(gray-band LLM 판정 포함)으로 교체한다.

**효과(news-analytics 측정 근거):** gray-band LLM이 임계값 근처 모호한 쌍의 과병합을 줄여 B-cubed F1 0.719→0.821(실 Gemini eval, 이란+코스피 370건, P=1.000 R=0.696). **이 eval은 newsstore와 동일 임베더(`gemini-embedding-001`/768/무정규화, `gemini_eval.py`)로 돌았다 → cross-model 외삽 아님.** 단 측정 코퍼스(이란+코스피 골든셋)는 newsstore 프로덕션 전체 스트림과 다르다 → **cross-corpus 리스크는 남는다**(정직히: §3·§7·§8에서 관측으로 닫는다). 즉 컷오버는 *측정상* 개선이며, 프로덕션 검증은 배포 후 관측한다.

## 2. 확정된 결정
1. **결합 = 라이브러리 import**(사용자 확정). news-analytics = 순수 결정(알고리즘). newsstore = I/O·키·저장(어댑터가 주입).
2. **완전 교체(cutover)**: 라이브 Job#2가 news-analytics를 호출. newsstore 자체 클러스터링 코드는 배정 경로에서 분리. **비파괴: 먼저 교체, 죽은 코드 물리 삭제는 후속 정리**(`coding-principles` 비파괴·SURGICAL — 발견된 죽은 코드는 flag).
3. **의존 패키징 = GitHub main 추적 + 빌드 시 lock 핀**(사용자 확정 2026-06-29: "두 repo가 서로 GitHub main을 보는 게 안전"):
   - `pyproject.toml`: `news-analytics @ git+https://github.com/chshin84/news-analytics@main` — 두 repo가 **main을 통합 기준선(SSOT)**으로 본다. news-analytics 변경이 main에 머지되면 다음 빌드가 자동 반영(수동 sha bump 불필요 — 활발한 동시 개발에 맞음).
   - **단, `@main`만 두면 빌드가 비재현적**(시점 T 빌드 ≠ T+1; FAIL-LOUD/SSOT 약화). 보완: **빌드 시 해소된 커밋 SHA를 `infra/requirements.lock`에 기록**해 *그 빌드*는 재현 가능하게 한다. 개발은 main을 추적, 배포 이미지는 lock의 SHA로 고정(양립).
   - 함의: 컷오버 배포 전 news-analytics main이 그린(테스트 통과)인지 확인하는 것이 양쪽의 책임(통합 계약).
4. **교체 범위 = 배정 결정만**. classify_kind·태깅·임베딩·요약·`create_story`/`append_to_story`/`save_enrichment`/`mark_processed`/`close_stale_stories`는 **그대로**(newsstore 소유, 비파괴 merge 유지).
5. **계약 문서 정정**: `firestore-contract.md`의 "Firestore-as-API · newsstore는 import 안 함" 결정을 "**newsstore가 news-analytics 라이브러리를 import, 모든 Firestore I/O는 newsstore 소유**"로 갱신(드리프트 제거, FAIL-LOUD).

## 3. 호환성 — 확인된 사실 (MEASURE-FIRST)
- ✅ **`centroid_sum` 의미 일치**: newsstore는 스토리 벡터를 멤버 임베딩 **합**으로 저장(`create_story` `centroid_sum=list(vec)`, `append_to_story` `add_vectors`). news-analytics `Story.centroid_sum`도 "멤버 임베딩 합"(코사인 스케일 불변). 1:1 매핑 가능.
- ✅ **임베딩 모델 일치**: newsstore `GeminiClient`는 `gemini-embedding-001` + `output_dimensionality=768`(무정규화). news-analytics eval(`gemini_eval.py`)도 **동일 모델·768·무정규화**로 F1 0.821 달성 → 동일 모델. 교차검증: 옛 newsstore 단일 임계값 `DEFAULT_THRESHOLD=0.72`가 새 gray-band 상단(hi=0.75) 바로 아래에 위치 → 같은 코사인 영역(모델 호환 방증).
- ⚠️ **임계값은 "정식 캘리브레이션"이 아니라 "eval 검증된 Phase-0 기본값"**(정직히): `news_analytics/config.py`가 `GRAY_BAND=(0.55,0.75)`를 *"측정 전 기본값"*으로 명시. 이 값으로 eval이 F1 0.821을 냈으니 **동일 모델에서 유효함은 입증**됐으나, 임계값 스윕이나 newsstore 전체 코퍼스 검증은 아니다. → v1은 배포 후 `llm_calls` 비율 + 스토리 품질 스폿체크로 관측(§7·§8). 임계값 재조정이 필요하면 news-analytics 측 결정(newsstore는 관측·보고).
- ⚠️ **갭 1 — store 읽기**: `get_open_stories`가 `title`을 안 돌려주고 centroid를 `count`로 평균낸 dict를 준다. gray-band LLM은 후보 스토리의 `title`을 프롬프트에 쓴다 → 배정 경로는 `title` + `centroid_sum`(원본 합)을 받아야 한다.
- ⚠️ **갭 2 — LLM 인터페이스**: news-analytics는 `llm.complete(prompt: str) -> str`(평문 첫 줄 `SAME`/`DIFFERENT`)을 요구. newsstore `GeminiClient`엔 `generate_json`(dict)·`embed`만 있고 평문 `complete`가 없다 → 추가 필요.

## 4. 아키텍처 — 데이터 흐름
`process_once`(newsstore 소유, 변경 최소):
```
get_unprocessed(batch)
  → classify_kind                         (그대로)
  → (story만) tag_items / embed_items     (그대로; embed=gemini-embedding-001/768)
  → [교체] 스토리 배정 결정
        from:  InMemoryVectorIndex.nearest(vec, threshold)      # 단일 임계값, LLM 없음
        to:    na_adapter.assign(item, vec, open_stories)       # → EventClusterer.assign (gray-band LLM)
  → create_story / append_to_story        (그대로, 비파괴 merge)
  → save_enrichment + mark_processed       (그대로)
  → close_stale_stories                    (그대로)
```
주 경로는 기사 임베딩을 **이미 보유**(processor가 클러스터 전 embed)하므로 `assign`은 `article.embedding`을 그대로 쓴다 → assign 경로에서 embed 재호출 없음. 주입 embed는 계약상 폴백.

## 5. 컴포넌트 (신규/변경)

### 5.1 의존성 (`pyproject.toml` + lock)
`enrich` extra에 추가:
```
"news-analytics @ git+https://github.com/chshin84/news-analytics@main"
```
- **개발은 main 추적**(결정 §2.3): news-analytics main이 통합 기준선. extras(`clustering`/`finance`)는 설치하지 않는다 — newsstore는 `clustering.EventClusterer`/`contracts`만 쓰고 코어 의존성 0(DI).
- **빌드 재현성**: 빌드 시 해소된 news-analytics 커밋 SHA를 `infra/requirements.lock`에 기록(또는 빌드 로그에 남겨) *그 이미지*는 고정 SHA로 재현 가능. `@main`(가변)과 lock(고정)의 분리.
- `infra/requirements.lock` 제약과 충돌 없는지 확인. Docker 빌드/Cloud Build가 GitHub에 네트워크 접근 가능(공개 repo).

### 5.2 `src/newsstore/enrich/na_adapter.py` (신규) — 경계 어댑터
news-analytics 타입/주입을 newsstore 데이터와 잇는 **유일한 결합점**. 한 파일에 격리(FOCUSED).
- `build_clusterer(client: LLMClient) -> EventClusterer`:
  - `embed = lambda texts: [client.embed(t) for t in texts]` (폴백; 주 경로 미사용).
  - `llm = client`(§5.3에서 `.complete` 보유) — news-analytics는 `llm.complete`만 duck-typed로 요구(자기 `contracts.LLMClient` Protocol). newsstore가 news-analytics의 Protocol을 import할 필요 없음.
  - `EventClusterer(embed=embed, llm=llm)` 반환(1회 생성, 배치 간 재사용).
- `to_article(item: RawItem, vec) -> Article`: `Article(id, title, body, source, published_at, tags=(), embedding=tuple(vec))`. **`RawItem`엔 `tags`가 없으므로 빈 튜플**(news-analytics assign은 tags 미사용 — body·title·embedding만).
- `to_stories(rows) -> list[Story]`: store 읽기 행(`id, title, centroid_sum`)을 `Story(id, title, centroid_sum=tuple(...))`로 매핑. **나머지 필드(`member_ids, entities, status, count, first_seen, last_seen`)는 dataclass 기본값**(assign은 후보 비교에 `id·title·centroid_sum`만 읽음 — `clustering.py` assign 참조).
- `assign(clusterer, item, vec, open_stories) -> str | None`: `to_article` + `clusterer.assign(article, open_stories)` 위임. (`to_article`/`to_stories`는 assign 경로에서만 호출 — 과분리 아니라 결합점 가독성; plan에서 인라인 여부 판단 가능.)

### 5.3 `GeminiClient.complete(prompt, *, timeout=DEFAULT_TIMEOUT) -> str` (신규 메서드)
평문 생성(`response_mime_type` JSON **없이** `generate_content`, `r.text` 반환) + 기존 `call_with_retry(_call, is_transient=self._is_transient)` 재사용. None 가드 유지(`generate_json`과 동일 패턴). 시그니처는 `generate_json`/`embed`와 정합(`*, timeout` 키워드). news-analytics gray-band가 `llm.complete(prompt)`로 호출(timeout 미전달 → 기본값 적용).
- **newsstore `ports.LLMClient` Protocol(contracts/ports.py)에도 `complete` 추가**: `GeminiClient`가 그 Protocol을 만족한다고 선언돼 있으므로(`processor`가 `client: LLMClient`로 받음), 드리프트 방지 위해 Protocol에도 시그니처를 더한다(EXPLICIT — 계약에 드러냄). FakeLLMClient(테스트)도 `complete` 구현.

### 5.4 store 읽기 확장 (`firestore_store.py::get_open_stories`)
배정 경로가 `title` + 원본 `centroid_sum`를 받도록 반환 dict 확장:
- 반환: `{id, title, centroid_sum(원본 합), centroid(평균, 기존), count(기존)}` — **기존 `centroid`/`count` 키 보존(비파괴, 기존 호출자 `InMemoryVectorIndex.from_open_stories` 안 깨짐)**, `title`·`centroid_sum` 추가.
- `where(status==open)` 쿼리·`last_seen >= cutoff` 클라측 필터는 그대로.
- 비고: `InMemoryVectorIndex.from_open_stories`는 평균 `centroid`를 다시 `c*count`로 합 역산(`vector_index.py`) — 어댑터는 원본 `centroid_sum`를 직접 쓰므로 그 역산 경로를 안 탄다(후속 정리 시 정리 대상).

### 5.5 `processor.py` 배선 (제어 흐름 명시)
`process_once`에서 인덱스 기반 배정을 어댑터 배정으로 교체. 의사코드:
```python
# 진입부(1회):
open_rows = store.get_open_stories(now - open_window)        # title·centroid_sum 포함(§5.4)
open_stories = na_adapter.to_stories(open_rows)              # list[Story]
clusterer = na_adapter.build_clusterer(client)              # embed·llm 주입(1회)
# 배치 loop(_assign_and_persist 대체):
for it in story_items (vec 있음):
    sid = na_adapter.assign(clusterer, it, vec, open_stories)   # gray-band LLM
    if sid is None:
        sid = id_factory(); store.create_story(sid, title=it.title, vec=vec, member_id=it.id, entities=entities, now=now)
        open_stories.append(Story(sid, it.title, centroid_sum=tuple(vec)))   # 같은 배치 내 후속 기사가 신규 스토리에 합류 가능하게 갱신
    else:
        store.append_to_story(sid, vec=vec, member_id=it.id, entities=entities, now=now)
        # (배치 내 centroid_sum 갱신은 v1 단순화: open_stories의 합은 다음 배치 진입 시 재읽기로 반영 — 동일 배치 누적은 후속 최적화)
```
- **이 PR의 변경 범위(정직히)**: 이것은 단순 "죽은 코드 표시"가 아니라 **동작 변경(단일 임계값 0.72 → gray-band LLM)이자 제어흐름 변경**(`InMemoryVectorIndex.from_open_stories` 생성·`index.nearest` 호출 제거). "비파괴"는 **데이터**(merge·덮어쓰기 없음)와 **코드 보존**(`cluster.py`·`vector_index.py` 물리 삭제는 후속 PR로 flag, 다른 호출자 확인 후)에만 적용 — 배정 알고리즘 교체 자체는 의도된 컷오버다.
- top-k 사전선별(벡터 인덱스로 `open_stories` 축소)은 **v1 미적용**(open 스토리 N 작음 가정). 배포 후 N·assign 지연을 관측해 커지면 후속(§9). assign의 후보 순회는 O(N) 코사인이며 **LLM 콜은 후보 최상위 1쌍에만**(기사당 ≤1콜) — 비용은 N과 무관(§6).

### 5.6 계약 문서 정정 (`docs/firestore-contract.md`)
구체 편집:
- 상단 §"결정(2026-06-28): news-analytics는 Firestore에 직접 read/write(Firestore-as-API). newsstore 라이브러리를 import 하지 않는다" → "**결정(2026-06-29): newsstore가 news-analytics 라이브러리를 import. news-analytics는 순수 DI 로직(I/O 없음), 모든 Firestore read/merge·스케줄·키는 newsstore 소유**"로 교체.
- "소유권 — 누가 쓰고 누가 읽나" 표의 `items`(인리치 필드) writer **`news-analytics (merge)`** → "**newsstore 어댑터(news-analytics 결정으로 merge)**", `stories` writer **`news-analytics`** → "**newsstore 어댑터(클러스터링=news-analytics, I/O=newsstore)**".
- "과도기 현실" 섹션은 클러스터링이 라이브러리로 이전됨을 반영해 갱신(분류·태깅·임베딩·요약은 아직 newsstore 잔류).

## 6. 에러 처리 + 비용 경계 (FAIL-LOUD / fail-soft)
- gray-band LLM 장애·DIFFERENT·부재 → news-analytics `EventClusterer.assign`이 **보수적 신규(`None`, fail-soft)** 반환(패스 안 죽음). 그 위에 newsstore `call_with_retry`(일시 오류 재시도).
- 차원 불일치·중복/누락 id·빈 임베딩 → news-analytics **ValueError(FAIL-LOUD)** — 조용히 뭉개지 않음.
- 임베딩 모델 드리프트(차원≠768) → 어댑터/계약 테스트로 폭발.
- **비용 경계(온라인 경로, $0 기조)**: `assign`은 후보 중 **최상위 1쌍이 gray-band일 때만** LLM 1콜 → **기사당 ≤1콜**, 대부분(sim≥0.75 또는 <0.55)은 결정론 0콜. 따라서 비용은 open_stories N과 무관(배치 `cluster_articles`의 `LLM_CALL_CAP_RATIO=0.2`는 배치 경로 전용 — 이번 컷오버는 온라인 `assign` 사용). 관측: news-analytics가 콜수를 로그로 노출, newsstore가 배치당 LLM 콜 비율을 집계·관측(§8). Gemini Developer API 무료 tier RPM/RPD 한도 초과 조짐이면 보고(임계값 초과 시 보수적 강등은 라이브러리가 fail-soft로 처리).
- 컷오버라 인리치 경로 **폴백 없음**: import/빌드 실패는 즉시 터짐. **롤백 = 이전 Job#2 이미지 태그**(REVERSIBLE — §8).

## 7. 테스트 (TDD — 구현 전 실패 테스트, fake LLM/embed)
계약은 **불변식**으로 검증(매직넘버 금지):
1. **같은 사건 2건 → 같은 story_id**: fake LLM이 gray-band에서 `SAME` → 합류.
2. **다른 사건 → 분리**: sim<lo 또는 LLM `DIFFERENT` → 신규(다른 story_id).
3. **gray-band LLM 장애 주입 → 보수적 신규**: fake LLM이 예외 → `assign`은 `None`(신규), 패스 생존(fail-soft).
4. **비파괴**: 기존 스토리에 멤버 합류 시 요약 필드(`summary`·`developments`) 보존(`append_to_story` merge).
5. **임베딩 차원 계약**: 768 아닌 벡터 혼입 → ValueError(FAIL-LOUD).
6. **어댑터 매핑 1:1**: store dict ↔ `Article`/`Story` 필드 매핑(title·centroid_sum 누락 없음; `Article.tags=()` 기본).
7. **GeminiClient.complete**: fake SDK로 평문 반환·None 가드·retry 동작(비기능).
8. **배치 내 신규 스토리 가시성**: 같은 배치의 두 기사가 같은 사건 → 첫 기사가 연 스토리에 둘째가 합류(`process_once`가 배치 중 `open_stories`를 갱신하는지 — §5.5 의사코드 불변식). 안 그러면 한 배치에서 같은 사건이 중복 스토리로 쪼개짐.
- 실행: `MSYS_NO_PATHCONV=1 docker compose run --rm test`(에뮬레이터). 빌드는 news-analytics git 핀을 포함해 import 가능해야 함.

## 8. 컷오버 / 롤백 (operations.md §E·§F 연동)
1. news-analytics `main`이 그린(테스트 통과)인지 확인 → newsstore 빌드가 `@main` 해소. 해소된 SHA를 lock/빌드로그에 기록(§5.1).
2. processor 이미지 재빌드(`INSTALL_ENRICH=true`, news-analytics 포함) → `gcloud run jobs update newsstore-enricher --image ...` → execute.
3. 스모크: 한 배치 실행 로그에서 news-analytics `clustering: ... llm_calls=N ...` 관측 + 스토리 생성/합류 정상. **스폿체크(cross-corpus 관측)**: 새로 생성/합류된 스토리 표본 ~10건이 사람 눈에 과병합/과분리 아닌지 확인(정식 메트릭 인프라는 YAGNI — 표본 점검으로 충분, 회귀 신호 시 보고).
4. 회귀: 사이트 스토리 탭이 정상 렌더(fail-soft 불변식 유지 — `stories` 비어도 강등).
5. **롤백 시 데이터 일관성(정직히)**: 롤백은 이전 이미지 태그로 `jobs update` 되돌림. 이미 `processed=true`로 기록된 기사는 **재처리하지 않으므로**(get_unprocessed가 안 집음) 손상 없음 — 롤백 후 미처리분만 옛 임계값으로 배정된다. 스토리는 open 클러스터(엄격 파티션 아님)라 **신/구 로직이 섞여 배정돼도 유효**(같은 기사가 두 story_id를 받는 일은 없음 — 기사당 1회 처리). 즉 부분 컷오버→롤백은 **비파괴**.
- **비용($0 기조)**: §6대로 온라인 assign은 기사당 ≤1콜. 배치당 LLM 콜 비율을 관측, 무료 tier 한도 초과 조짐이면 보고.

## 9. 후속 (이 스펙 범위 밖, 백로그)
- `cluster.py`·배정용 `vector_index.py` 물리 삭제(다른 호출자 없음 확인 후).
- news-analytics 후속 페이즈(렌즈·델타·risk/impact·요약) 인수 시 동일 import 패턴 확장.
- top-k 후보 사전선별(벡터 인덱스)로 `open_stories` 축소 — open 스토리 수가 커질 때만(YAGNI).
- `meta` source `tier` 발행 배선(별 핸드오프 TODO; 본 스펙과 독립).

<!-- spec-review: passed lenses=3 date=2026-06-29 -->
