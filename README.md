# newsstore

무료 RSS 피드를 5분마다 수집해 **Firestore**에 중복 제거 저장하고, **공개 웹사이트**로 보여주는 뉴스 데이터 모듈. (`daytrade_assist`의 뉴스 데이터 모듈 — 별개 자기완결 repo)

- **라이브 사이트:** https://daily-recap-498506.web.app
- **GitHub:** https://github.com/chshin84/newsstore (public)
- Step-1(수집)·저장·뷰어 라이브. **인리치먼트(LLM 태깅·임베딩·클러스터·스토리·점수)는 별개 repo `news-analytics` 소유** — newsstore와는 **Firestore 스키마로만** 만난다(경계·계약 SSOT: `docs/firestore-contract.md`). 과도기로 코드는 아직 newsstore에 잔류(§진행 상황).

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
| **`FIRESTORE_EMULATOR_HOST`** | `host:8080` | **저장소=Firestore 단일.** 설정 시 로컬/테스트가 에뮬레이터에 붙음(`docker compose`가 자동 설정). 미설정=실 Firestore. sqlite 백엔드 제거됨. |
| `GOOGLE_CLOUD_PROJECT` | `daily-recap-498506` | 타겟 GCP/Firestore 프로젝트 ID (배포 공통; 에뮬레이터는 `test`) |
| `GCP_REGION` | `asia-northeast3` | 배포/셋업 리전 (`docs/setup.md`·`operations.md`) |

→ **모든 값은 루트 `.env` 한 곳에서 관리.** `cp .env.example .env` 로 만들고 값만 바꾸면 됨(타겟 프로젝트 변경 = `GOOGLE_CLOUD_PROJECT` 한 줄). Docker 실행은 `--env-file .env`.

조합 예:
- **로컬 테스트** → `docker compose run --rm test` (Firestore 에뮬레이터 자동)
- **클라우드(Cloud Run Job)** → `APP_ENV=home` + `GOOGLE_CLOUD_PROJECT=daily-recap-498506` (실 Firestore)
- **회사에서 로컬** → `APP_ENV=office`

## 로컬 실행 (Docker only — 호스트에 로컬 Python 없음)

```bash
cp .env.example .env          # 값 확인/수정 (APP_ENV, NEWSSTORE_BACKEND, …)
docker build -f infra/Dockerfile -t newsstore .

# 1회 수집 (.env 설정 사용, named volume로 영속)
docker run --rm --env-file .env -v newsstore_data:/data newsstore \
  python -m newsstore.entrypoints.run_collect --force
```

### 테스트
**Firestore 에뮬레이터를 자동 기동**해 store 테스트를 실 client 계약대로 검증(mock-firestore·sqlite 제거):
```bash
MSYS_NO_PATHCONV=1 docker compose run --rm test
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
- 🔀 **인리치먼트(태깅/스토리/점수) → `news-analytics` repo 소유.** Cloud Run Job#2(`newsstore-enricher`)·#3(`newsstore-summarizer`)는 **라이브**이나 **과도기로 newsstore 이미지에서 운영 중**(`docs/operations.md §E·§F`). 코드 물리 이전(`src/newsstore/enrich/` 디렉터리·`ports.py` 분할)은 별도 작업. 경계·계약: `docs/firestore-contract.md`.

## 문서
- 로드맵(Step 1~7): `docs/roadmap.md`
- 최초 셋업(0→배포): `docs/setup.md` · 운영·재배포: `docs/operations.md`
- 설계: `docs/superpowers/specs/` · 구현계획: `docs/superpowers/plans/`
- **분할 경계·계약(newsstore ↔ news-analytics): `docs/firestore-contract.md`** (Firestore 스키마 SSOT + 스펙/플랜 소유권 인덱스)
- 소스 선택 근거(히스토리): `docs/handoff/2026-06-12-session-handoff.md`
