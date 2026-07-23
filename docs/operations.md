# 운영 / 재배포 런북

이 문서는 **변경분을 클라우드에 반영**하는 명령 모음이다.
**0→배포 최초 셋업 절차(프로젝트/Firestore/Cloud Run/Scheduler/IAM/Firebase/규칙/Hosting/TTL 생성)는 `docs/setup.md` 참조.**

newsstore는 **뉴스 수집 전용**이다 — 뉴스 RSS 수집기, FMP 뉴스 수집기, 정적 사이트만 운영한다. 분석/LLM 잡은 없다. (FMP 팩터·가격 수집은 별개 로컬 레포 `DB-news-data`(DuckDB)로 이관됐다.)

## 전제
- `gcloud`가 사용자 프로필에 인증돼 있어야 함 (`chshin84@gmail.com`, 프로젝트 `daily-recap-498506`).
  - gcloud 풀경로(머신별): 집=`C:\Users\ho381\...`, 사내=`C:\Users\CHSHIN\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd`.
  - **사내(office)에서 gcloud SSL 차단 시 우회:** ePrism MITM 프록시가 최신 gcloud(urllib3 v2 strict)의 AKI 검증(`certificate verify failed: Missing Authority Key Identifier`)을 막으면 **옛 gcloud(402) 컨테이너 + ePrism CA** 편법으로 우회한다(`scripts/deploy-office.ps1`, Cloud Run Jobs는 `beta` 트랙). 집은 MITM 없어 평범하게 §A, 사내는 위 스크립트.
- **Firebase 관리/규칙/호스팅 REST 호출 시 quota project 헤더 필수**: `x-goog-user-project: daily-recap-498506` (없으면 403). 토큰은 `gcloud auth print-access-token`.
- 프로젝트/리전 변수는 루트 **`.env`**(`GOOGLE_CLOUD_PROJECT`, `GCP_REGION`). PowerShell 로드법은 `docs/setup.md` 참조.
- `newsstore-collect-all` 잡은 `FMP_API_KEY`(백엔드 전용 비밀)를 **Secret Manager**(`fmp-api-key`)로 주입한다. 커밋/이미지/로그 금지.
- 같은 `newsstore-collect-all` 잡이 `GEMINI_API_KEY`(백엔드 전용 비밀)도 **Secret Manager**(`gemini-api-key`)로 주입한다(임베딩 패스). RSS·네이버·FMP·임베딩이 한 잡으로 통합됐으므로 두 비밀 모두 이 잡 하나에 들어간다.

## 리소스 인벤토리
| 종류 | 이름 |
|------|------|
| GCP 프로젝트 | `daily-recap-498506` (asia-northeast3) |
| Firestore | `(default)` Native — 컬렉션 `items`·`feed_state`·`meta`·`item_vectors`·`job_health` |
| Artifact Registry | `newsstore` → 이미지 `asia-northeast3-docker.pkg.dev/daily-recap-498506/newsstore/collector:latest` |
| Cloud Run Job | `newsstore-collect-all` — RSS+네이버+FMP 병렬 수집 + 임베딩 패스(`run_collect_all`, secrets `gemini-api-key`·`fmp-api-key`·네이버 자격증명) |
| Cloud Run Job | `newsstore-backfill-embed` — 임베딩 백필 일회성 잡(`run_backfill_embed`, secret `gemini-api-key`) |
| Cloud Scheduler | `newsstore-collect-all-15min` (`*/15 * * * *`) — 통합 수집기 |
| Secret Manager | `fmp-api-key` (FMP 뉴스 Job에 `--set-secrets`로 주입; SA에 secretAccessor) |
| Secret Manager | `gemini-api-key` (collector Job에 `--set-secrets`로 주입 — 임베딩 패스; SA에 secretAccessor) |
| 서비스계정 | `newsstore-job@daily-recap-498506.iam.gserviceaccount.com` (roles: `datastore.user`, `run.invoker`) |
| Firebase Hosting | site `daily-recap-498506` → https://daily-recap-498506.web.app |
| Firebase 웹앱 | appId `1:754646487603:web:19e77fba52a8aacf1b0946` (config는 `web/index.html`에 인라인) |

---

## A. 수집기 재배포 (config/*.yaml 또는 수집기 코드 변경 시)
`config/feeds.yaml`·`config/naver_news.yaml`·`config/fmp_news.yaml`은 이미지에 `COPY`되므로
**반드시 재빌드 후 Job 갱신**해야 반영된다. RSS·네이버·FMP가 이제 `newsstore-collect-all`
Job 하나로 통합돼 있다(2026-07-23, 이전 3개 Job에서 병합).
```
# 1) 이미지 재빌드
gcloud builds submit --config infra/cloudbuild.yaml \
  --substitutions=_IMAGE=asia-northeast3-docker.pkg.dev/daily-recap-498506/newsstore/collector:latest .
# 2) Job을 새 이미지 digest로 재고정
gcloud beta run jobs update newsstore-collect-all \
  --image=asia-northeast3-docker.pkg.dev/daily-recap-498506/newsstore/collector:latest \
  --region=asia-northeast3
# 3) 즉시 1회 실행 (안 하면 다음 스케줄에 반영)
gcloud beta run jobs execute newsstore-collect-all --region=asia-northeast3 --wait
# 4) 확인
gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="newsstore-collect-all"' \
  --freshness=5m --format="value(textPayload)"
```

### 임베딩 패스 (newsstore-collect-all 잡 내)
- 수집 후 `embed_pass`가 story 대기분(`embed_pending`)을 런당 500건까지 임베딩해 `item_vectors`에 쓴다. Gemini 장애는 수집을 막지 않고, 실패분은 다음 15분 런이 재시도한다. 설정 드리프트(키 오류·차원 불일치)는 항목 처분 없이 run 실패로 승격된다.
- **키 부재 + 대기분 존재 = run 실패(exit 1)** — 조용한 무임베딩 고착을 스케줄러가 감지한다(대기 0건이면 경고 후 정상 종료 — 키 없는 로컬 수집 스모크 보존).
- **최초 롤아웃 순서**: 시크릿 바인딩을 **이미지 배포보다 먼저** 한다 — 순서가 뒤집히면 새 이미지가 대기분을 쌓으며 매 15분 런이 exit 1로 끝난다(수집분은 보존되고 키 바인딩 즉시 자가치유되는 의도된 fail-loud지만, 알림 소음을 피하려면 순서를 지킨다).
- **비밀**: `GEMINI_API_KEY`는 Secret Manager `gemini-api-key`로 주입한다(생성은 `docs/setup.md §8`). 키를 재발급했으면 새 버전을 올리고 잡을 재실행한다:
  ```
  printf '%s' "<NEW_GEMINI_API_KEY>" | gcloud secrets versions add gemini-api-key --data-file=-
  ```
- **배포 직후 실측(MEASURE-FIRST)**: 첫 런 로그에서 (collect 소요 + embed 소요) < task-timeout 600초를 확인하고, 넘치면 embed_pass cap을 낮춘다.

### 임베딩 백필 (일회성 — 배포 직후)
로컬 Docker로 실행한다(Cloud Run 타임아웃 제약 없음). 멱등 — 재실행 안전. 무진전(지속 장애)이면 exit 1로 끝나며 잔여분은 정규 15분 런이 이어받는다.
```bash
MSYS_NO_PATHCONV=1 docker compose run --rm collect python -m newsstore.entrypoints.run_backfill_embed
```

## B. 사이트 재배포 (web/ 변경 시)
Firebase CLI/Node 없이 **Hosting REST API**로 배포 (PowerShell).
> ⚠️ **Hosting 릴리스는 파일 전체 스냅샷이다.** populateFiles에 넣은 파일만 새 릴리스에 존재하고, 빠뜨린 파일은 **404로 사라진다**(이전 릴리스가 갖고 있어도 무관). `index.html`이 `./config.js`(Firebase 웹 설정)를 import하면 **둘 다** 올려야 한다 — 하나만 올리면 config.js 404 → Firebase 초기화 실패 → 무한 로딩. 그래서 아래는 `web/` 배포 대상 **전체**를 자동으로 올린다(파일 추가 시 `$deployFiles`만 갱신).
```powershell
$g="C:\Users\ho381\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
$tok=(& $g auth print-access-token).Trim()
$H=@{Authorization="Bearer $tok"; "x-goog-user-project"="daily-recap-498506"}
$site="https://firebasehosting.googleapis.com/v1beta1/projects/daily-recap-498506/sites/daily-recap-498506"
# 배포 대상 전체 (URL경로 → 로컬파일). 새 정적파일 추가 시 여기만 늘린다.
$deployFiles=@{ "/index.html"="D:\projects\data-only\web\index.html"; "/config.js"="D:\projects\data-only\web\config.js"; "/dashboard.html"="D:\projects\data-only\web\dashboard.html"; "/dashboard_logic.mjs"="D:\projects\data-only\web\dashboard_logic.mjs" }
$gzmap=@{}; $hashmap=@{}
foreach($p in $deployFiles.Keys){
  $raw=[IO.File]::ReadAllBytes($deployFiles[$p])
  $ms=New-Object IO.MemoryStream
  $gz=New-Object IO.Compression.GzipStream($ms,[IO.Compression.CompressionMode]::Compress)
  $gz.Write($raw,0,$raw.Length); $gz.Close(); $gzb=$ms.ToArray()
  $gzmap[$p]=$gzb; $hashmap[$p]=(([Security.Cryptography.SHA256]::Create().ComputeHash($gzb)|%{$_.ToString("x2")}) -join "")
}
$ver=Invoke-RestMethod -Method POST -Uri "$site/versions" -Headers $H -ContentType "application/json" -Body "{}"
$pop=Invoke-RestMethod -Method POST -Uri "https://firebasehosting.googleapis.com/v1beta1/$($ver.name):populateFiles" -Headers $H -ContentType "application/json" -Body (@{files=$hashmap}|ConvertTo-Json)
foreach($need in $pop.uploadRequiredHashes){
  $p=($hashmap.GetEnumerator()|Where-Object{$_.Value -eq $need}).Key
  Invoke-WebRequest -Method POST -Uri "$($pop.uploadUrl)/$need" -Headers $H -ContentType "application/octet-stream" -Body $gzmap[$p]|Out-Null
}
Invoke-RestMethod -Method PATCH -Uri "https://firebasehosting.googleapis.com/v1beta1/$($ver.name)?updateMask=status" -Headers $H -ContentType "application/json" -Body '{"status":"FINALIZED"}'|Out-Null
Invoke-RestMethod -Method POST -Uri "$site/releases?versionName=$($ver.name)" -Headers $H -ContentType "application/json" -Body "{}"|Out-Null
"deployed ($($deployFiles.Keys -join ', ')) -> https://daily-recap-498506.web.app"
```
배포 후 브라우저는 **Ctrl+F5**(캐시). 검증: 사이트 콘솔에 404 없는지.

## C. 보안 규칙 변경 (firestore.rules)
`firebaserules` REST로 ruleset 생성 + `cloud.firestore` release 갱신 (PowerShell, 헤더 `x-goog-user-project` 필수). 또는 Firebase 콘솔 → Firestore → 규칙에 붙여넣기. **전면 공개 read 모델**이다:
- **공개 read**: `items`·`meta`·`item_vectors`·`job_health` 모두 `allow read: if true`. 대시보드(`web/dashboard.html`)·뉴스 리더(`web/index.html`)가 **로그인 없이** 읽는다.
- **write는 전면 금지**(수집기는 Admin SDK라 규칙 우회). `feed_state`(폴링 커서)만 기본 거부.
- **노출 범위는 60일 버퍼뿐**(깊은 아카이브는 다운스트림 로컬 DB 몫이라 Firestore 밖). **구글 auth·허용목록 불요**(공개 모델). 배포는 `firebase deploy --only firestore:rules,hosting`.

## D. 복합 인덱스 추가
```
gcloud firestore indexes composite create --collection-group=items \
  --field-config=field-path=source,order=ascending \
  --field-config=field-path=published_at,order=descending --async
gcloud firestore indexes composite list --format="value(state,fields.fieldPath)"
```
현재 인덱스: `source+published_at`(소스 필터).

## F. TTL 정책 (content 컬렉션 60일 만료)
모든 content 컬렉션(`items`·`item_vectors`)은 `expire_at`을 TTL 정책이 보고 만료시킨다(비용 통제 — 저장 시각 + 60일; `item_vectors`는 원본 item의 `expire_at` 미러링). **`feed_state`·`meta`엔 TTL을 걸지 않는다**(폴링 커서 만료 시 증분 수집 어긋남). 최초 프로비저닝은 `docs/setup.md §7`(전 컬렉션 루프). 현재 상태 확인:
```
gcloud firestore fields ttl list --collection-group=items
```

## G. 잡 실패 알림 (Cloud Monitoring)
**왜:** Cloud Scheduler는 잡을 `:run`으로 **시작**시키고 HTTP 200(=시작 수락)만 받는다. 잡이 시작 직후 죽어도 스케줄러는 초록(성공)으로 보여 **조용한 실패**가 된다(Fail-Loud 위반). → Cloud Run Job **실패 실행 수>0**이면 알림.

지표: `run.googleapis.com/job/completed_execution_count` (resource `cloud_run_job`, metric label `result="failed"`). 잡(collect-all·backfill-embed) 공통 적용(job_name 필터 없이 전체).

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
- 보강(선택): 잡이 **아예 안 돈** 경우(스케줄러 자체 실패)는 위 지표로 안 잡힌다 — 스케줄러 실패 로그 알림을 별도로 추가.

## 접근 방식 / 결정 (newsstore)
- **비파괴 우선**: 중복 제거·스팸 필터·TruthSocial 라벨 등은 원본을 지우지 않는다. 수집 시점 `kind` 분류(`classify_kind`)로 라벨링하고, 노출은 `web/index.html`(뷰)이 `kind === "story"`만 보여주는 식으로 처리한다. 튜닝·되돌리기 쉽다.
- **본문 정책(무스크래핑 오버라이드):** 기본은 "피드가 주면 사용". 헤드라인-only라도 **화이트리스트 소스는 개별 기사 페이지를 fetch해 본문을 채운다**(`src/newsstore/collect/body_fetch.py` — 한경 `.article-body`). **무차별 크롤링은 안 함** — 도달성·추출이 실증된 소스만 화이트리스트, 바운드(per-feed 상한·per-article 타임아웃·스로틀)로 IP 차단 위험 억제, 배포 스모크로 RSS까지 정상인지 확인. 본문 부족 소스는 피드 추가도 병행.
- **피드 추가 전 curl 실측**(HTTP·item수·desc 유무) → 되는 것만 등록 → A 재배포.
- **콘솔 수동 대신 REST**로 GCP/Firebase 운영(인증 공유).
- 환경(`APP_ENV`=home/office, 저장소=Firestore 단일)은 `README.md` 표 참조.

## 알아둘 함정
- 수집기는 **Cloud Run 데이터센터 IP**라 일부 사이트가 차단함(fxstreet 제거됨, Bloomberg 기사본문 403). → 기사 본문 fetch는 **도달 실증된 화이트리스트만**(한경 OK; Investing/Bloomberg/FT 기사페이지 403). 화이트리스트 fetch가 IP를 막히게 하면 RSS 수집까지 영향이므로 **바운드(상한·타임아웃·스로틀)+배포 스모크**로 관리(본문 정책 §접근 방식).
- 피드 추가는 "되는지 curl 테스트 → feeds.yaml → A 재배포" 순서.
