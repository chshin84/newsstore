# 운영 / 재배포 런북

배포는 **이미 완료**돼 라이브다. 이 문서는 이후 **변경분을 클라우드에 반영**하는 명령 모음이다.
(최초 1회 셋업 — 프로젝트/Firestore/Cloud Run/Scheduler/IAM/규칙/Hosting 생성 — 은 전부 끝났음.)

## 전제
- `gcloud`가 사용자 프로필에 인증돼 있어야 함 (`chshin84@gmail.com`, 프로젝트 `daily-recap-498506`).
  - 이 PC에선 PATH에 없어 풀경로 사용: `C:\Users\ho381\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd`
- **Firebase 관리/규칙/호스팅 REST 호출 시 quota project 헤더 필수**: `x-goog-user-project: daily-recap-498506` (없으면 403). 토큰은 `gcloud auth print-access-token`.

## 리소스 인벤토리
| 종류 | 이름 |
|------|------|
| GCP 프로젝트 | `daily-recap-498506` (asia-northeast3) |
| Firestore | `(default)` Native — 컬렉션 `items`, `feed_state` |
| Artifact Registry | `newsstore` → 이미지 `asia-northeast3-docker.pkg.dev/daily-recap-498506/newsstore/collector:latest` |
| Cloud Run Job | `newsstore-collector` (env `NEWSSTORE_BACKEND=firestore`, `GOOGLE_CLOUD_PROJECT=daily-recap-498506`, `APP_ENV=home`) |
| Cloud Scheduler | `newsstore-5min` (`*/5 * * * *`) |
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
현재: `source+published_at`(소스필터), `tags+published_at`(태그필터), `processed+fetched_at`(Step-2 큐) — 전부 READY.

## 알아둘 함정
- 수집기는 **Cloud Run 데이터센터 IP**라 일부 사이트가 차단함(fxstreet 제거됨, Bloomberg 기사본문 403). 본문은 **피드 자체 description**으로만 — 기사 스크래핑은 안 함.
- 피드 추가는 "되는지 curl 테스트 → feeds.yaml → A 재배포" 순서.
