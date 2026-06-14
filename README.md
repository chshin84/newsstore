# newsstore

무료 RSS 피드를 5분마다 수집해 **Firestore**에 중복 제거 저장하고, **공개 웹사이트**로 보여주는 뉴스 데이터 모듈. (`daytrade_assist`의 뉴스 데이터 모듈 — 별개 자기완결 repo)

- **라이브 사이트:** https://daily-recap-498506.web.app
- **GitHub:** https://github.com/chshin84/newsstore (public)
- Step-1(수집)·저장·뷰어 라이브. Step-2 인리치먼트는 진행 중 — enrich 모듈(휴리스틱 분류/클러스터 순수로직)·Store 확장 완료, LLM(Gemini) 태깅·임베딩 런타임 연결은 다음(Plan 3/4). 자세한 진행은 아래 §진행 상황.

## 아키텍처

```
Cloud Scheduler (*/5분)
   └─ trigger → Cloud Run Job  (수집기 1패스)
                   └─ FirestoreStore → Firestore: items, feed_state
Firebase Hosting (web/index.html, 정적)
   └─ 브라우저가 Firestore JS SDK로 items 직접 읽기(공개 read 규칙) → 목록/소스필터 렌더
```

- 전부 한 GCP 프로젝트 `daily-recap-498506` (리전 `asia-northeast3` 서울).
- 수집기는 Admin SDK라 보안규칙 우회. 사이트는 `items` **읽기 전용**.
- 인증은 IAM 바인딩(서비스계정 `newsstore-job`, role `datastore.user`) — **키 파일 없음**.

## 환경 변수 (두 축)

| 키 | 값 | 의미 |
|----|----|------|
| **`APP_ENV`** | `home` \| `office` | **보안 환경.** `home`=집, 기본 SSL 검증. `office`=회사 ePrism TLS 프록시 → 루트 CA `ePrism-SSL-ROOT-CA.crt`를 이미지에 주입(.crt는 git 제외, 회사 PC에만). 클라우드(Cloud Run)는 `home`. |
| **`NEWSSTORE_BACKEND`** | `sqlite` \| `firestore` | **저장소 환경.** `sqlite`(기본)=로컬·집 테스트(파일 `data/newsstore.db`). `firestore`=클라우드 저장. 코드는 동일, 토글만. |
| `GOOGLE_CLOUD_PROJECT` | `daily-recap-498506` | 타겟 GCP/Firestore 프로젝트 ID (firestore 백엔드 + 배포 공통) |
| `NEWSSTORE_DB` | 경로 | sqlite DB 경로 (기본 `/data/newsstore.db`) |
| `GCP_REGION` | `asia-northeast3` | 배포/셋업 리전 (`docs/setup.md`·`operations.md`) |

→ **모든 값은 루트 `.env` 한 곳에서 관리.** `cp .env.example .env` 로 만들고 값만 바꾸면 됨(타겟 프로젝트 변경 = `GOOGLE_CLOUD_PROJECT` 한 줄). Docker 실행은 `--env-file .env`.

조합 예:
- **집에서 로컬 테스트** → `APP_ENV=home` + `NEWSSTORE_BACKEND=sqlite` (아무것도 안 set해도 기본값)
- **클라우드(Cloud Run Job)** → `APP_ENV=home` + `NEWSSTORE_BACKEND=firestore` + `GOOGLE_CLOUD_PROJECT=daily-recap-498506`
- **회사에서 로컬** → `APP_ENV=office` + `NEWSSTORE_BACKEND=sqlite`

## 로컬 실행 (Docker only — 호스트에 로컬 Python 없음)

```bash
cp .env.example .env          # 값 확인/수정 (APP_ENV, NEWSSTORE_BACKEND, …)
docker build -f infra/Dockerfile -t newsstore .

# 1회 수집 (.env 설정 사용, named volume로 영속)
docker run --rm --env-file .env -v newsstore_data:/data newsstore \
  python -m newsstore.run --force
```

### 테스트
호스트 Git Bash가 `${PWD}`를 망가뜨려 마운트가 stale 이미지로 폴백되니(테스트 수가 틀리게 나옴) **이 형태로** 실행:
```bash
MSYS_NO_PATHCONV=1 docker run --rm -v "D:/projects/newsstore:/app" newsstore pytest -q
```

## 셋업 / 재배포 / 운영
- **최초 0→배포 셋업**(새 프로젝트·재해복구·복제): **`docs/setup.md`** (gcloud + REST만으로 전체 프로비저닝)
- **변경 반영**(피드·코드·사이트 수정 후): **`docs/operations.md`** (이미지 재빌드 → Job 갱신 / Hosting REST 배포 / 인덱스·규칙)

## 피드 레지스트리
`config/feeds.yaml` — 한국(인포맥스·한경·매경), 미국주식(Benzinga), 크립토(CoinDesk·Cointelegraph), FX/금리(InvestingLive·Investing·Fed·ECB), **Bloomberg(markets/technology/economics/business/politics/opinion/crypto/wealth + Flipboard Korea)**, Reuters(Google News 경유), Google News(루머·KR칩), TruthSocial, Axios.
- 피드 추가/변경은 이미지에 `COPY` 되므로 **재빌드+Job 갱신** 필요.

## 진행 상황
- ✅ **Step-1 수집기**: 완료·배포·라이브 (Cloud Run Job + Scheduler */5 → Firestore).
- ✅ **공개 사이트**: 라이브 (소스 필터·중복제거·스팸필터·소스별 색·호버 본문).
- 🚧 **Step-2 (LLM 태깅/스토리)**: 진행 중.
  - ✅ Plan 1 — `src/newsstore/enrich/`(taxonomy·classify·cluster, 휴리스틱 분류 + centroid 클러스터 순수로직).
  - ✅ Plan 2 — Store 확장: `save_enrichment`(kind/tags/embedding/story_id) + `stories`(centroid sum/count·get_open·close_stale), sqlite/firestore 양쪽.
  - ✅ Plan 3 — Gemini 태깅(`tagger`, 결정론 어휘/티커 검증)·임베딩(`embedder`, 768 dim 가드)·LLM 클라이언트(`llm`, timeout/retry/None가드). DI라 google-genai 없이 로직 테스트.
  - ✅ Plan 4 (로직) — `enrich/processor.py`(get_unprocessed→classify→tag+embed→클러스터→save+mark) + `process.py` 엔트리포인트. **배포(Cloud Run Job#2 + GEMINI_API_KEY)는 사용자 게이트** — `docs/operations.md §E`. 배포되면 사이트 태그 드롭다운 자동 활성.

## 문서
- 로드맵(Step 1~7): `docs/roadmap.md`
- 최초 셋업(0→배포): `docs/setup.md` · 운영·재배포: `docs/operations.md`
- 설계: `docs/superpowers/specs/` · 구현계획: `docs/superpowers/plans/`
- 소스 선택 근거(히스토리): `docs/handoff/2026-06-12-session-handoff.md`
