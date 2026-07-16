# 임베딩 재도입 설계 — item_vectors (data-only 위 최소 조각)

- 날짜: 2026-07-16
- 상태: 설계 승인 대기 → 승인 시 구현 계획으로 전환
- 배경: 이 저장소를 다운로드해 개인 데일리 리포트를 만드는 다운스트림이 생겼다. 각자가
  기사를 따로 임베딩하는 것보다 수집 시점에 한 번 임베딩해 두는 것이 낫다는 판단으로,
  data-only 전환(9852dcd) 때 제거했던 것 중 **임베딩 벡터 계산만** 되살린다.
  생성형 LLM(태깅·요약·클러스터·리포트)은 계속 배제한다 — 스코프 문장은 "생성형 LLM
  배제, 단 임베딩 벡터 계산만 예외"로 정정한다.
- 구현 원칙: main 브랜치 히스토리(ca8840a)의 **검증된 기존 코드를 기준으로 복원**한다.
  새로 짜지 않고, embed에 필요한 부분만 축소해 가져온다.

## 사용자 결정 (2026-07-16 브레인스토밍)

1. **모델**: `gemini-embedding-001`, `output_dimensionality=768`. 과거 검증된 구성
   그대로이며, 이 선택은 다운스트림과의 계약이다(유사도 검색 쿼리도 같은 모델·차원으로
   임베딩해야 한다).
2. **실행 위치**: collector 잡 안에서 수집·저장이 끝난 뒤 별도 임베딩 패스로 돈다.
   Gemini 장애가 뉴스 수집을 막지 않는다.
3. **대상**: `kind == "story"`인 기사만. spam·digest·sports는 임베딩하지 않는다.
4. **저장 위치**: 별도 컬렉션 `item_vectors/{item_id}`. 벡터(기사당 약 6KB)를 items
   문서 밖에 두어 공개 웹 피드(클라이언트 SDK로 80건 통째 읽기, 필드 선택 불가)에
   대량 페이로드를 싣지 않는다.
5. **백필**: 배포 직후 TTL 30일 윈도우 안의 기존 story 기사를 소급 임베딩한다.

## 아키텍처

### 데이터 계약 — `item_vectors/{item_id}`

| 필드 | 타입 | 내용 |
|---|---|---|
| `vector` | array\<float\> ×768 | 임베딩 벡터. 차원이 768이 아니면 저장하지 않는다(fail-loud). 차원은 `len(vector)`로 자기기술되므로 별도 dim 필드는 두지 않는다. |
| `embed_model` | string | `"gemini-embedding-001"` — 다운스트림이 쿼리 임베딩 모델을 맞추는 근거. store가 상수 SSOT에서 주입한다. |
| `embedded_at` | timestamp | 임베딩 시각. store가 주입한다. |
| `expire_at` | timestamp | **원본 item 문서의 `expire_at`을 그대로 복사**한다(기사와 벡터가 함께 만료). |

- 임베딩 입력은 `title + " " + body[:500]`(과거 embedder의 `embed_text`와 동일).
  입력 규칙도 계약이므로 firestore-contract.md에 명시한다.
- 모델명·차원 상수(`EMBED_MODEL`·`EMBED_DIM`)는 `contracts/embedding.py`에 단일
  정의(SSOT)하고 embed 모듈·store가 모두 여기서 도출한다(이중 리터럴 금지).
- `firestore.rules`: item_vectors는 공개 read, 클라이언트 write 금지(다른 수집
  컬렉션과 동일 패턴).
- TTL 정책: `expire_at` 필드 TTL을 item_vectors 컬렉션 그룹에 활성화한다. 기존
  절차(setup.md §7의 gcloud `fields ttl update`) 목록에 컬렉션만 추가한다.
  firestore-contract.md의 TTL 규칙 표에는 "item_vectors = 원본 item의 expire_at
  미러링" 예외를 price_bars(바 날짜 기준)처럼 명시한다.
- **모델 교체는 단방향 문이다**: 다운스트림이 embed_model 계약에 의존하기 시작하면
  모델·차원 변경은 전량 재임베딩 + 다운스트림 협응이 필요하다. `embed_model` 필드가
  mismatch 감지 수단이며, 교체 시에는 재임베딩 완료 후 모델명을 일괄 전환하는 절차를
  밟는다(이 비가역성을 인지하고 결정했다).

### 대기열 — item 문서의 `embed_pending` 플래그

- `_to_doc`(수집 시점)에서 `classify_kind` 결과가 `story`인 기사에만
  `embed_pending: true`를 박는다. 비-story에는 필드 자체를 만들지 않는다 —
  Firestore는 "필드 없음"을 쿼리할 수 없으므로, 플래그의 존재 자체가 "임베딩 대상이며
  아직 안 됨"을 뜻하게 설계한다(단일 equality 쿼리로 대기분 조회, 복합 인덱스 불필요).
- 이 플래그는 임베딩 완료 시 제거되는 **과도기 boolean**이며, 그 전까지 공개 read인
  items 문서에 노출된다. 백엔드 처리 상태의 경미한 노출은 수용한다(웹 파서는 미지
  필드를 무시한다). firestore-contract.md에 transient 필드로 명시한다.
- 재시도 가능한 실패(429·5xx·네트워크)는 플래그가 남아 다음 런이 자동 재시도한다.
  **재시도 무의미한 항목 귀속 실패는 좀비가 되지 않게 즉시 처분한다**: 빈 임베딩 입력
  (title+body가 공백뿐)과 400(입력 문제)은 error 로그와 함께 플래그만 제거하고
  벡터를 쓰지 않는다 — 매 런 쿼터를 태우는 영구 재시도를 막는다.
  **항목 귀속이 아닌 비일시 오류(401/403 인증, 404 모델명, 차원 불일치)는 항목
  처분하지 않고 패스 전체 실패로 승격한다** — 전 항목 공통의 설정 드리프트를 항목별로
  처분하면 백로그 전체의 플래그가 조용히 걷혀 무임베딩이 고착된다(구현 리뷰 반영).

### 임베딩 패스 — collector 잡 내 후처리

```
run_collect: collect_once(수집·저장) → embed_pass(store, embedder, cap) → 요약 로그·종료코드
```

- `embed_pass`는 `items where embed_pending == true`를 **런당 상한(cap, 기본 500건)**
  까지 읽어(id·title·body·expire_at), 병렬 임베딩(과거와 동일하게 동시 50, 순서 보존)
  후 store에 저장을 위임한다. 남은 대기분은 다음 런이 이어서 소화한다.
  - 상한의 근거: collector Cloud Run 잡은 task-timeout 600초·**5분 주기**
    (operations.md의 `newsstore-5min`)로 돈다. 상한이 없으면 백필 직후 수만 건
    백로그를 한 런이 물고 늘어지다 타임아웃으로 강제 종료되고, 다음 런이 같은 전량을
    다시 시도하는 낭비가 반복된다. 500건 × 동시 50은 런 시간 여유 안에서 끝난다고
    추정하되, 같은 600초 예산을 선행 collect_once가 분점하므로 **배포 시 실측**으로
    (collect 소요 + 임베딩 처리량 × cap) < task-timeout을 확인하고 필요하면 cap을
    조정한다(MEASURE-FIRST). 백로그는 여러 런에 걸쳐 단조 감소한다.
  - 런이 5분을 넘겨 실행이 겹치면 같은 기사를 이중 임베딩할 수 있다 — 결과는
    멱등(같은 문서 덮어쓰기)이고 쿼터만 2배 소모하는 트레이드오프로, cap이 런 시간을
    5분 안쪽으로 눌러 실질 발생을 막는다.
- **실패 격리(FAIL-LOUD와의 균형)**:
  - 기사 단위 실패는 그 기사만 건너뛴다. 재시도 가능/불가 처분은 위 대기열 절 규칙을
    따른다.
  - 패스 전체 실패(인증 오류 등 설정 드리프트)는 수집 결과를 보존한 채 **종료 코드 1**
    로 끝낸다 — 스케줄러가 런 실패로 감지한다(조용한 무임베딩 고착 방지). 재시도로
    수집이 다시 돌아도 upsert_items가 기존 id를 덮어쓰지 않으므로(멱등) 안전하다.
  - **키 부재의 fail-loud는 "대기분이 실재할 때"로 좁힌다**: GEMINI_API_KEY 없이
    대기분이 있으면 exit 1, 대기분 0건이면 경고 로그 후 exit 0 — 키 없는 로컬 수집
    스모크(`docker compose run collect`)를 깨지 않으면서 프로덕션 드리프트는 잡는다.
  - run_collect의 종료 코드 합성: 기존 피드 실패율(FAIL_RATE_ALERT) **또는** 임베딩
    패스 전체 실패 중 하나라도 걸리면 1이다.

### 임베딩 클라이언트 — `src/newsstore/embed/`

main 히스토리(ca8840a)의 검증된 코드를 **embed 전용으로 축소 복원**한다.

- `embedder.py`: `BODY_CAP = 500`, `embed_text()`, `embed_items()`(ThreadPoolExecutor
  동시 50, 순서 보존). 차원 상수는 `contracts/embedding.py`의 `EMBED_DIM`을 참조한다.
  과거 코드와 달리 기사 단위 실패를 예외로 전파하지 않고, **항목별 결과를 3분류로
  돌려준다** — 성공(벡터), 영구 실패(사유: 빈 입력·400), 재시도 가능 실패
  (429·5xx·네트워크). 설정 드리프트(401/403·404·차원 불일치)는 예외로 전파해 패스
  전체 실패로 승격한다(위 대기열 절). embed_pass가 이 분류로 clear_embed_pending
  대상과 플래그 유지 대상을 결정론적으로 가른다(성공만 반환하면 실패 종별 정보가
  소실되어 좀비 처분이 불가능하다).
- `gemini.py`: `google-genai` 기반 embed 전용 클라이언트 — 과거 gemini.py의 embed
  경로 그대로: `models.embed_content(model=EMBED_MODEL, contents=text,
  config=types.EmbedContentConfig(output_dimensionality=EMBED_DIM))` + lazy import +
  일시 오류 재시도 래퍼(call_with_retry). 재시도는 5xx·네트워크·429를 지수 백오프로
  다루되, 429는 동시 50과 결합해 폭주하지 않도록 지터를 둔다. generate_json·complete는
  복원하지 않는다(YAGNI).
- `contracts/ports.py`의 Store Protocol에 두 메서드를 추가한다:
  - `get_pending_embed_items(limit) -> list[PendingItem]` —
    `PendingItem = TypedDict(item_id, title, body, expire_at)`.
  - `save_vectors(entries) -> int` — `VectorEntry = TypedDict(item_id, vector,
    expire_at)`를 받아 item_vectors 문서 set + 원본 embed_pending 해제(DELETE_FIELD)를
    **같은 batch**(250건 × 2op = 500 op 한도)로 커밋한다. 청킹은 기존
    save_docs·save_bars 관례대로 store 내부가 소유한다. embed_model·embedded_at은
    store가 주입한다(호출자 미제공 — 단일 통제점 유지). 반환은 쓴 수.
  - `clear_embed_pending(ids)` — 재시도 무의미 실패의 플래그 처분용.
  - **만료 경계 처리**: batch 커밋이 원본 문서 부재(TTL 삭제 경합)로 NotFound를 내면
    batch 전체가 롤백되므로, 그 청크는 항목 단위로 재커밋해 부재 항목만 건너뛴다 —
    한 건의 만료가 나머지 249건의 벡터를 날리지 않게 한다.

### 비밀·의존성

- `GEMINI_API_KEY`는 **백엔드 전용 비밀**로 재도입한다. `.env.example`에는
  플레이스홀더만, 프로덕션은 collector 잡 env(Secret Manager)에만 주입한다.
  prices·fundamentals 잡에는 넣지 않는다.
- `google-genai`는 과거 구조대로 **optional extra**(`embed = ["google-genai>=1.0"]`)
  + lazy import로 복원한다 — 미설치 환경에서도 import·테스트가 가능한 속성을 보존한다.
- **프로덕션 설치 경로를 명시적으로 배선한다**(lock 포함만으로는 설치되지 않는다 —
  `-c requirements.lock`은 버전 제약일 뿐 설치 트리거가 아니다): `infra/Dockerfile`의
  EXTRAS 조립에 embed를 추가해 프로덕션(gcp) 빌드가 `.[gcp,embed]`를 설치하게 하고,
  `infra/requirements.lock` 재생성 명령도 `.[dev,gcp,embed]`로 갱신해 google-genai가
  lock과 이미지 양쪽에 실제로 들어가게 한다.

### 백필 (일회성)

- `scripts/backfill_embed_pending.py`(Docker로 실행): TTL 윈도우 안의
  `kind == "story"` 기사 중 item_vectors에 벡터가 없는 것들에 `embed_pending: true`를
  마킹한다. 단, **잔여 수명 2일 미만인 기사는 제외**한다 — 곧 만료될 벡터에 백필
  쿼터를 쓰지 않고, 만료 경합(위 NotFound 케이스) 창도 줄인다.
- 실제 임베딩은 정규 임베딩 패스가 소화한다 — 임베딩 경로가 한 벌만 존재한다(SSOT).
  마킹 후 스크립트가 `embed_pass`를 **대기분 0이 될 때까지 반복 호출**해 즉시
  소진시킬 수 있다(같은 함수 재사용 — 5분 주기를 기다릴 필요 없음). 로컬 실행이라
  Cloud Run task-timeout의 제약을 받지 않는다. 단, 재시도 가능 실패가 지속되면
  대기분이 0이 안 될 수 있으므로 **무진전 가드**를 둔다: 연속 2회 호출에서 남은
  대기분이 줄지 않으면 중단하고 잔여 건수를 로그로 남긴다(잔여분은 정규 5분 주기가
  이어받는다).
- 멱등: 이미 벡터가 있으면 건너뛰고, 재실행해도 결과가 같다.
- 백필 규모는 문서로 단정하지 않는다 — 배포 시점에 items의 story 건수를 실측해
  (MEASURE-FIRST) 소진 시간을 확인한다. cap·반복 호출 구조라 규모와 무관하게 안전하다.

## 웹·대시보드

변경 없다. item_vectors는 웹이 읽지 않는다.

## 문서 갱신

- `docs/firestore-contract.md`: item_vectors 스키마·TTL 미러링 예외·임베딩 입력 규칙·
  embed_pending(transient·공개 노출 수용) 계약.
- `docs/operations.md`: GEMINI_API_KEY 시크릿(collector 잡), item_vectors TTL
  프로비저닝, 백필 실행 절차, 재배포 경로(이미지 재빌드 → collector 잡 update).
- `docs/setup.md`: 최초 셋업에 시크릿·TTL 추가.
- `README.md`·`CLAUDE.md`: 스코프 문장 정정("생성형 LLM 배제, 임베딩 벡터 계산만 예외").
- `.env.example`: GEMINI_API_KEY 플레이스홀더 추가(인라인 주석 금지 관례 준수).

## 테스트 (TDD — 구현 전 실패 테스트부터)

- store(에뮬레이터): story만 embed_pending이 박히는지, get_pending_embed_items의
  limit 준수, save_vectors 후 벡터 존재·embed_model 주입·플래그 제거·expire_at
  미러링, 원본 부재 항목이 섞인 batch에서 나머지가 저장되는지(NotFound 격리),
  clear_embed_pending, 재실행 멱등성.
- embedder(단위, mock 클라이언트): embed_text 조립(BODY_CAP), 항목별 3분류 반환
  (성공 벡터/영구 실패 사유/재시도 가능 실패 — 빈 입력·400은 영구, 차원 불일치·
  401은 패스 승격), 순서 보존.
- embed_pass(통합, 에뮬레이터 + mock 클라이언트): 성공/재시도가능실패/영구실패 혼재
  시 성공분 벡터 저장·재시도분 플래그 잔존·영구실패분 플래그 제거, cap 준수(잔여
  대기분 유지), 빈 입력 처분.
- backfill(에뮬레이터): 마킹 대상 선정(story ∧ 벡터 없음 ∧ 잔여 수명 ≥ 2일), 멱등성
  (재실행 시 추가 마킹 없음).
- run_collect 통합: 임베딩 실패 시 수집 결과 보존, 키 부재 × 대기분 존재 → exit 1,
  키 부재 × 대기분 0건 → exit 0, 피드 실패율과 임베딩 실패의 종료 코드 합성.
- 계약 테스트: firestore.rules에 item_vectors 공개 read 존재(test_index_contract 패턴).

## 기각한 대안

- **item 문서에 embedding 필드(옛 설계)**: 공개 웹 피드 80건 로드마다 약 0.5MB가
  추가된다. 웹 클라이언트 SDK는 필드 선택이 불가해 회피 수단이 없다.
- **별도 Cloud Run 잡**: 장애 격리는 깔끔하나 잡·스케줄러·배포 절차가 하나 더 늘어난다.
  collector 내 후처리 패스로도 격리 목표(수집 불차단·자동 재시도)를 달성한다.
- **Firestore 네이티브 Vector 타입 + KNN**: 다운스트림이 전량 다운로드해 쓰는 구도라
  서버측 KNN 수요가 아직 없다(YAGNI). 배열 필드가 다운스트림 파싱에도 단순하다.
  수요가 생기면 마이그레이션 가능(REVERSIBLE).
- **inline 임베딩(저장 직전)**: 코드가 가장 단순하나 Gemini 장애가 뉴스 수집을
  지연·차단한다. 수집이 이 저장소의 핵심 책무라 기각.
- **런당 처리 상한 없음(초안)**: 리뷰에서 기각 — task-timeout 600초·5분 주기와
  충돌해 백필 중 타임아웃 반복(thrash)을 만든다. cap + 다음 런 이어받기 + 백필
  스크립트의 반복 호출로 대체했다.

<!-- spec-review: passed -->
