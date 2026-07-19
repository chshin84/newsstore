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
- **Cloud Run Job 클론**: 새 Job을 `--args`만으로 생성하면 이미지 CMD가 args로 덮이는데 Dockerfile은 ENTRYPOINT가 없어(`CMD ["python","-m",...]`) args가 곧 실행 커맨드가 됨 → `-m`을 프로그램으로 exec하려다 *"container exited abnormally / exec likely failed"*로 죽는다(newsstore-prices 최초 생성서 재발, 2026-07-04). **단순 처방: create/update에 `--command=python`을 명시**하고 `--args=-m,newsstore.entrypoints.run_X`로 준다(그러면 `command=python`+`args=-m;...`). 복잡 복제가 필요하면 `describe --format=export` → name·mode sed → **`gcloud alpha run jobs replace`**(beta엔 `replace` 없음). 참고: `--args="^;^-m;..."` 커스텀 구분자는 리딩 `;`가 빈 arg를 만들 수 있으니 `--args=-m,mod` 콤마형이 안전.
- **office gcloud 인증 위치**: 호스트 gcloud가 아니라 **docker 볼륨 `gcloud-cfg`**에 상주(`deploy-office.ps1`가 거기에 저장). 모든 호출은 `/work/ePrism-SSL-ROOT-CA.crt`를 컨테이너에 cp+`update-ca-certificates` 후 동작 — **`docker run`에 `-v "D:/projects/newsstore":/work` 마운트를 빼먹으면 CA 못 심어 SSL 실패**(빈 결과·가짜 0이 나옴, 데이터 없음으로 오인 금지).
- **Firebase Hosting 버전=전체 스냅샷**: `populateFiles`에 바뀐 파일만 넣으면 나머지(예 `config.js`)가 빠져 사이트가 깨진다. `web/` **전 파일**(index.html+config.js) 모두 포함해 배포. 순서 = create version → populateFiles → 업로드 → finalize → **release**.
- **Cloud Scheduler→Run Job 호출**: `run.googleapis.com/v2/.../jobs/X:run`은 **oauthToken**(scope `cloud-platform`)으로 호출(oidc 아님). `--oauth-service-account-email=newsstore-job@…`.
- **하드코딩 금지(SSOT)**: 리스트/설정은 원본(feeds.yaml 등)에서 도출, 두 곳 복제 X.
- **`zip` 무음 절단**: `zip(a,b)`는 짧은 쪽에 맞춰 조용히 자름 → 길이 다른 벡터/리스트 연산이 가짜 결과를 냄(코사인·centroid_sum에서 3곳 재발). 길이 계약은 `len` 검증으로 fail-loud(원칙3). 합/내적은 `cluster.add_vectors`처럼 SSOT 헬퍼로 도출.
- **피드 도달성은 IP별로 다름 (양방향)**: 사이트가 IP/UA로 차단 → **Docker 프로빙 호스트 IP ≠ 프로덕션 Cloud Run IP**라 결과가 다르다. mk.co.kr·매경은 Docker에서 `403`이나 Cloud Run(서울)에선 `200`(라이브 수집 확인); bls.gov·opec.org는 Cloud Run에서도 `403`(fxstreet 동류). → **프로빙의 `403`/타임아웃은 *비권위*(`404`만 경로 권위), 최종 판정은 배포 스모크 로그.** 수집기는 브라우저 User-Agent 전송(`collect/fetcher.py` `DEFAULT_HEADERS`)으로 UA 기반 차단 일부 회피(IP 기반은 못 푼다).
- **머지 후 이미지 재빌드 필수 (배포 전)**: 코드를 main에 머지해도 `processor:latest` 이미지가 그대로면 **라이브 Job이 옛 코드를 돌린다** → 새 `--mode`(예 `score`)가 `invalid choice`로 죽음. **머지 → `gcloud builds submit` 재빌드 → `jobs update --image` → execute** 순서를 지켜라.
- **사내(ePrism MITM) gcloud SSL**: 최신 gcloud(urllib3 v2 strict)가 프록시 인증서 AKI 부재를 거부(`Missing Authority Key Identifier`) → 로컬·Cloud Shell 모두 차단, CA 추가로 안 풀림. **우회: `scripts/deploy-office.ps1`**(옛 gcloud 402 컨테이너 + ePrism CA + `core/custom_ca_certs_file` + Cloud Run Jobs는 `beta` 트랙 + Job용 SA `newsstore-job@`로 secret 접근). 집(MITM 없음)에선 평범하게 됨.
- **PowerShell→bash 루프변수 깨짐**: `bash -c "for J in ...; do gcloud ... \$J; done"`를 PowerShell에서 호출하면 `$J`가 안 풀려 인자가 밀림(`Invalid resource name [ --image=...]`). → 루프 대신 **명시적 커맨드 나열**.
- **LLM grounding 리뷰어 오탐 = 리뷰어 입력 부실(생성기보다 적게 봄)**: 리포트 리뷰어가 "아일랜드 1,500BTC 압수"를 '출처 없는 날조'로 기각했으나 **실제 사실**(크립토 프레임 watchpoint 극). 원인 ① 리뷰어가 요약 150자만 받고 생성기는 200자 → 리뷰어가 **덜 봄** ② 구체 사실(수치·고유명사)은 요약이 아니라 스토리 `developments`에 있는데 **둘 다 전개 미전달** ③ 리뷰어가 **프레임을 아예 못 받아** 정당한 극 restate(watchpoints)를 날조로 오판. → **리뷰어 입력 = 생성기 입력 이상 + 출력이 근거하는 모든 출처(여기선 standing 프레임 극)를 명시적으로 제공**. 공유 `_story_line`(제목+요약+최신 전개)으로 생성기·리뷰어 대칭, `build_review_prompt(frame)`로 프레임을 2차 출처로 인정. 결과 10/10 통과(오탐 0). **일반화(domain-llm-runtime): grounding 리뷰어에는 판정 대상이 근거로 삼을 수 있는 컨텍스트를 남김없이 줘라 — 덜 주면 정당한 출력을 환각으로 죽인다.** 그리고 FAIL-LOUD 배지(검증 실패)를 성급히 억누르지 않은 덕에 이 입력 결함을 추적할 수 있었다(배지=진단 흔적).

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

## 2026-07-03 ultracode 전수 감사 (버그 헌트 27건 + 스펙 반영 검토)
- **WAF/차단 페이지는 bozo만으론 못 잡는다** — 정상형(well-formed) XML인 차단 페이지는 feedparser bozo=0. → 다음엔 **`entries==0 and (bozo or not fp.version)`**(피드 포맷 미인식)으로 판정. 실패 시 그 응답의 ETag를 저장하면 차단 페이지에 304를 받아 무수집이 고착되니 **상태 미갱신**이 핵심.
- **`.get(key, [])` 기본값은 null 값을 못 막는다** — LLM JSON은 키를 `null`로 줄 수 있어(`{"lenses": null}`) 기본값이 안 먹고 순회에서 TypeError. → 다음엔 **`resp.get(k) or []` 또는 `isinstance` 가드**. "실 SDK는 None을 준다" gotcha의 JSON-값 변형.
- **설정(yaml) 개정 커밋이 코드의 손복제 상수를 안 고친다** — topics.yaml asset_hint 보정 커밋이 lens_classify의 _KR/_US_HINT를 누락(같은 날 커밋인데도). → 다음엔 어휘 집합을 **설정에서 도출**하고, 손복제가 불가피하면 **어휘 무결성 테스트**로 드리프트를 터뜨린다.
- **`timedelta.days`는 음수에서 내림(floor)** — `abs((dt-ref).days) > N`은 과거 N일+1초=-N-1일로 드롭, 미래 N일+23시간=N일로 통과(비대칭). → **`abs(dt-ref) > timedelta(days=N)`** 로 비교.
- **Firestore 문서 수는 집계 쿼리로** — `col.count().get()`(1000건당 1 read)이 stream() 전수 훑기(문서당 1 read+통째 전송)를 대체. **에뮬레이터도 지원 확인**(2026-07). 로그 한 줄용 count가 스케줄 잡에 있으면 비용이 단조 증가한다.
- **'last_seen 상위 N 스캔창'은 starvation을 낳는다** — 버스트로 창 밖에 밀린 대상은 순위 동결로 영구 미처리. → 대상 선정은 **전수 스캔+incremental 카운터**(이 레포의 lensing/scoring/article 패턴)로 하고, limit은 **콜 상한**으로만(오래 굶은 것부터 소진).
- **requirements.lock을 pip `-c`(constraints)로 쓰면 전이 의존성이 비고정** — constraints는 설치되는 것만 핀하고 목록에 없는 전이는 자유 해석. → 재현성이 목적이면 **전체 `pip freeze`로 재생성**(도커 안: `pip install -e '.[extras]' && pip freeze --exclude-editable`).
- **compose 서비스가 `image:`만 참조하고 아무도 빌드하지 않으면 절차 문서가 거짓이 된다** — `build:` 블록을 함께 배선해 머리말 절차만으로 실행 가능하게.
- **fake store가 실계약 필드를 빼먹어 datetime 직렬화 크래셔가 테스트를 통과** — 리포트 탭 구현에서 fake가 `updated_at` 없는 프레임만 줘서 `json.dumps(frame)`의 TypeError(프로덕션 첫 런 잡 전체 사망)를 287개 테스트가 못 잡음(최종 리뷰가 Docker 재현으로 발견). → 다음엔 **저장 계약이 심는 모든 필드를 fake에도 심고**, 프롬프트/직렬화 경로는 **에뮬레이터 왕복 실물로 1개 이상** 테스트한다("mock이 프로덕션 계약을 약화" gotcha의 직렬화 변형).

## 2026-07-04 리포트 탭 배포
- **Firebase Hosting 배포는 파일 전체 스냅샷 — index.html만 올리면 config.js가 404로 증발** — operations.md §B 스크립트가 `/index.html` 하나만 populateFiles에 넣어서, 재배포 순간 이전 릴리스의 `/config.js`(index.html이 import하는 Firebase 웹 설정)가 새 릴리스에서 사라짐 → 모듈 import 404 → Firebase 미초기화 → 피드·리포트 무한 "불러오는 중". 사이트는 HTTP 200이라 얕은 검증은 통과(스모크가 첫화면만 봄). → 다음엔 **Hosting은 배포 대상 전체를 한 릴리스에 올린다**(§B를 `web/` 전 파일 루프로 수정 완료). 검증도 **config.js 200 + 콘솔 404 없음 + 피드 실제 렌더(카드 수>0)**까지 봐야 한다(첫화면 200으로 "됐다" 금지). 진단은 브라우저 콘솔/네트워크가 SSOT — 단, Playwright 세션 캐시가 옛 404를 하드캐싱하니 캐시-우회 fetch나 새 클라(PowerShell curl)로 서버 실상태를 봐라.

- **2026-07-10 (radar)** 원격 main에 다른 머신 세션의 커밋 74개가 쌓여 push 거부 + 사용자 발화("피드 가격만 남기고") 오독 → 원인: 두 머신에서 병렬로 세션이 진행될 때 로컬 스냅샷·대화 맥락만으로 사용자 발화를 해석했다 — "가격"은 집 세션이 갓 구축한 가격 수집을 가리키는 최신 사실이었는데 오타로 재해석했다 → 해결: **머지·푸시·해석 전에 `git fetch`로 원격을 먼저 측정**하고(상태 문서·로컬 스냅샷은 진실의 캐시), 사용자 발화의 명사가 낯설면 "오타 추정"보다 "내가 모르는 최신 작업" 가설을 먼저 검증한다. 컷/정지 절차 문서에는 고정 목록 대신 판정 규칙(유지: 피드·가격 / 정지: LLM 유발)을 남겨 인벤토리 드리프트에 강건하게 한다.

- **2026-07-10 (radar)** 첫 실데이터 일보에서 어휘 창발 신호가 영어 기능어(on/as/Is/Why)에 침수 → 원인: 불용어가 한국어 조사만 등록돼 있었고 라틴 토큰의 대소문자 변형이 이중 집계됨 — 픽스처 기반 테스트는 전부 통과했다(픽스처가 영어 헤드라인 분포를 재현하지 않음) → 해결: **실데이터 E2E 1회를 머지 게이트로 삼아라** — 픽스처가 못 잡는 분포 결함은 실코퍼스 첫 런이 즉시 드러낸다(STOPWORDS_EN + 소문자 접기로 수정, 회귀 테스트 등재).

## 2026-07-16 임베딩 재도입 (item_vectors)
- **새 office 머신에서 컨테이너의 외부 HTTPS 전면 실패("self-signed certificate in certificate chain")** — 피드 86/87 + Gemini 호출 전부 SSL 검증 실패 → 원인: `ePrism-SSL-ROOT-CA.crt`가 gitignore 대상이라 새 머신 저장소 루트에 없었고, Dockerfile은 파일이 있을 때만 CA를 굽는다(APP_ENV=office여도 파일 없으면 조용히 스킵) → 해결: **Windows 인증서 저장소에서 내보내면 된다** — `Get-ChildItem Cert:\LocalMachine\Root | Where Subject -match 'ePrism'`로 찾아 RawData를 base64 PEM(`-----BEGIN CERTIFICATE-----`)으로 저장소 루트에 쓰고 이미지 재빌드. 이때도 실패 격리는 설계대로 동작했다(수집분 저장·retryable 플래그 유지·fail-loud exit).
- **실 Firestore 대상 로컬 스모크는 ADC(`gcloud auth application-default login`) 없이는 못 돈다** — 대신 **에뮬레이터 store + 실 API 키** 조합(`docker compose run -e FIRESTORE_EMULATOR_HOST=... -e GOOGLE_CLOUD_PROJECT=test collect`)으로 외부 API 경로(실 Gemini 임베딩·차원·http_options)를 프로덕션 데이터 오염 없이 E2E 검증할 수 있다. 이 조합으로 수집 1927건 → embed 500(cap) → 백필 drain 1433건 소진을 실측했다.
- **google-genai SDK는 API 키를 URL이 아니라 헤더로 보낸다**(httpx 로그의 batchEmbedContents URL에 키 없음) — 예외 문자열 `key=` 스크러빙(redact)은 예방 방어선으로 유지하되, URL 노출 걱정으로 로그 레벨을 낮출 필요는 없다.
- **백필이 "marked 0"으로 끝났는데 story는 5.5만 건** — 원인: 버그가 아니라 측정 결과였다. 데이터를 REST로 직접 재보니 오늘 배포 이전 수집분엔 `expire_at`이 아예 없었다 — data-only 전환(7-13 커밋)의 이미지가 실제 프로덕션 collector에는 배포된 적이 없었던 것(문서·커밋은 "전환 완료"였지만 인프라는 옛 이미지). 백필의 수명 가드는 expire_at 없는 문서를 설계대로 제외했다 → 교훈: **"0건"이 나오면 코드 의심 전에 데이터에서 상태를 도출하라**(이 파일의 Firestore 0건 gotcha와 동족). 그리고 **"배포됐다"는 커밋·문서가 아니라 런타임 데이터(필드 존재·로그)로 판정하라** — 상태 문서는 진실의 캐시다.

## 2026-07-19 factors 잡 부활 + 문서 위생
- **깨진 스케줄 잡의 조용한 실패 — 계약 문서 "구현 완료"를 믿지 마라** — `newsstore-stocks` 잡이 없는 모듈 `run_stock_prices`(실제는 `run_factors`)를 호출해 매일 07:00 `exit(1)`로 죽고 있었다. 계약 문서는 factors "구현 완료·2856문서 실검증"이라 PIT가 도는 줄 알았으나, gcloud 로그로 보니 **§2 backfill 불가 스냅샷(estimates·price_targets·grades_consensus)이 매일 영구 유실** 중이었다(스케줄러는 `:run` 시작만 확인해 초록으로 보임 — operations §G의 조용한 실패). → 잡 성패는 스케줄러 초록·계약 문서의 "완료"가 아니라 **실행 로그(textPayload·exit code)로 도출**하라. "배포됐다는 커밋 아니라 런타임 데이터로 판정" gotcha의 잡-실행 변형.
- **plain env가 secret 바인딩을 가려 빈 키로 조용히 0건 수집** — 잡에 빈 `FMP_API_KEY` plain env가 남아 있으면 `--set-secrets FMP_API_KEY=fmp-api-key:latest`가 안 먹는다(동명 plain 잔존). 빈 키로 돌면 FMP는 401이 아니라 **빈 배열**을 반환해, `collect_universe`가 `0 symbols` → 잡은 `exit(0)`으로 "성공"한다(FAIL-LOUD 아님). → `--set-secrets` **전에** 동명 plain env를 `--remove-env-vars=FMP_API_KEY`로 지워라. 그리고 빈-키 증상은 에러가 아니라 빈 결과이니 **exit 0이 아니라 심볼 수·수집 수를 검문**하라. "실 SDK는 빈 결과에 None/빈 배열" gotcha의 인증 변형.
- **stale 계약 문서를 리뷰어가 진실로 믿어 옳은 설계를 오판** — factors-v2 설계 리뷰에서 리뷰어가 `firestore-contract.md`(30일)를 SSOT로 믿어 설계의 60일을 "grounding critical(틀림)"로 판정했으나, 코드(`_TTL=60`)+데이터(기존 문서 일괄 만료 실측)로 보면 진실은 60이고 **계약 문서가 stale**이었다. → 리뷰어에 계약 문서를 source로 줄 때 그 문서 자체가 stale일 수 있음을 전제하고, 휘발성 사실(TTL·배포·잡 상태)은 문서가 아니라 **코드·인프라에서 도출해 리뷰어에 주입**하라. 넛지대로 리뷰를 돌린 덕에 설계가 기존 구현·계약과 어긋난 지점(그린필드 오인·유니버스 600 대 2000·조정 대 raw EOD)을 다수 발견했다(리뷰 레이어의 가치).
- **전수 수집 잡의 조용한 타임아웃 사망** — 모듈·시크릿을 고쳐 잡이 실제 수집을 시작했는데도 `FAILED`로 끝났다. 원인: task-timeout이 **300초(5분)**인데 `--cadence all`(600종목 × 11엔드포인트 ≈ 6,600콜, 콜당 ~0.34초 = **약 37분**)이 이를 넘겨 "Terminating task because it has reached the maximum timeout of 300 seconds"로 강제 종료(maxRetries=1이라 재시도도 같은 이유로 사망). FMP 호출은 200 OK로 정상이라 로그만 얼핏 보면 잘 되는 듯 보였다. → **전수 수집 잡은 task-timeout을 실측 패스시간의 여유배로**(여기선 3600s). 그리고 "수집 중"(200 OK 로그)과 "완주 성공"(exit 0 + `collect done` 카운트)은 다르다 — **완주 카운트로 검증**하라(검증 후 주장).
- **history dedup이 전체 이력을 read해 Firestore read 비용 폭탄** — `run_factor_pass`의 history shape는 매 런 `filter_new_ids_in`(=`get_all`)로 **응답 전체 행의 존재를 확인**한다. `prices_eod`는 종목당 ~1,230행이라 1000종목이면 **런당 ~123만 read**. `--cadence all`로 매일 돌리면 prices_eod dedup read만 **월 ~$22**(read ≈ $0.06/10만). 컴퓨트(62분)가 주범인 줄 알았지만 Cloud Run **Job은 실행 초 단위 과금(상시 아님)**이라 컴퓨트는 ~$0.3/월로 작았고, **read/write가 지배**였다. → **백필 가능한 history/snapshot(§1)는 weekly로, 백필 불가 §2(asof, dedup-read 없음)만 daily로 분리**(SPECS cadence). 교훈: 대량 이력 dedup은 "전체 재조회"라 **빈도가 곧 비용** — 백필 가능한 데이터를 매일 재수집하지 마라. 비용 진단은 컴퓨트 시간이 아니라 read/write 건수부터 세라.
