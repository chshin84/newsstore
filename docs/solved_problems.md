# 해결된 문제 로그 (solved_problems)

작업 중 발견·해결된 문제 기록. 대부분 **사용자 지적/요청**이나 **코드 리뷰**에서 나왔다. 각 항목: 문제 → 원인 → 해결.
(미해결·대기 항목은 GitHub Issues — 손유지 백로그 파일은 두지 않는다.)

## 핵심 gotchas (재발 방지 — 서브에이전트 주입용 다이제스트)
*반복되는 cross-cutting 함정*만 추림. SDD/ultracode 서브에이전트엔 **이 섹션 + `coding-principles.md`를 주입**(전체 아카이브 말고). 배선: `docs/subagent-context.md`.
- **Docker-only**: 테스트 `docker compose run --rm test` (또는 `MSYS_NO_PATHCONV=1 docker run -v "D:/projects/newsstore:/app" newsstore pytest -q`). `$(pwd)` 마운트는 stale 이미지로 조용히 폴백.
- **Firestore 실client**: 빈 문서 `to_dict()`가 `None` 반환 → 항상 `... or {}` (MockFirestore는 못 잡음).
- **PowerShell 변수 대소문자 비구분**: `$h`와 `$H`는 같은 변수 → 충돌 주의.
- **Firebase REST**: 헤더 `x-goog-user-project: daily-recap-498506` 없으면 403.
- **인라인 주석 금지**: `.gitignore`/`.env`/`--env-file`은 줄끝 `# 주석`을 값/패턴에 섞음 → 주석은 별도 줄.
- **프로덕션을 테스트에 맞춰 약화 금지**: 테스트 더블이 부실하면 *테스트*를 고쳐라(프로덕션 `client.close()`를 guard로 무르게 X).
- **Cloud Run Job 클론**: 새 Job을 `--args`만으로 생성하면 이미지 ENTRYPOINT가 덮여 *"container exited abnormally / exec likely failed"*로 죽는다. 기존 Job을 `gcloud run jobs describe --format=export` → name·mode만 sed 치환 → **`gcloud alpha run jobs replace`**(beta엔 `replace` 없음)로 적용해야 command(`python`)+args(`-m run_enrich --mode X`)+env(`GOOGLE_CLOUD_PROJECT`)까지 정확히 복제됨.
- **office gcloud 인증 위치**: 호스트 gcloud가 아니라 **docker 볼륨 `gcloud-cfg`**에 상주(`deploy-office.ps1`가 거기에 저장). 모든 호출은 `/work/ePrism-SSL-ROOT-CA.crt`를 컨테이너에 cp+`update-ca-certificates` 후 동작 — **`docker run`에 `-v "D:/projects/newsstore":/work` 마운트를 빼먹으면 CA 못 심어 SSL 실패**(빈 결과·가짜 0이 나옴, 데이터 없음으로 오인 금지).
- **Firebase Hosting 버전=전체 스냅샷**: `populateFiles`에 바뀐 파일만 넣으면 나머지(예 `config.js`)가 빠져 사이트가 깨진다. `web/` **전 파일**(index.html+config.js) 모두 포함해 배포. 순서 = create version → populateFiles → 업로드 → finalize → **release**.
- **Cloud Scheduler→Run Job 호출**: `run.googleapis.com/v2/.../jobs/X:run`은 **oauthToken**(scope `cloud-platform`)으로 호출(oidc 아님). `--oauth-service-account-email=newsstore-job@…`.
- **하드코딩 금지(SSOT)**: 리스트/설정은 원본(feeds.yaml 등)에서 도출, 두 곳 복제 X.
- **`zip` 무음 절단**: `zip(a,b)`는 짧은 쪽에 맞춰 조용히 자름 → 길이 다른 벡터/리스트 연산이 가짜 결과를 냄(코사인·centroid_sum에서 3곳 재발). 길이 계약은 `len` 검증으로 fail-loud(원칙3). 합/내적은 `cluster.add_vectors`처럼 SSOT 헬퍼로 도출.
- **피드 도달성은 IP별로 다름 (양방향)**: 사이트가 IP/UA로 차단 → **Docker 프로빙 호스트 IP ≠ 프로덕션 Cloud Run IP**라 결과가 다르다. mk.co.kr·매경은 Docker에서 `403`이나 Cloud Run(서울)에선 `200`(라이브 수집 확인); bls.gov·opec.org는 Cloud Run에서도 `403`(fxstreet 동류). → **프로빙의 `403`/타임아웃은 *비권위*(`404`만 경로 권위), 최종 판정은 배포 스모크 로그.** 수집기는 브라우저 User-Agent 전송(`collect/fetcher.py` `DEFAULT_HEADERS`)으로 UA 기반 차단 일부 회피(IP 기반은 못 푼다).
- **머지 후 이미지 재빌드 필수 (배포 전)**: 코드를 main에 머지해도 `processor:latest` 이미지가 그대로면 **라이브 Job이 옛 코드를 돌린다** → 새 `--mode`(예 `score`)가 `invalid choice`로 죽음. **머지 → `gcloud builds submit` 재빌드 → `jobs update --image` → execute** 순서를 지켜라.
- **사내(ePrism MITM) gcloud SSL**: 최신 gcloud(urllib3 v2 strict)가 프록시 인증서 AKI 부재를 거부(`Missing Authority Key Identifier`) → 로컬·Cloud Shell 모두 차단, CA 추가로 안 풀림. **우회: `scripts/deploy-office.ps1`**(옛 gcloud 402 컨테이너 + ePrism CA + `core/custom_ca_certs_file` + Cloud Run Jobs는 `beta` 트랙 + Job용 SA `newsstore-job@`로 secret 접근). 집(MITM 없음)에선 평범하게 됨.
- **PowerShell→bash 루프변수 깨짐**: `bash -c "for J in ...; do gcloud ... \$J; done"`를 PowerShell에서 호출하면 `$J`가 안 풀려 인자가 밀림(`Invalid resource name [ --image=...]`). → 루프 대신 **명시적 커맨드 나열**.

## 환경 / 툴링
- **로컬 Python 없음** — 호스트 `python`은 Windows Store 스텁. → **Docker 전용 개발**(개발 원칙 7). 모든 실행·테스트는 Docker.
- **Docker bind-mount 경로 폴백** — Git Bash `$(pwd)`/`${PWD}`가 망가져 마운트가 *stale 이미지*로 조용히 폴백 → 테스트 수가 틀리게(44 대신 33) 나옴. → `MSYS_NO_PATHCONV=1 docker run --rm -v "D:/projects/newsstore:/app" newsstore pytest -q`.
- **Workflow `args`가 문자열로 전달** — 첫 피드검증 워크플로가 `feeds.map is not a function`로 실패. → 스크립트에 `typeof args === 'string' ? JSON.parse(args) : args` 폴백.
- **PowerShell 변수 대소문자 비구분** — Hosting 배포에서 루프변수 `$h`(해시)가 `$H`(헤더)를 덮어써 실패. → 변수명 분리(`$hdr`/`$rh`) + 해시→바이트 직접 맵 + `[byte[]]` 캐스팅.
- **`.gitignore` 인라인 주석 미지원** — `uv.lock  # ...` 패턴이 안 먹혀 파일이 계속 추적됨. → 주석을 별도 줄로.

## 코드 리뷰에서 잡은 것 (FirestoreStore)
- **`get_feed_state`/`get_unprocessed`의 `to_dict()` None** — 실제 google client는 빈 문서에 `None` 반환 → `AttributeError`(MockFirestore는 못 잡음). → `snap.to_dict() or {}` 가드.
- **`run.py` 프로덕션 약화** — 구현자가 테스트 더블 맞추려 `client.close()`를 `getattr(client,"close",...)`로 약화. → 리뷰가 잡음 → 프로덕션 원복 + 테스트가 `close()` 있는 가짜 제공.
- **미사용 import / N+1 read** — `from typing import Optional` 미사용 제거, `mark_processed` 배치-read TODO 주석.

## GCP / Firebase 배포
- **Firebase REST 403 (quota project)** — gcloud 토큰으로 Firebase API 호출 시 quota project 미설정. → 헤더 **`x-goog-user-project: daily-recap-498506`** 필수.
- **콘솔에 프로젝트 안 보임 / 웹앱·apiKey 못 찾음** — GCP 프로젝트에 Firebase 미추가 상태. → **REST `:addFirebase`** 로 추가 + 웹앱 생성 + config 발급(콘솔 헤맬 필요 없어짐).
- **실수로 만든 중복 프로젝트** `daily-recap-498506-5ff8b` — "새 Firebase 프로젝트"를 눌러 별개 빈 프로젝트 생성. → 무해(이름만 중복, ID 다름) 확인 후 삭제. 진짜는 `daily-recap-498506`.
- **apiKey 노출 우려** — 공개 repo/사이트에 Firebase 웹 apiKey 보임. → **비밀 아님**(식별자일 뿐, 접근은 보안규칙이 통제) 확인. 단 **`GEMINI_API_KEY`는 진짜 비밀** → 백엔드 전용(개발 원칙 8).
- **fxstreet 항상 실패** — Cloud Run 데이터센터 IP에서 차단(집 IP에선 됨). → 피드 제거(실패 0).

## 사이트 — 데이터 품질 / UX
- **`&quot;` 등 엔티티 노출** — 제목에 디코딩 안 된 HTML 엔티티(인포맥스 이중 인코딩). → 표시 전 클라이언트 디코드.
- **TruthSocial이 본문을 제목에** — 피드가 본문을 title에 실음. → 제목="Truth Social", 본문은 미리보기.
- **같은 뉴스 중복**(BitGo PR 등) — dedup이 URL(link) 기준이라 같은 뉴스가 URL만 달라 중복 저장. → 사용자 선택대로 **뷰에서 제목 정규화 dedup**(비파괴).
- **집단소송 로펌 PR + "$X 투자했다면" 클릭베이트** — Benzinga 양산 스팸. → 고정밀 키워드 필터. 이후 백엔드 `classify.SPAM_SIGNALS`로 이식·통합 완료(뷰 JUNK에서 승격).
- **소스 색 겹침** — 해시 충돌. → 황금각(137.5°) 배정.
- **영어 폰트 가독성** — → Inter(영) + Noto Sans KR(한).
- **블룸버그 너무 적음** — 실은 132건(3위)인데 최신순 80개에 고빈도 소스(Benzinga·GNews)에 밀려 안 보였음. → **소스 필터 드롭다운** + Bloomberg 카테고리 피드 5개 추가.
- **소스 드롭다운에 빈 항목** — ForexLive/FXStreet/FinancialJuice 등 데이터 없는 소스 하드코딩. → 실제 소스만 → 이후 **SSOT**(meta/sources)로 완전 자동화.
- **소스 선택 시 인덱스 에러** — `source+published_at` 복합 인덱스 생성 중. → 친절 안내+자동 재시도, 인덱스 READY.

## 피드 / 수집
- **Reuters GN 중복** — 새 `reuters_top`이 기존 `gn_macro_reuters`(둘 다 site:reuters.com)와 겹침 + 헤드라인뿐. → `gn_macro_reuters` 제거, Reuters 단독화.
- **본문 스크래핑 가능성** — 전 소스 curl 테스트 → Bloomberg 403·CoinDesk/CT/Investing JS렌더·GN 리다이렉트로 fragile. → **스크래핑 안 함, 피드 확충이 정답**(결정).

## Step-2 하드닝
- **cosine/centroid_sum 무음 절단** — `cluster.cosine`이 `zip(a,b)`로 dot은 min(len)만 합산하되 노름은 전체로 계산 → 차원 다르면 가짜 유사도를 조용히 반환(fail-loud 위반). 같은 패턴이 두 스토어 `append_to_story`의 `centroid_sum += vec`에도 존재. → `cosine`에 `len` 검증 ValueError + `add_vectors(a,b)` SSOT 헬퍼 신설(cluster.py), 두 스토어가 도출. 회귀 테스트(차원 불일치 시 ValueError) 추가.
- **firestore `mark_processed` to_dict() None 가드 재발** — 같은 파일 6곳은 `or {}` 쓰는데 `mark_processed`(line 128)만 누락 → 실 client 빈 문서(exists=True, to_dict()=None)에서 AttributeError(MockFirestore는 못 잡음, 핵심 gotcha 재발). → `to_dict() or {}`로 일관화. 실 client 조건을 재현하는 최소 fake(exists=True·to_dict→None)로 회귀 테스트.
- **SPAM_SIGNALS↔web JUNK 크로스언어 SSOT 드리프트** — backend `classify.SPAM_SIGNALS`와 `web/index.html` JUNK 25키워드가 각각 하드코딩(한쪽만 고치면 kind=spam과 뷰 isJunk 드리프트). 근본해소(뷰→`kind` 쿼리)는 Plan 3/4 잔여라, 최소 안전망으로 **드리프트 가드 테스트**(`tests/test_spam_signals_drift.py`: index.html JUNK 파싱 → set 동등성 fail-loud) 추가. probe 주입→FAIL로 가드 실효성 검증.

## Step-2 라이브 통합 (실 Gemini 스모크가 잡은 것)
> 측정 먼저(원칙7)·검증 후 주장(원칙5)의 사례 — 유닛테스트(fake)는 다 통과했지만 라이브가 4개 버그를 드러냄.
- **모델명은 라이브 `models.list`로 확정** — spec의 `gemini-2.0-flash`는 API에서 "no longer available"(404), `text-embedding-004`/`text-multilingual-embedding`은 이 **Developer API 키(GEMINI_API_KEY)에 없음**(그건 Vertex/ADC 경로). 실재: gen=`gemini-2.5-flash*`, embed=`gemini-embedding-001`만. → 추측 말고 `client.models.list()`로 확인 후 핀.
- **gemini-embedding-001은 기본 3072차원** — 768로 받으려면 `EmbedContentConfig(output_dimensionality=768)` 명시. 안 하면 dim 가드(`embedder.EMBED_DIM=768`)가 fail-loud로 터짐(가드가 제 역할).
- **retry는 4xx에 하면 낭비** — `call_with_retry`가 404(비일시적)에 3회 재시도. → `is_transient` 술어로 4xx(404/400)는 즉시 실패, 408/429/5xx/네트워크만 재시도(advisor-nonfunctional).
- **클러스터 임계값은 임베딩 모델별로 재캘리브레이션** — 0.83은 *스파이크의 Vertex 모델* 기준. gemini-embedding-001(768) 실측: **같은 스토리 0.68~0.80 / 다른 스토리 0.47~0.56** → 0.83이면 아무것도 안 묶임. 0.65로 조정(소표본, 프로덕션 데이터로 정밀화 요), `NEWSSTORE_CLUSTER_THRESHOLD` env로 튜닝. **교훈: 임계값은 모델 종속 — 임베딩 모델 바꾸면 반드시 재측정.**
- **태깅 통제어휘는 프롬프트 주입 시 잘 지켜짐** — `build_prompt`가 "entities ONLY from: …"로 어휘를 주입하면 모델이 캐노니컬 토큰(`Fed`,`rates`,`inflation`)을 그대로 반환 → `validate_tags` 결정론 필터 통과. (어휘 미주입 시엔 freeform "Federal Reserve" 반환 → 다 걸러짐. 즉 프롬프트 SSOT 주입이 핵심.)

## 설계 — 임베딩 클러스터링 (스파이크 검증)
- **union-find 과병합** — naive 단일임계 쌍연결이 *전이 연쇄*로 무관한 한국어 금융기사 9건을 한 덩어리로. → **centroid 온라인 + 임계 0.83**(중심과 비교 → 사슬 차단).

## 정리 / 리팩터
- **SSOT 위반: `index.html` SRC_ORDER 하드코딩** — 사용자 지적. feeds.yaml 소스를 복제 → 드리프트 위험. → 수집기가 `meta/sources`를 feeds.yaml에서 도출·기록 → 사이트가 읽음. **중복 제거**(드리프트 테스트 불필요).
- **firebaseConfig 인라인** — → `web/config.js` 분리.
- **uv.lock / data;C / docker-compose / .env.example / .dockerignore** — uv.lock gitignore · `data;C` 빈 잔재 삭제 · 미사용 docker-compose 삭제(→ **이후 린 compose로 부활: `docker compose run --rm test/collect`, 마운트 폴백 회피**) · 디스크 소실된 .env.example 복원 · .dockerignore에 tests/·web/·*.md 추가(런타임 이미지 순수화).
