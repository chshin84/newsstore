# 운영 / 재배포 런북

이 문서는 **변경분을 클라우드에 반영**하는 명령 모음이다.
**0→배포 최초 셋업 절차(프로젝트/Firestore/Cloud Run/Scheduler/IAM/Firebase/규칙/Hosting 생성)는 `docs/setup.md` 참조.**

## 전제
- `gcloud`가 사용자 프로필에 인증돼 있어야 함 (`chshin84@gmail.com`, 프로젝트 `daily-recap-498506`).
  - gcloud 풀경로(머신별): 집=`C:\Users\ho381\...`, 사내=`C:\Users\CHSHIN\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd`.
  - **사내(office)에서 gcloud SSL 차단 시 우회:** ePrism MITM 프록시가 최신 gcloud(urllib3 v2 strict)의 AKI 검증(`certificate verify failed: Missing Authority Key Identifier`)을 막으면 **옛 gcloud(402) 컨테이너 + ePrism CA** 편법으로 우회한다(`scripts/deploy-office.ps1`, Cloud Run Jobs는 `beta` 트랙). 집은 MITM 없어 평범하게 §A/§F, 사내는 위 스크립트. 정공법(IT의 AKI 준수 인증서 / GitHub→Cloud Build 트리거)은 선택.
- **Firebase 관리/규칙/호스팅 REST 호출 시 quota project 헤더 필수**: `x-goog-user-project: daily-recap-498506` (없으면 403). 토큰은 `gcloud auth print-access-token`.
- 프로젝트/리전 변수는 루트 **`.env`**(`GOOGLE_CLOUD_PROJECT`, `GCP_REGION`). PowerShell 로드법은 `docs/setup.md` 참조.

## 리소스 인벤토리
| 종류 | 이름 |
|------|------|
| GCP 프로젝트 | `daily-recap-498506` (asia-northeast3) |
| Firestore | `(default)` Native — 컬렉션 `items`, `feed_state` |
| Artifact Registry | `newsstore` → 이미지 `asia-northeast3-docker.pkg.dev/daily-recap-498506/newsstore/collector:latest` |
| Cloud Run Job | `newsstore-collector` (env `NEWSSTORE_BACKEND=firestore`, `GOOGLE_CLOUD_PROJECT=daily-recap-498506`, `APP_ENV=home`) |
| Cloud Scheduler | `newsstore-5min` (`*/5 * * * *`) |
| Cloud Run Job #2 | `newsstore-enricher` — Step-2 클러스터 인리치(image `processor:latest`, CMD `python -m newsstore.entrypoints.run_enrich`, secret `gemini-api-key`) |
| Cloud Scheduler #2 | `newsstore-enrich-10min` (`*/10 * * * *`) |
| Cloud Run Job #3 | `newsstore-summarizer` — 스토리 요약(같은 image `processor:latest`, args `... run_enrich --mode summary`, secret 동일) |
| Cloud Scheduler #3 | `newsstore-summary-hourly` (`5 * * * *`) |
| Cloud Run Job #4~#6 | `newsstore-lenser`(args `--mode lenses`) · `newsstore-scorer`(`--mode score`) · `newsstore-article`(`--mode article`) — 모두 같은 `processor:latest`, args만 다름, secret 동일 |
| Cloud Scheduler #4~#6 | `newsstore-lens-10min`(`*/10`) · `newsstore-score-10min`(`3-59/10`) · `newsstore-article-10min`(`6-59/10`) — 윈도 내 lens→score→article 시차 |
| Secret Manager | `gemini-api-key` (`processor:latest` 쓰는 enrich Job 5개 모두에 `--update-secrets`로 주입; SA에 secretAccessor) |
| 서비스계정 | `newsstore-job@daily-recap-498506.iam.gserviceaccount.com` (roles: `datastore.user`, `run.invoker`) |
| Firebase Hosting | site `daily-recap-498506` → https://daily-recap-498506.web.app |
| Firebase 웹앱 | appId `1:754646487603:web:19e77fba52a8aacf1b0946` (config는 `web/index.html`에 인라인) |

---

## A. 수집기 재배포 (config/feeds.yaml 또는 수집기 코드 변경 시)
`config/feeds.yaml`은 이미지에 `COPY` 되므로 **반드시 재빌드 후 Job 갱신**해야 반영된다.
```
# 1) 이미지 재빌드 ([gcp] 타깃 = google-cloud-firestore 포함)
gcloud builds submit --config infra/cloudbuild.yaml \
  --substitutions=_IMAGE=asia-northeast3-docker.pkg.dev/daily-recap-498506/newsstore/collector:latest .
# 2) Job을 새 이미지 digest로 재고정
gcloud run jobs update newsstore-collector \
  --image=asia-northeast3-docker.pkg.dev/daily-recap-498506/newsstore/collector:latest \
  --region=asia-northeast3
# 3) 즉시 1회 실행 (안 하면 다음 5분 스케줄에 반영)
gcloud run jobs execute newsstore-collector --region=asia-northeast3 --wait
# 4) 확인 (실패 피드 / 수집 수)
gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="newsstore-collector"' \
  --freshness=5m --format="value(textPayload)" | Select-String "feed\(s\) failed|collected .* new item"
```

## B. 사이트 재배포 (web/index.html 변경 시)
Firebase CLI/Node 없이 **Hosting REST API**로 배포 (PowerShell):
```powershell
$g="C:\Users\ho381\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
$tok=(& $g auth print-access-token).Trim()
$H=@{Authorization="Bearer $tok"; "x-goog-user-project"="daily-recap-498506"}
$site="https://firebasehosting.googleapis.com/v1beta1/projects/daily-recap-498506/sites/daily-recap-498506"
$raw=[IO.File]::ReadAllBytes("D:\projects\newsstore\web\index.html")
$ms=New-Object IO.MemoryStream
$gz=New-Object IO.Compression.GzipStream($ms,[IO.Compression.CompressionMode]::Compress)
$gz.Write($raw,0,$raw.Length); $gz.Close(); $gzb=$ms.ToArray()
$hash=([Security.Cryptography.SHA256]::Create().ComputeHash($gzb)|%{$_.ToString("x2")}) -join ""
$ver=Invoke-RestMethod -Method POST -Uri "$site/versions" -Headers $H -ContentType "application/json" -Body "{}"
$pop=Invoke-RestMethod -Method POST -Uri "https://firebasehosting.googleapis.com/v1beta1/$($ver.name):populateFiles" -Headers $H -ContentType "application/json" -Body (@{files=@{"/index.html"=$hash}}|ConvertTo-Json)
if($pop.uploadRequiredHashes){Invoke-WebRequest -Method POST -Uri "$($pop.uploadUrl)/$hash" -Headers $H -ContentType "application/octet-stream" -Body $gzb|Out-Null}
Invoke-RestMethod -Method PATCH -Uri "https://firebasehosting.googleapis.com/v1beta1/$($ver.name)?updateMask=status" -Headers $H -ContentType "application/json" -Body '{"status":"FINALIZED"}'|Out-Null
Invoke-RestMethod -Method POST -Uri "$site/releases?versionName=$($ver.name)" -Headers $H -ContentType "application/json" -Body "{}"|Out-Null
"deployed -> https://daily-recap-498506.web.app"
```
배포 후 브라우저는 **Ctrl+F5**(캐시).

## C. 보안 규칙 변경 (firestore.rules)
`firebaserules` REST로 ruleset 생성 + `cloud.firestore` release 갱신 (PowerShell, 헤더 `x-goog-user-project` 필수). 또는 Firebase 콘솔 → Firestore → 규칙에 붙여넣기.

## D. 복합 인덱스 추가
```
gcloud firestore indexes composite create --collection-group=items \
  --field-config=field-path=<FIELD>,order=ascending \
  --field-config=field-path=published_at,order=descending --async
gcloud firestore indexes composite list --format="value(state,fields.fieldPath)"
```
인덱스: `source+published_at`(소스필터), `tags+published_at`(태그필터), `processed+fetched_at`(Step-2 큐).

> ⚠️ **소유권 안내:** 아래 §E·§F의 인리치/요약 패스는 **`news-analytics` repo 소유**다(경계·계약: `docs/firestore-contract.md`). 코드·이미지·Job이 newsstore에서 운영되므로(처리기 이미지를 newsstore Dockerfile로 빌드) 런북을 여기 유지한다.

## E. 인리치 Processor 배포 (`processor:latest` 이미지 — enrich Job 5개 공용)
> **코드 변경 재배포(평소):** processor 이미지 1개를 재빌드한 뒤 **그걸 쓰는 Job 5개 모두**를 새 이미지로 갱신한다(이름이 `newsstore-processor`가 아니라 패스별로 나뉘어 있음):
> ```
> gcloud builds submit --config infra/cloudbuild.processor.yaml \
>   --substitutions=_IMAGE=asia-northeast3-docker.pkg.dev/daily-recap-498506/newsstore/processor:latest .
> for j in newsstore-enricher newsstore-lenser newsstore-scorer newsstore-article newsstore-summarizer; do
>   gcloud run jobs update "$j" --image=asia-northeast3-docker.pkg.dev/daily-recap-498506/newsstore/processor:latest --region=asia-northeast3
> done
> gcloud run jobs execute newsstore-enricher --region=asia-northeast3 --wait   # 스모크
> ```
> 5개는 같은 이미지에 `--args ... run_enrich --mode {cluster|lenses|score|article|summary}`만 다르다. 아래는 **최초 생성** 절차(이름 예시 `newsstore-processor`는 역사적 — 실제 잡은 위 5개).

수집기와 **별도 Job**. 같은 Dockerfile을 `INSTALL_ENRICH=true`로 빌드(google-genai 포함)해 **별 이미지**(`processor:latest`)로 올리고, CMD를 `python -m newsstore.entrypoints.run_enrich`로 돌린다. `GEMINI_API_KEY`는 **Secret Manager**로 주입(커밋/이미지/로그 금지 — 백엔드 전용 비밀).

> **선결: `requirements.lock`에 google-genai 추가.** lock이 constraints(-c)라 미포함이면 빌드 실패. `pip-compile`/`uv` 등으로 `enrich` extra 포함해 재생성 후 커밋. (httpx<1.0 등 기존 핀과 충돌 시 해소 필요 — 이게 첫 빌드 게이트.)

```
# 1) 비밀 생성 + Job SA에 접근 권한
printf '%s' "<GEMINI_API_KEY>" | gcloud secrets create gemini-api-key --data-file=- --replication-policy=automatic
gcloud secrets add-iam-policy-binding gemini-api-key \
  --member=serviceAccount:newsstore-job@daily-recap-498506.iam.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
# 2) Processor 이미지 빌드(enrich extra)
gcloud builds submit --config infra/cloudbuild.processor.yaml \
  --substitutions=_IMAGE=asia-northeast3-docker.pkg.dev/daily-recap-498506/newsstore/processor:latest .
# 3) Job #2 생성 (CMD 오버라이드 + 비밀 주입). SA는 수집기와 공유(datastore.user 보유)
gcloud run jobs create newsstore-processor \
  --image=asia-northeast3-docker.pkg.dev/daily-recap-498506/newsstore/processor:latest \
  --region=asia-northeast3 \
  --service-account=newsstore-job@daily-recap-498506.iam.gserviceaccount.com \
  --set-env-vars=NEWSSTORE_BACKEND=firestore,GOOGLE_CLOUD_PROJECT=daily-recap-498506,APP_ENV=home \
  --update-secrets=GEMINI_API_KEY=gemini-api-key:latest \
  --command=python --args=-m,newsstore.entrypoints.run_enrich
# 4) 수동 1회 실행 + 로그 확인
gcloud run jobs execute newsstore-processor --region=asia-northeast3 --wait
gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="newsstore-processor"' \
  --freshness=10m --format="value(textPayload)" | Select-String "enrichment done|aborted"
# 5) Scheduler #2 (수집과 시차; 예: 매시 10분). HTTP로 Run Admin API의 Job:run 호출(수집기 패턴 동일)
gcloud scheduler jobs create http newsstore-enrich-hourly --location=asia-northeast3 \
  --schedule="10 * * * *" \
  --uri="https://run.googleapis.com/v2/projects/daily-recap-498506/locations/asia-northeast3/jobs/newsstore-processor:run" \
  --http-method=POST --oauth-service-account-email=newsstore-job@daily-recap-498506.iam.gserviceaccount.com
```
이후 코드/어휘 변경 반영은 §A와 동일하게 **2)+3) 재빌드→이미지 갱신**(`gcloud run jobs update newsstore-processor --image=...`). 복합 인덱스(스토리/태그 쿼리)가 필요하면 §D.

## F. 스토리 요약 패스 (Pass 3 — `--mode summary`, 시간당)
요약 패스는 **기존 `processor` 이미지를 그대로 재사용**한다(`run_enrich --mode summary`). cluster 패스(10분)와 별도로 **시간당** 돈다. Cloud Run Job의 `--args`는 생성 시 고정이라 **같은 이미지로 두 번째 Job**(`newsstore-summarizer`, args에 `--mode summary`) + 전용 Scheduler `newsstore-summary-hourly`로 배포한다. 코드/어휘 변경 반영은 아래 0)+이미지 갱신.
```
# 0) 코드 반영: processor 이미지 재빌드 + 두 인리치 Job(클러스터/요약) 이미지 갱신
gcloud builds submit --config infra/cloudbuild.processor.yaml \
  --substitutions=_IMAGE=asia-northeast3-docker.pkg.dev/daily-recap-498506/newsstore/processor:latest .
gcloud run jobs update newsstore-enricher \
  --image=asia-northeast3-docker.pkg.dev/daily-recap-498506/newsstore/processor:latest --region=asia-northeast3
gcloud run jobs update newsstore-summarizer \
  --image=asia-northeast3-docker.pkg.dev/daily-recap-498506/newsstore/processor:latest --region=asia-northeast3
# 1) 요약 전용 Job(같은 이미지, args만 다름; 비밀·SA·env 동일)
gcloud run jobs create newsstore-summarizer \
  --image=asia-northeast3-docker.pkg.dev/daily-recap-498506/newsstore/processor:latest \
  --region=asia-northeast3 \
  --service-account=newsstore-job@daily-recap-498506.iam.gserviceaccount.com \
  --set-env-vars=NEWSSTORE_BACKEND=firestore,GOOGLE_CLOUD_PROJECT=daily-recap-498506,APP_ENV=home \
  --update-secrets=GEMINI_API_KEY=gemini-api-key:latest \
  --command=python --args=-m,newsstore.entrypoints.run_enrich,--mode,summary
# 2) 수동 1회 실행 + 확인
gcloud run jobs execute newsstore-summarizer --region=asia-northeast3 --wait
gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="newsstore-summarizer"' \
  --freshness=10m --format="value(textPayload)" | Select-String "summary pass|aborted"
# 3) 시간당 Scheduler (cluster와 시차: 매시 5분). Bash가 cron 공백을 망가뜨리니 PowerShell에서.
gcloud scheduler jobs create http newsstore-summary-hourly --location=asia-northeast3 \
  --schedule="5 * * * *" \
  --uri="https://run.googleapis.com/v2/projects/daily-recap-498506/locations/asia-northeast3/jobs/newsstore-summarizer:run" \
  --http-method=POST --oauth-service-account-email=newsstore-job@daily-recap-498506.iam.gserviceaccount.com
```
- 튜닝 env: `NEWSSTORE_SUMMARY_BATCH`(런당 스캔/요약 스토리 수, 기본 10).
- 이후 코드 변경 반영은 §A처럼 재빌드 → **두 Job 모두** `--image` 갱신.

## 접근 방식 / 결정 (newsstore)
- **비파괴 우선**: 중복 제거·스팸 필터·TruthSocial 라벨 등은 **저장은 그대로 두고 `web/index.html`(뷰)에서** 처리(키워드 필터·제목 정규화 dedup). 튜닝·되돌리기 쉬움. DB레벨 변경은 사용자가 명시 요청 시.
- **본문 정책(무스크래핑 오버라이드):** 기본은 "피드가 주면 사용". 헤드라인-only라도 **화이트리스트 소스는 개별 기사 페이지를 fetch해 본문을 채운다**(`collect/body_fetch.py` — 한경 `.article-body`; 임팩트 뉴스일수록 풀본문이 완성도↑). **무차별 크롤링(전체 사이트 긁기)은 안 함** — 도달성·추출이 실증된 소스만 화이트리스트, 바운드(per-feed 상한·per-article 타임아웃·스로틀)로 IP 차단 위험 억제, 배포 스모크로 RSS까지 정상인지 확인. 설계 SSOT: `docs/superpowers/specs/2026-06-28-body-enrichment-korean-design.md`. 본문 부족 소스는 피드 추가도 병행.
- **피드 추가 전 curl 실측**(HTTP·item수·desc 유무) → 되는 것만 등록 → A 재배포.
- **콘솔 수동 대신 REST**로 GCP/Firebase 운영(인증 공유).
- 환경 두 축(`APP_ENV`=home/office, `NEWSSTORE_BACKEND`=sqlite/firestore)은 `README.md` 표 참조.

## 알아둘 함정
- 수집기는 **Cloud Run 데이터센터 IP**라 일부 사이트가 차단함(fxstreet 제거됨, Bloomberg 기사본문 403). → 기사 본문 fetch는 **도달 실증된 화이트리스트만**(한경 OK; Investing/Bloomberg/FT 기사페이지 403). 화이트리스트 fetch가 IP를 막히게 하면 RSS 수집까지 영향이므로 **바운드(상한·타임아웃·스로틀)+배포 스모크**로 관리(본문 정책 §접근 방식).
- 피드 추가는 "되는지 curl 테스트 → feeds.yaml → A 재배포" 순서.
