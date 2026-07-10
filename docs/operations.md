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
| Cloud Run Job | `newsstore-collector` (env `GOOGLE_CLOUD_PROJECT=daily-recap-498506`, `APP_ENV=home`) |
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
  --set-env-vars=GOOGLE_CLOUD_PROJECT=daily-recap-498506,APP_ENV=home \
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
  --set-env-vars=GOOGLE_CLOUD_PROJECT=daily-recap-498506,APP_ENV=home \
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
- 스토리 시간창 튜닝(#9, 재빌드 없이 env): `NEWSSTORE_OPEN_WINDOW_HOURS`(열린 스토리 비교 창, 기본 48) · `NEWSSTORE_CLOSE_AFTER_HOURS`(무활동 close, 기본 24). 잘못된 값은 기동 시 즉시 에러(FAIL-LOUD).
  - **측정(값 결정 전)**: `stories`의 `first_seen`/`last_seen` 분포로 실제 스토리 수명을 본 뒤 창을 정한다(짧게=오병합↓·빠른 종결 / 길게=장기 전개 이어붙임·노이즈↑).
- gray-band 클러스터 임계 튜닝(#6, env): `NEWSSTORE_GRAY_BAND_LO`(기본 0.62) · `NEWSSTORE_GRAY_BAND_HI`(기본 0.80). sim≥hi 자동 합류 / sim<lo 자동 신규 / 그 사이만 LLM 판정. `0≤lo≤hi≤1` 위반은 기동 시 에러(FAIL-LOUD).
  - **기본값 근거**: 운영 측정에서 스토리 최근접쌍 코사인이 중앙 0.657·p95 0.767이라, 이전 0.55/0.75(이란+코스피 차용값)는 거의 모든 비교가 LLM 판정 구간에 걸려 호출이 과도했다. 0.62/0.80으로 올려 결정론 구간을 넓혔다. 추가 조정은 위 env로.
- dual score 게이트 튜닝(#7, env): `NEWSSTORE_SCORE_MIN_MEMBERS`(비금융자산/emergent를 채점하는 최소 멤버수, 기본 2). standing/watch 렌즈는 게이트 면제(상시 채점).
  - **측정(값 결정 전)**: `stories`의 `risk`/`impact` 분포·게이트 통과율을 떠서 임계를 정한다. 루브릭(0~3 의미)·REF_WINDOW·EVENT_SANITY_DAYS는 코드 상수(라이브 분포 보고 후속 조정).
- 태그 어휘 범위 측정(#8): `enrich.tag_report.tag_coverage(items_tags, vocab)`로 태그 빈도·무태그율·어휘밖(out_of_vocab) 태그를 본 뒤 통제 어휘(`config/taxonomy.yaml`) 범위를 정한다. 라이브 집계 예:
  ```python
  from newsstore.store.factory import make_store
  from newsstore.enrich.tag_report import tag_coverage
  with make_store() as s:
      tags = [(d.to_dict() or {}).get("tags", []) for d in s.db.collection("items").stream()]
  print(tag_coverage(tags))   # vocab=set(taxonomy 티커/엔티티)로 out_of_vocab도
  ```
- 이후 코드 변경 반영은 §A처럼 재빌드 → **두 Job 모두** `--image` 갱신.

## G. 잡 실패 알림 (Cloud Monitoring) — #13
**왜:** Cloud Scheduler는 잡을 `:run`으로 **시작**시키고 HTTP 200(=시작 수락)만 받는다. 잡이 시작 직후 죽어도 스케줄러는 초록(성공)으로 보여 **조용한 실패**가 된다(Fail-Loud 위반). → Cloud Run Job **실패 실행 수>0**이면 알림.

지표: `run.googleapis.com/job/completed_execution_count` (resource `cloud_run_job`, metric label `result="failed"`). 6개 잡(collector·enricher·lenser·scorer·article·summarizer) 공통 적용(job_name 필터 없이 전체).

```bash
# 1) 알림 채널(이메일) — 1회. 채널 ID를 받아둔다.
gcloud beta monitoring channels create --display-name="newsstore-alert" \
  --type=email --channel-labels=email_address=chshin84@gmail.com \
  --format="value(name)"            # → projects/daily-recap-498506/notificationChannels/XXXX

# 2) 알림 정책 — 실패 실행 수>0 (정렬창 1h). <CHANNEL>에 위 값 대입.
cat > /tmp/job-fail-policy.json <<'JSON'
{
  "displayName": "newsstore Cloud Run Job failures",
  "combiner": "OR",
  "conditions": [{
    "displayName": "job failed executions > 0",
    "conditionThreshold": {
      "filter": "resource.type=\"cloud_run_job\" AND metric.type=\"run.googleapis.com/job/completed_execution_count\" AND metric.label.\"result\"=\"failed\"",
      "comparison": "COMPARISON_GT",
      "thresholdValue": 0,
      "duration": "0s",
      "aggregations": [{"alignmentPeriod": "3600s", "perSeriesAligner": "ALIGN_SUM"}]
    }
  }],
  "notificationChannels": ["<CHANNEL>"]
}
JSON
gcloud alpha monitoring policies create --policy-from-file=/tmp/job-fail-policy.json
```
- 확인: `gcloud alpha monitoring policies list --format="value(displayName,enabled)"`. 콘솔 Monitoring → Alerting에도 보임.
- 보강(선택): 잡이 **아예 안 돈** 경우(스케줄러 자체 실패)는 위 지표로 안 잡힌다 — execution 부재 자체를 보려면 `--mode` 잡별 last-success heartbeat(미래 #13 후속) 또는 스케줄러 실패 로그 알림을 추가.

## H. 클라우드 컷 절차 (로컬 레이더 작업장 전환 시)
로컬 레이더 작업장(`docs/superpowers/specs/2026-07-10-local-radar-workbench-design.md`)이 자리잡으면 클라우드 인리치/분석 5개 패스를 정지하고 수집기만 유지한다. 로컬 sync는 프로덕션 Firestore를 **무인증 REST(`runQuery`)로 공개 읽기**하는 전제 위에 서 있으므로, 컷을 실행하기 전에 그 전제가 살아 있는지 스모크로 확인한다.

**컷 실행 전 게이트**: 프로덕션 `items`에 무인증 `runQuery` 1페이지 스모크(`curl POST https://firestore.googleapis.com/v1/projects/<프로젝트>/databases/(default)/documents:runQuery` — `limit 3`)가 200을 반환하는지 확인한다. 실패하면 sync 전제(공개 읽기 REST)가 깨진 것이므로 컷을 멈추고 조사한다.

**절차**(스펙 §8):
1. `gcloud scheduler jobs pause newsstore-enrich-10min | newsstore-summary-hourly | newsstore-lens-10min | newsstore-score-10min | newsstore-article-10min`(5건 — collector `newsstore-5min`은 유지).
2. frames/report 잡·스케줄러는 애초에 만들지 않는다(기존 미배포 상태 유지 — 이전 배포 체크리스트의 해당 항목 폐기).
3. `web/index.html` 변경분(피드 탭 기본·스토리/리포트 탭 숨김) Hosting 재배포(§B).
4. `firestore.rules`는 무변경(items·stories·meta 공개 읽기 — sync가 사용).
5. 재개 절차(전 단계 가역): pause한 잡 resume + Hosting 롤백 + **로컬 `local.db` 전체 재동기화**(정지 기간 밖 문서 갱신이 증분 창을 벗어나므로 — 캐시라 재구축이 안전하다).

## I. 로컬 레이더 작업장 운영
로컬 전용 패키지 `src/newsstore/radar/`가 Firestore를 SQLite로 동기화하고 순수 산수로 레이더 신호·종목 스테이션·일보를 산출한다(신규 LLM 콜 0). 상세 설계는 `docs/superpowers/specs/2026-07-10-local-radar-workbench-design.md`.

**데일리 커맨드**:
```
docker compose run --rm sync && docker compose run --rm prices; docker compose run --rm radar
```
prices가 실패해도(예: 휴장·소스 파손) radar는 진행한다(`;`로 이어 결측 표기 우선).

**산출·원장 위치**:
- 일보: `radar_out/`
- 판단 원장(게이트·판단·리뷰): `journal/journal.jsonl`
- 게이트 시드: `radar/gates.yaml`
- 프레임(리스크/프리미엄/관찰점) 시드: `radar/frames.json`

**백테스트**:
```
docker compose run --rm radar python -m newsstore.entrypoints.run_radar --mode backtest
```

**알려진 정상 신호**: 3일 이상 연휴(설·추석)에는 prices의 "신규 0행 3일 연속" 크래시가 예정대로 발생한다. 이것은 소스 파손이 아니라 휴장이며, 다음 거래일 재실행에서 자동으로 해소된다(거래일 판정기를 별도로 만들지 않은 YAGNI의 수용 비용 — 스펙 §3.2).

## 접근 방식 / 결정 (newsstore)
- **비파괴 우선**: 중복 제거·스팸 필터·TruthSocial 라벨 등은 **저장은 그대로 두고 `web/index.html`(뷰)에서** 처리(키워드 필터·제목 정규화 dedup). 튜닝·되돌리기 쉬움. DB레벨 변경은 사용자가 명시 요청 시.
- **본문 정책(무스크래핑 오버라이드):** 기본은 "피드가 주면 사용". 헤드라인-only라도 **화이트리스트 소스는 개별 기사 페이지를 fetch해 본문을 채운다**(`src/newsstore/collect/body_fetch.py` — 한경 `.article-body`; 임팩트 뉴스일수록 풀본문이 완성도↑). **무차별 크롤링(전체 사이트 긁기)은 안 함** — 도달성·추출이 실증된 소스만 화이트리스트, 바운드(per-feed 상한·per-article 타임아웃·스로틀)로 IP 차단 위험 억제, 배포 스모크로 RSS까지 정상인지 확인. 설계 SSOT: `docs/superpowers/specs/2026-06-28-body-enrichment-korean-design.md`. 본문 부족 소스는 피드 추가도 병행.
- **피드 추가 전 curl 실측**(HTTP·item수·desc 유무) → 되는 것만 등록 → A 재배포.
- **콘솔 수동 대신 REST**로 GCP/Firebase 운영(인증 공유).
- 환경(`APP_ENV`=home/office, 저장소=Firestore 단일)은 `README.md` 표 참조.

## 알아둘 함정
- 수집기는 **Cloud Run 데이터센터 IP**라 일부 사이트가 차단함(fxstreet 제거됨, Bloomberg 기사본문 403). → 기사 본문 fetch는 **도달 실증된 화이트리스트만**(한경 OK; Investing/Bloomberg/FT 기사페이지 403). 화이트리스트 fetch가 IP를 막히게 하면 RSS 수집까지 영향이므로 **바운드(상한·타임아웃·스로틀)+배포 스모크**로 관리(본문 정책 §접근 방식).
- 피드 추가는 "되는지 curl 테스트 → feeds.yaml → A 재배포" 순서.
