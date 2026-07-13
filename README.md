# newsstore

무료 RSS 피드를 5분마다 수집하고 시장 가격·펀더멘털(FMP)을 수집해 **Firestore**에 중복 제거 저장하고, **공개 웹사이트**로 보여주는 **수집 전용** 데이터 모듈. (`daytrade_assist`의 뉴스·시장 데이터 모듈 — 별개 자기완결 repo)

- **사이트:** https://daily-recap-498506.web.app
- **GitHub:** https://github.com/chshin84/newsstore (public)
- **수집 전용, 무LLM.** 분석·태깅·임베딩·클러스터·스토리·리포트·신호 같은 인리치 레이어는 이 repo에 없다. 필터는 LLM이 아니라 **비-LLM 규칙**(중복 제거 + 스팸·스포츠·다이제스트 키워드 분류)이다.
- **모든 content 데이터에 1개월 TTL**을 걸어 Firestore 비용을 통제한다(`items`·`prices`·`fundamentals`의 `expire_at`; `feed_state` 제외). 계약 SSOT: `docs/firestore-contract.md`.

## 아키텍처

```
Cloud Scheduler (*/5분)   → Cloud Run Job (뉴스 수집 1패스)      → Firestore: items, feed_state, meta
Cloud Scheduler (시간당)  → Cloud Run Job (가격 수집, FMP+Yahoo) → Firestore: prices
Cloud Scheduler (일 1회)  → Cloud Run Job (펀더멘털 수집, FMP)   → Firestore: fundamentals
Firebase Hosting (web/index.html, 정적)
   └─ 브라우저가 Firestore JS SDK로 items/prices 직접 읽기(공개 read 규칙) → 목록/소스필터 렌더
```

- 전부 한 GCP 프로젝트 `daily-recap-498506` (리전 `asia-northeast3` 서울).
- 세 수집 Job은 같은 이미지를 쓰고 CMD만 다르다. Admin SDK라 보안규칙 우회. 사이트는 **읽기 전용**.
- 인증은 IAM 바인딩(서비스계정 `newsstore-job`, role `datastore.user`) — **키 파일 없음**.
- 가격·펀더멘털은 FMP REST를 호출하므로 `FMP_API_KEY`(백엔드 전용 비밀)가 필요하다 — Secret Manager로 주입.

## 환경 변수 (두 축)

| 키 | 값 | 의미 |
|----|----|------|
| **`APP_ENV`** | `home` \| `office` | **보안 환경.** `home`=집, 기본 SSL 검증. `office`=회사 ePrism TLS 프록시 → 루트 CA `ePrism-SSL-ROOT-CA.crt`를 이미지에 주입(.crt는 git 제외, 회사 PC에만). 클라우드(Cloud Run)는 `home`. |
| **`FIRESTORE_EMULATOR_HOST`** | `host:8080` | **저장소=Firestore 단일.** 설정 시 로컬/테스트가 에뮬레이터에 붙음(`docker compose`가 자동 설정). 미설정=실 Firestore. sqlite 백엔드 제거됨. |
| `GOOGLE_CLOUD_PROJECT` | `daily-recap-498506` | 타겟 GCP/Firestore 프로젝트 ID (배포 공통; 에뮬레이터는 `test`) |
| `GCP_REGION` | `asia-northeast3` | 배포/셋업 리전 (`docs/setup.md`·`operations.md`) |
| **`FMP_API_KEY`** | (비밀) | **백엔드 전용 비밀.** 가격·펀더멘털 수집(FMP REST)에 필요. 커밋/클라이언트 노출 금지 — `.env`(로컬)·Secret Manager(클라우드). `.env.example`엔 플레이스홀더만. |

→ **모든 값은 루트 `.env` 한 곳에서 관리.** `cp .env.example .env` 로 만들고 값만 바꾸면 됨(타겟 프로젝트 변경 = `GOOGLE_CLOUD_PROJECT` 한 줄). Docker 실행은 `--env-file .env`.

조합 예:
- **로컬 테스트** → `docker compose run --rm test` (Firestore 에뮬레이터 자동)
- **클라우드(Cloud Run Job)** → `APP_ENV=home` + `GOOGLE_CLOUD_PROJECT=daily-recap-498506` (실 Firestore)
- **회사에서 로컬** → `APP_ENV=office`

## 로컬 실행 (Docker only — 호스트에 로컬 Python 없음)

```bash
cp .env.example .env          # 값 확인/수정 (APP_ENV, GOOGLE_CLOUD_PROJECT, …)
docker build -f infra/Dockerfile -t newsstore .

# 1회 뉴스 수집 (.env 설정 사용, named volume로 영속)
docker run --rm --env-file .env -v newsstore_data:/data newsstore \
  python -m newsstore.entrypoints.run_collect --force
```
가격·펀더멘털 수집(FMP)은 compose 서비스로도 돌린다(`FMP_API_KEY` 필요):
```bash
docker compose run --rm prices          # 지수·환율·국채 (FMP + Yahoo 폴백)
docker compose run --rm fundamentals    # 티커별 재무제표 (FMP)
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

## 문서
- 최초 셋업(0→배포): `docs/setup.md` · 운영·재배포: `docs/operations.md`
- Firestore 스키마 계약(TTL·kind·FMP 소스): `docs/firestore-contract.md`
- 코드 원칙: `docs/coding-principles.md` · 설계 스펙 히스토리: `docs/superpowers/specs/`
