# 최초 셋업 (0 → 배포)

이 프로젝트를 **밑바닥부터** GCP에 올리는 절차. (이 문서는 재해복구·새 프로젝트 복제·포크 배포용 기록.) 이후 변경 반영은 `docs/operations.md`.

> **firebase CLI/Node 없이 gcloud + REST API만으로** 전부 프로비저닝할 수 있다.

## 전제 / 변수
- `gcloud` 설치 + 로그인(`gcloud auth login`, `gcloud auth application-default login`), GCP **결제 계정** 1개.
- 변수는 루트 **`.env`** 에서 (`GOOGLE_CLOUD_PROJECT`, `GCP_REGION`). 아래 명령의 `<PROJECT_ID>`=`GOOGLE_CLOUD_PROJECT`, `<REGION>`=`GCP_REGION`. PowerShell 세션에 로드:
  ```powershell
  Get-Content .env | ? { $_ -match '^\s*[^#].*=' } | % { $k,$v=$_ -split '=',2; Set-Item "env:$($k.Trim())" $v.Trim() }
  # 이후: $env:GOOGLE_CLOUD_PROJECT , $env:GCP_REGION
  ```
- **Firebase REST 호출엔 헤더 `x-goog-user-project: <PROJECT_ID>` 필수**(없으면 quota project 403). 토큰 = `gcloud auth print-access-token`.

## 1. 프로젝트 · API · Firestore
```
gcloud projects create <PROJECT_ID>
gcloud config set project <PROJECT_ID>
gcloud billing projects link <PROJECT_ID> --billing-account=<BILLING_ID>
gcloud services enable firestore.googleapis.com run.googleapis.com cloudscheduler.googleapis.com \
  cloudbuild.googleapis.com artifactregistry.googleapis.com \
  firebase.googleapis.com firebasehosting.googleapis.com firebaserules.googleapis.com
gcloud firestore databases create --location=<REGION>      # Native 모드
```

## 2. 이미지 (Artifact Registry + Cloud Build)
```
gcloud artifacts repositories create newsstore --repository-format=docker --location=<REGION>
gcloud builds submit --config infra/cloudbuild.yaml \
  --substitutions=_IMAGE=<REGION>-docker.pkg.dev/<PROJECT_ID>/newsstore/collector:latest .
```

## 3. 서비스계정 · IAM · Cloud Run Job
```
gcloud iam service-accounts create newsstore-job
SA=newsstore-job@<PROJECT_ID>.iam.gserviceaccount.com
gcloud projects add-iam-policy-binding <PROJECT_ID> --member="serviceAccount:$SA" --role="roles/datastore.user"
gcloud projects add-iam-policy-binding <PROJECT_ID> --member="serviceAccount:$SA" --role="roles/run.invoker"
gcloud run jobs create newsstore-collector \
  --image=<REGION>-docker.pkg.dev/<PROJECT_ID>/newsstore/collector:latest --region=<REGION> \
  --service-account=$SA \
  --set-env-vars=GOOGLE_CLOUD_PROJECT=<PROJECT_ID>,APP_ENV=home \
  --max-retries=1 --task-timeout=600
gcloud run jobs execute newsstore-collector --region=<REGION> --wait   # 스모크: Firestore에 items 쌓이는지
```

## 4. Cloud Scheduler (5분마다)
```
gcloud scheduler jobs create http newsstore-5min --location=<REGION> --schedule="*/5 * * * *" \
  --uri="https://<REGION>-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/<PROJECT_ID>/jobs/newsstore-collector:run" \
  --http-method=POST --oauth-service-account-email=$SA
```

## 5. Firebase 추가 + 웹앱 + config (REST, firebase CLI 없이)
PowerShell. `$H`엔 `Authorization: Bearer <token>` + `x-goog-user-project: <PROJECT_ID>`.
```powershell
$base="https://firebase.googleapis.com/v1beta1/projects/<PROJECT_ID>"
# (a) GCP 프로젝트에 Firebase 활성화 (LRO → 폴링)
Invoke-RestMethod -Method POST -Uri "$base:addFirebase" -Headers $H -ContentType "application/json" -Body "{}"
# (b) 웹앱 생성 (LRO → 폴링) → 응답 appId
Invoke-RestMethod -Method POST -Uri "$base/webApps" -Headers $H -ContentType "application/json" -Body '{"displayName":"newsstore-web"}'
# (c) config 발급 → apiKey 등
Invoke-RestMethod -Method GET -Uri "$base/webApps/<APP_ID>/config" -Headers $H
```
→ 받은 `apiKey/authDomain/projectId/...`를 **`web/index.html`의 `firebaseConfig`** 에 인라인(공개 read 전용이라 노출 안전).

## 6. 보안 규칙 + 복합 인덱스
**규칙**(`firebaserules` REST): ruleset 생성 → `cloud.firestore` release 갱신.
```powershell
$rb="https://firebaserules.googleapis.com/v1/projects/<PROJECT_ID>"
$rules=Get-Content firestore.rules -Raw
$rs=Invoke-RestMethod -Method POST -Uri "$rb/rulesets" -Headers $H -ContentType "application/json" -Body (@{source=@{files=@(@{name="firestore.rules";content=$rules})}}|ConvertTo-Json -Depth 6)
Invoke-RestMethod -Method POST -Uri "$rb/releases" -Headers $H -ContentType "application/json" -Body (@{name="projects/<PROJECT_ID>/releases/cloud.firestore";rulesetName=$rs.name}|ConvertTo-Json)
```
(또는 Firebase 콘솔 → Firestore → 규칙에 붙여넣기.)
**인덱스**(gcloud): `firestore.indexes.json`에 정의된 것 = `source+published_at`(소스 필터). 가격·펀더멘털은 문서 키 직접 조회라 복합 인덱스가 필요 없다.
```
gcloud firestore indexes composite create --collection-group=items \
  --field-config=field-path=source,order=ascending --field-config=field-path=published_at,order=descending --async
```

## 7. TTL 정책 (content 컬렉션 30일 만료 — 비용 통제)
`items`·`prices`·`price_bars`·`fundamentals`는 각 문서의 `expire_at`을 Firestore TTL 정책이 보고 만료시킨다(`items`·`prices`·`fundamentals`는 저장 시각 + 30일, `price_bars`는 바 날짜 + 30일). **`feed_state`엔 TTL을 걸지 않는다**(폴링 커서가 만료되면 증분 수집이 어긋난다). `price_bars`(5분봉 완전 스트림)는 문서 수가 가장 빠르게 늘어 TTL이 특히 중요하다.
```
gcloud firestore fields ttl update expire_at --collection-group=items \
  --enable-ttl --project=<PROJECT_ID>
gcloud firestore fields ttl update expire_at --collection-group=prices \
  --enable-ttl --project=<PROJECT_ID>
gcloud firestore fields ttl update expire_at --collection-group=price_bars \
  --enable-ttl --project=<PROJECT_ID>
gcloud firestore fields ttl update expire_at --collection-group=fundamentals \
  --enable-ttl --project=<PROJECT_ID>
```
(콘솔 → Firestore → TTL에서도 컬렉션 그룹별 `expire_at` 필드를 지정할 수 있다.)

## 8. 가격·펀더멘털 수집 Job (FMP)
가격(`run_prices`)·펀더멘털(`run_fundamentals`)은 FMP REST를 호출하므로 `FMP_API_KEY`(백엔드 전용 비밀)가 필요하다 — **Secret Manager**로 주입한다(커밋/이미지/로그 금지). 같은 collector 이미지를 쓰고 CMD만 다르다.
```
# (a) 비밀 생성 + Job SA에 접근 권한
printf '%s' "<FMP_API_KEY>" | gcloud secrets create fmp-api-key --data-file=- --replication-policy=automatic
gcloud secrets add-iam-policy-binding fmp-api-key \
  --member="serviceAccount:$SA" --role=roles/secretmanager.secretAccessor
# (b) 가격 수집 Job (같은 이미지, CMD 오버라이드 + 비밀 주입)
gcloud run jobs create newsstore-prices \
  --image=<REGION>-docker.pkg.dev/<PROJECT_ID>/newsstore/collector:latest --region=<REGION> \
  --service-account=$SA --set-env-vars=GOOGLE_CLOUD_PROJECT=<PROJECT_ID>,APP_ENV=home \
  --update-secrets=FMP_API_KEY=fmp-api-key:latest \
  --command=python --args=-m,newsstore.entrypoints.run_prices --max-retries=1 --task-timeout=600
# (c) 펀더멘털 수집 Job
gcloud run jobs create newsstore-fundamentals \
  --image=<REGION>-docker.pkg.dev/<PROJECT_ID>/newsstore/collector:latest --region=<REGION> \
  --service-account=$SA --set-env-vars=GOOGLE_CLOUD_PROJECT=<PROJECT_ID>,APP_ENV=home \
  --update-secrets=FMP_API_KEY=fmp-api-key:latest \
  --command=python --args=-m,newsstore.entrypoints.run_fundamentals --max-retries=1 --task-timeout=600
# (d) 스케줄러(예: 가격 시간당, 펀더멘털 일 1회). 수집기 패턴과 동일한 :run 호출
gcloud scheduler jobs create http newsstore-prices-hourly --location=<REGION> \
  --schedule="10 * * * *" \
  --uri="https://<REGION>-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/<PROJECT_ID>/jobs/newsstore-prices:run" \
  --http-method=POST --oauth-service-account-email=$SA
gcloud scheduler jobs create http newsstore-fundamentals-daily --location=<REGION> \
  --schedule="30 6 * * *" \
  --uri="https://<REGION>-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/<PROJECT_ID>/jobs/newsstore-fundamentals:run" \
  --http-method=POST --oauth-service-account-email=$SA
```

## 9. 사이트 배포 (Firebase Hosting, REST)
기본 site(`<PROJECT_ID>`)는 자동 생성됨. 업로드 절차는 `docs/operations.md` **§B** 참조(version → populateFiles → gzip+sha256 업로드 → finalize → release).

→ 완료되면 **https://<PROJECT_ID>.web.app** 에서 서빙된다. 이후 모든 변경은 `docs/operations.md`.
