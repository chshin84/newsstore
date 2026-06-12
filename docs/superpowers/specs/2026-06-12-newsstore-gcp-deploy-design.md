# newsstore — GCP 배포 + 뷰어 사이트 설계

_작성: 2026-06-12 · 상태: 승인됨, 구현 계획 대기_

## 1. 목표 / 범위

Step-1 수집기를 **Google Cloud에서 5분마다 자동 실행**하여 **Firestore**에 저장하고,
들어온 뉴스를 보는 **공개 정적 사이트**를 띄운다.

**포함:** 스케줄러, Firestore 스토어, 클라우드 배포, 뷰어 사이트.
**불포함(별개 작업):** Step-2 LLM 태깅, Step-4 아키타입. 단 사이트의 태그 드롭다운은 Step-2가 생기면 자동으로 채워지도록 자리만 잡는다.

### 호스팅 결정 (= "가장 깔끔한" 올구글)
- **Cloud Run Job** — 수집기(한 번 돌고 끝나는 작업)
- **Cloud Scheduler** — `*/5 * * * *`로 Job 트리거
- **Firestore (Native)** — DB
- **Firebase Hosting** — 정적 사이트
- 핵심 이점: **서비스계정 JSON 키 파일이 없음.** Cloud Run에 IAM 권한만 바인딩 → 키 유출 관리 부담·타 플랫폼 환경변수 주입이 사라짐. 한 프로젝트·한 청구서.
- 비용: Firestore 무료티어(1GB 저장 / 5만 읽기·2만 쓰기 일) + Cloud Run scale-to-zero + Scheduler 무료(3잡) → 이 볼륨이면 사실상 $0.

## 2. 데이터 흐름

```
Cloud Scheduler (*/5분)
   └─ HTTP/trigger → Cloud Run Job (collector 1패스)
                        └─ FirestoreStore → Firestore: items, feed_state
Firebase Hosting (index.html)
   └─ 브라우저 Firestore JS SDK → items 읽기(공개 read 규칙) → 목록/드롭다운 렌더
```

## 3. Firestore 데이터 모델

### 컬렉션 `items/{id}`
`id` = 기존 `make_id()` sha1.

| 필드 | 타입 | 비고 |
|------|------|------|
| feed_id, source, asset_hint, language, url, title, body | string | RawItem 그대로 |
| published_at, fetched_at | **timestamp** | 정렬용 네이티브 타임스탬프 (ISO 문자열 아님) |
| processed | bool = `false` | Step-2 핸드오프 계약 |
| processed_at | timestamp \| null | |
| tags | array\<string\> = `[]` | Step-2가 채움; 드롭다운 쿼리 대상 |

### 컬렉션 `feed_state/{feed_id}`
`etag, last_modified, last_fetched(timestamp)` — 조건부 GET 상태. Job이 매번 새로 떠도 Firestore에 남아 유지.

### Dedup 규칙 (중요)
- 신규 아이템은 문서 id로 **`create()`** 시도 → `AlreadyExists`면 skip(신규 카운트 미가산).
- **기존 문서를 덮어쓰지 않는다.** 재수집돼도 `processed`/`tags`가 보존됨. (`set(merge=True)`로 메타만 갱신도 금지 — 단순 create-or-skip.)

### 보안 규칙
```
match /items/{id}      { allow read: if true;  allow write: if false; }
match /feed_state/{id} { allow read: if false; allow write: if false; }
```
수집기는 Admin SDK라 규칙을 우회한다(클라이언트만 규칙 적용). 사이트는 `items`만 읽는다.

### 인덱스 (복합)
1. `items`: `published_at DESC` — 필터 없는 최근 N
2. `items`: `tags array-contains` + `published_at DESC` — 드롭다운 필터

## 4. 수집기 코드 변경 (최소·격리)

- **새 파일** `src/newsstore/store/firestore_store.py` — `FirestoreStore`가 기존 `Store` Protocol 7개 메서드 구현:
  `upsert_items / get_feed_state / set_feed_state / count / get_unprocessed / mark_processed`.
  - `google-cloud-firestore` Admin SDK 사용.
  - `upsert_items`: 배치 `create()`, `AlreadyExists` 카운트 제외 → 신규 수 반환.
  - `get_unprocessed`: `where('processed','==',false).order_by('fetched_at').limit(n)`.
  - `mark_processed`: 배치 update `processed=true, processed_at`.
- **`run.py`**: `NEWSSTORE_BACKEND` 환경변수로 스토어 선택.
  - `sqlite`(기본) → 기존 `SqliteStore`. 로컬/테스트는 변동 없음.
  - `firestore` → `FirestoreStore(project=…)`. 클라우드(Cloud Run Job)에서만 사용.
- **모델**: `RawItem`은 그대로. `processed`/`tags`는 스토어 레이어의 문서 필드로만 존재(모델 미오염).
- 의존성: `pyproject.toml`에 `google-cloud-firestore` 추가(클라우드 빌드용). 로컬 sqlite 경로엔 불필요하므로 optional extra로 분리 고려(`[gcp]`).

## 5. 배포 런북 (사용자 수행 단계)

1. GCP 프로젝트 생성 → **Firestore Native 모드** 활성화 (리전: asia-northeast3 서울 권장).
2. 컬렉터 이미지 빌드/푸시 → **Cloud Run Job** 생성 (env: `NEWSSTORE_BACKEND=firestore`, `GOOGLE_CLOUD_PROJECT=…`).
3. **Cloud Scheduler** 잡 생성: `*/5 * * * *` → Cloud Run Job 실행 트리거. Job 실행용 서비스계정에 `run.invoker`.
4. Cloud Run Job 서비스계정에 **`roles/datastore.user`** 바인딩 (Firestore 읽기/쓰기). ← 키 파일 없음.
5. **보안 규칙 + 인덱스** 배포 (`firebase deploy --only firestore:rules,firestore:indexes`).
6. 정적 사이트 → **Firebase Hosting** 배포 (`firebase deploy --only hosting`).

## 6. 뷰어 사이트

- **단일 `index.html` + 바닐라 JS + Firebase JS SDK** (web/ 디렉토리). 프레임워크 없음 — Firestore SDK 학습 집중.
- Firebase 웹 config(공개 apiKey 등)는 정적 파일에 포함(공개 read 전용이라 안전).
- UI:
  - 상단 **태그 드롭다운**: 현재 옵션 `전체`만(Step-2 후 태그 채워짐). 선택 시 `array-contains` 쿼리.
  - **최근 N개**(기본 50) 뉴스 카드: 제목(→url 링크), source, published_at(상대시각).
  - 쿼리: `collection('items').orderBy('published_at','desc').limit(N)` (+ 태그 선택 시 `where`).

## 7. 테스트 / 에러 처리 / 롤아웃

### 테스트
- 기존 Protocol/수집기 테스트는 **SqliteStore**로 계속(Docker, 빠름) — 회귀 보호 유지.
- `FirestoreStore`는 **Firestore 에뮬레이터** 기반 스모크 테스트 1개(create-or-skip dedup, get_unprocessed, mark_processed 라운드트립).

### 에러 처리
- 기존 `run.py`의 feed별 격리 + 실패율 exit code 유지 → Cloud Scheduler가 실패 인지.
- Firestore 일시 오류: SDK 기본 재시도. 패스 단위 실패는 다음 5분 패스에서 자연 복구(조건부 GET 상태가 남아 중복 최소).

### 롤아웃 순서 (각 단계 독립 검증)
1. `FirestoreStore` + env 스위치 (에뮬레이터 테스트 그린)
2. 컨테이너를 Cloud Run Job으로 배포 → **수동 1회 실행** → Firestore 콘솔에서 items 확인
3. Cloud Scheduler 5분 트리거 연결 → 두 패스 후 신규/중복 동작 확인
4. 보안 규칙 + 인덱스 배포
5. 정적 사이트 Firebase Hosting 배포 → 공개 URL에서 목록 확인

## 8. 결정 사항 (확정)

- SQLite는 **테스트/로컬용으로 유지**, Firestore는 **클라우드 스토어로 추가**(완전 제거 아님).
- 태그 드롭다운은 Step-2 전엔 `전체`만 — 그래도 지금 배포.
- 데이터 보존: **무한 누적**(TTL 없음). 일 볼륨 수 MB 수준, Firestore 무료 1GB라 장기 여유. 필요 시 후속으로 TTL 정책 추가.

## 9. 환경 Gotchas (유지)

- 호스트에 로컬 Python 없음 → 로컬 실행/테스트는 Docker.
- infomax 5피드 naive-KST pubDate → `tz_offset:9` 보정(기존 로직).
- 사무실 ePrism 프록시 ↔ Firestore gRPC 충돌 우려는 **수집기를 클라우드에서 돌려 회피**(회사 PC에서 Firestore 직접 쓰기 안 함).
