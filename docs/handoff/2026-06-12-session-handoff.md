# newsstore — 세션 핸드오프 (2026-06-12)

> ⚠️ **SUPERSEDED (낡음).** §1~3(상태·미완성·다음할일)은 옛 시점 기준이라 **틀림** — 그 사이
> 스케줄러·Firestore·GCP 배포·공개 사이트가 **전부 완료·라이브**됐다(https://daily-recap-498506.web.app).
> **현재 상태·실행법은 `README.md` / `docs/operations.md` / 메모리 참조.**
> 이 문서는 **소스 선택 이유·결정 기록(§4~6)** 보존용으로만 남긴다.

이 문서 하나로 **집(또는 다른 PC)에서 이어서 작업**할 수 있게 만든 핸드오프다.
전체 대화 흐름 + 현재 상태 + 정직한 미완성 항목 + 다음 할 일 + 환경 셋업을 담는다.

---

## 0. 지금 당장 집에서 이어가기 (TL;DR)

```bash
git clone https://github.com/chshin84/newsstore.git
cd newsstore
# 집 환경 설정 (ePrism 프록시 없음)
cp infra/.env.example .env   # Windows: copy infra\.env.example .env
#   .env 안에서 APP_ENV=office  →  APP_ENV=home 으로 바꿀 것
# (집에선 ePrism 인증서 불필요. Dockerfile이 .crt 없으면 자동 스킵)

# 빌드 & 1회 수집
docker build -f infra/Dockerfile -t newsstore .
docker run --rm -e APP_ENV=home -v ${PWD}:/app newsstore python -m newsstore.run --force
# 테스트
docker run --rm -v ${PWD}:/app newsstore pytest -q
```

**중요한 환경 사실:**
- 이 호스트엔 **로컬 파이썬이 없다 → 모든 파이썬은 Docker로 실행.**
- **office**(회사·ePrism TLS 프록시) vs **home**(집): `.env`의 `APP_ENV`로 분기. office는 루트 CA `ePrism-SSL-ROOT-CA.crt`(git 제외, 회사 PC에만 존재)를 이미지에 주입, home은 기본 검증.
- `.env`, `*.crt`는 **git에 안 올라감**(.gitignore). 집에선 `.env`를 새로 만들어야 함(APP_ENV=home).
- 수집 데이터는 `data/newsstore.db`(SQLite). `-v ${PWD}:/app` 볼륨 마운트로 영속화.

---

## 1. 현재 상태 (무엇이 되고 무엇이 안 되나)

### ✅ 완료 (Step 1 수집기 — main 병합 + GitHub 푸시됨)
- 패키지 `src/newsstore/`: models, ssl_config(office|home), config, parser, fetcher, store/{base,sqlite_store}, collector, run
- **20개 pytest 통과** (TDD, 도커 내 실행)
- 레지스트리 `config/feeds.yaml` = **30개 피드**
- **실거동 검증: 30피드에서 923건 수집, 재실행 0건(URL해시 dedup), 피드별 예외 격리**
- 수집/처리 분리 아키텍처: 수집기는 LLM 안 씀, raw 저장소가 유일한 접점
- 조건부 GET(ETag/If-Modified-Since)로 예의, raw 즉시 저장(백필 버퍼)

### ❌ 아직 안 됨 (= 집에서 할 일)
1. **스케줄러** — 지금은 `run.py`가 **1회 수집**만. 주기 실행(매 5분 등) 미구현. 로컬은 cron/스케줄드 태스크, GCP는 Cloud Scheduler 필요.
2. **Firestore 저장** — 지금은 SQLite만. `store/base.py`의 `Store` Protocol 뒤에 `FirestoreStore` 추가하고 `run.py`에서 교체하면 됨(드롭인).
3. **GCP 배포/관리** — 미배포. 내 GCP 계정에서 돌리려면 Cloud Run(컨테이너) + Cloud Scheduler(트리거) + Firestore(저장) 구성 필요. **단, 서울 리전(asia-northeast3) egress IP에서 인포맥스 접근되는지 배포 전 검증 필수**(인포맥스는 자동 fetcher 차단 전력 있음 — 회사 한국 IP에선 됨).
4. **raw 뷰어 웹페이지** — 미구현. 사용자 요청: "상단에 RSS 피드별 드롭다운(셀렉트) 하나 + 그 아래 해당 피드의 raw 항목 리스트". 단일 페이지면 충분(SQLite 읽어서 렌더; 예: 작은 Flask/FastAPI 또는 정적 HTML+JSON 덤프).

---

## 2. 다음 작업 제안 (집에서 이어갈 순서)

### (A) 약간의 추가 — raw 뷰어 웹페이지 (사용자 요청)
- 목표: 수집된 `raw_items`를 **피드별로** 눈으로 확인.
- 최소안: `src/newsstore/viewer.py`에 작은 웹앱(FastAPI/Flask) — 상단 `<select>`(feed_id 목록, `SELECT DISTINCT feed_id`), 선택 시 `SELECT ... WHERE feed_id=? ORDER BY published_at DESC` 결과를 카드 리스트로. 도커로 포트 노출(`-p 8000:8000`).
- TDD로: 라우트 테스트(피드 목록, 피드별 항목) 먼저.

### (B) 스케줄러 (Step 1 "확실히" 동작)
- 로컬/회사: Windows 스케줄드 태스크 또는 도커 `restart: always` + 내부 루프(매 5분 `collect_once`). 또는 호스트 cron이 `docker run ...`을 5분마다.
- GCP: Cloud Scheduler → Cloud Run job/service. (배포는 C)

### (C) Firestore + GCP 배포
- `FirestoreStore(Store)` 구현(google-cloud-firestore), `run.py`에서 환경변수로 SQLite/Firestore 선택.
- GCP: 컨테이너 푸시(Artifact Registry) → Cloud Run → Cloud Scheduler(5분) → Firestore. 서울 리전. Secret Manager에 키.
- **배포 전 반드시**: 서울 리전 egress에서 인포맥스 GET 되는지 테스트.

### (D) Step 2 — Gemini 중요도 태깅 (별도 서브프로젝트)
- raw 저장소를 읽어 중요도+태깅 → 카드(`news`)/본문(`news_body`) 분리(스펙 §5-6).
- 소배치(10~50건) Gemini Flash 구조화 출력. 집계 리뷰는 카드만 모아서.

---

## 3. 핵심 산출물 위치
- 설계: `docs/superpowers/specs/2026-06-12-newsstore-design.md`
- 구현계획(Step 1): `docs/superpowers/plans/2026-06-12-newsstore-collector.md`
- 소스 검증 스파이크(일회용): `scripts/*.py` (인포맥스/Benzinga/Bloomberg/커버리지/하닉 스쿱 등 — 삭제 가능)
- 이 핸드오프: `docs/handoff/2026-06-12-session-handoff.md`

---

## 4. 전체 대화 흐름 (그대로 — 무엇을 묻고 무엇을 찾았나)

> 시간 순. 사용자 질문 → 핵심 결론/데이터.

1. **"한·미 뉴스 광범위, 미국은 벤징가로 충분?"** → 벤징가는 *금융/증시 전문*. 종합뉴스(정치·국제) 아님. 광범위하려면 통신사 필요.
2. **"벤징가 전쟁 이슈 포함?"** → *시장 영향 각도로만*(유가·방산주). 전황·외교 보도는 Reuters/AP 영역.
3. **"자산운용사: 전날 미국 정리 + 시간당 Gemini 중요도, 크립토·채권·FX 커버?"** → 벤징가=주식 강함, 채권·FX 약함. 멀티소스 필요. (rolling vs daily 구분)
4. **"24h 스케줄러, 시간당 직전1h Gemini 태깅, rolling 아님"** → 수집/처리 분리 건전. 24h는 크립토·FX 때문에 맞음. 멀티소스 필수.
5. **"합쳐서 200달러"** → 월 예산이면 Bloomberg/Reuters/벤징가 *유료 API*는 탈락. **무료 RSS + Gemini Flash**가 정답. (벤징가 유료 API도 $200 초과)
6. **"한·미주식·크립토·FX·한미채권, 인포맥스 무료 RSS 상당?"** → 인포맥스가 한국 백본(특히 채권/외환). 6버킷 소스 매트릭스 정리.
7. **"RSS vs API 차이? RSS 직접 받으면?"** → RSS=pull·고정개수·요약/전문 천차만별. API=필터·전문·구조화. 받는 행위는 동일.
8. **"스케줄러 한번 죽으면 다 죽네?"** → 수집/처리 분리, **raw 즉시 저장=백필버퍼**, OS레벨 재기동, dedup으로 해결.
9. **"GAS/GitHub Actions/BigQuery?"** → **GitHub Actions cron은 지연·누락**으로 위험. **GCP 매니지드 서버리스** 선택.
10. **소비 방식** → MVP는 **"쿼리 가능 저장소만"**.
11. **인포맥스 RSS 실측** → 요약 ~270자(태깅엔 충분), 본문은 `#article-view-content-div` 스크래핑. **"AI 학습·활용 금지" 문구** 있으나 → 사용자: 외부 개인 프로젝트라 *무시*. Reuters RSS 폐지·차단. 벤징가 RSS=전문. CoinDesk=요약.
12. **자동승인 + 로컬 HTTP GET 폴백** 합의(메모리 저장). WebFetch는 일부 한국/사내 사이트 차단 → 내 PC에서 GET.
13. **firecrawl vs bs4** → bs4=파서(2층), Firecrawl=스크래핑 올인원 서비스(전층). 정적사이트(인포맥스)엔 requests+bs4면 충분.
14. **도커 크롤 테스트** → 사내 ePrism 뒤 컨테이너에서 인포맥스 본문 추출 성공, 인증서 주입 OK.
15. **서버 위치 중요** → IP/지역 차단 사이트엔 한국 IP 유리. WebFetch(미국클라우드) 막힌 곳은 로컬 GET.
16. **소스 대량 실측** → 벤징가 카테고리 피드 40+개(중첩 `/{sec}/{sub}/feed`), `/feed`는 열림·기사페이지는 차단, 요약 풍부. **폴링주기 = 피크 발행간격 기준**(고볼륨 5분, 깊은 피드 시간당). 벤징가 무료는 15개 캡.
17. **FX/채권/매크로 커버리지** → FX 강함(ForexLive 전문 3600자, FXStreet). 채권=ForexLive 중앙은행 피드(타임스탬프有)+Fed/ECB. 매크로=ForexLive+공식+Google News.
18. **Google News 디코딩** → 인코딩 풀기 비현실(batchexecute 취약)+소스 차단. **Google News=헤드라인만**.
19. **트럼프/Axios/루머/경제캘린더** → 트럼프 원문 `trumpstruth.org/feed`. Axios `axios.com/feeds/feed.rss`. 루머=GNews 쿼리. **경제캘린더=TradingView 공개 엔드포인트(forecast/actual/previous, 무료·무키)**.
20. **실시간 급락 테스트** → 데이터는 *랠리*를 보여줌(코스피 +8%, 미국 2개월래 최고). 솔직히 "급락 아님" 보고. 시스템은 *뉴스(지연)*지 *시세(실시간)*가 아님.
21. **하닉/삼성 레버리지 스쿱** → 표준 피드가 *놓침* → "RSS 커버리지가 (독점 스쿱엔) 약하다" 확인.
22. **Bloomberg RSS 발견(정정)** → 아까 "Bloomberg 무료 RSS 없다"는 **틀림**. `feeds.bloomberg.com/{markets,technology,...}/news.rss` 작동·우리 IP OK·그 스쿱 원본 포착. **Flipboard `@bloomberg/korea` = 한국 전용·리드 포함**. atlasflux/Feedspot은 스크래퍼라 불필요(퍼스트파티 직접 폴링).
23. **한국 소스 확장** → 연합뉴스·한경·매경·아시아경제 RSS 작동. 단 **연합인포맥스=연합뉴스 금융단말 자회사**(중복) → 독립지(한경·매경·아시아경제)가 진짜 다변화. 사용자: 헤드라인만으로 "이슈 있음" 알면 충분.
24. **결정** → Step 1(수집기) 먼저 → Step 2(Gemini 태깅) 나중. raw 저장소로 완전 분리.
25. **스펙 작성** → office/home 분리, 카드/본문 분리, Gemini 2단계(소배치 태깅 + 카드 집계리뷰).
26. **계획 작성 → 서브에이전트로 Step 1 구현 → main 병합 → GitHub 푸시.** (현재 지점)

---

## 5. 결정·제약 요약 (잊지 말 것)
- **무료 RSS의 한계(정직)**: Bloomberg 퍼스트파티 RSS로 *원본 스쿱 헤드라인*은 잡지만, **본문·실시간 시세는 무료로 못 가짐**. 이 시스템은 "맥락·이슈 인지 레이어"지 "알파 스쿱/실시간 시세"가 아님. 실시간 시세 필요하면 별도 quote API.
- **자산군별 무료 천장**: 미국=Benzinga, 한국=인포맥스+독립지, 글로벌 스쿱 헤드라인=Bloomberg feeds + Google News.
- **Google News 출처(Reuters/AP/WSJ)는 제목만**(본문 차단/인코딩).
- **예산 $200/월**, 데이터는 $0(무료 RSS), 실지출은 Gemini Flash + (배포 시) GCP 소액.
- **인포맥스 GCP egress 접근**은 배포 전 미검증 리스크.

---

## 6. 레지스트리(현재 30피드) 메모
`config/feeds.yaml` 참고. 포함: 인포맥스(채권외환/증권/해외주식/국제/정책), 한경, 매경, Benzinga(news/markets/movers/crypto/commodities), CoinDesk, Cointelegraph, ForexLive(news/centralbank), FXStreet, Investing(fx/bonds), Fed, ECB, **Bloomberg(markets/technology/economics + Flipboard Korea)**, Google News(macro_reuters/rumor/kr_chips), TruthSocial, Axios.
추가 후보(미반영): 아시아경제, 이데일리·머니투데이·서울경제(정확한 RSS URL 재확인 필요), TradingView 경제캘린더(비RSS 커넥터).
