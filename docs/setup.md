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
gcloud run jobs create newsstore-collect-all \
  --image=<REGION>-docker.pkg.dev/<PROJECT_ID>/newsstore/collector:latest --region=<REGION> \
  --command=python --args=-m,newsstore.entrypoints.run_collect_all \
  --service-account=$SA \
  --set-env-vars=GOOGLE_CLOUD_PROJECT=<PROJECT_ID>,APP_ENV=home \
  --max-retries=1 --task-timeout=600
# 네이버 자격증명(NAVER_CLIENT_ID/NAVER_CLIENT_SECRET)은 §8에서 생성·주입한다
# (누락하면 이 잡은 NAVER_CLIENT_ID 미설정으로 fail-loud 실패하므로 아래 스모크 전에 §8을 마친다).
gcloud run jobs execute newsstore-collect-all --region=<REGION> --wait   # 스모크: Firestore에 items 쌓이는지
# 임베딩 백필 잡(일회성·멱등) — 같은 이미지를 쓰고 CMD만 다르다. 언제 쓰는지는 docs/operations.md 참조.
# 백필은 대기분이 많아 한 번에 오래 도므로 task-timeout을 정규 수집보다 길게 잡는다.
gcloud run jobs create newsstore-backfill-embed \
  --image=<REGION>-docker.pkg.dev/<PROJECT_ID>/newsstore/collector:latest --region=<REGION> \
  --command=python --args=-m,newsstore.entrypoints.run_backfill_embed \
  --service-account=$SA \
  --set-env-vars=GOOGLE_CLOUD_PROJECT=<PROJECT_ID>,APP_ENV=home \
  --max-retries=1 --task-timeout=3600
# 이 잡도 임베딩을 하므로 §8의 gemini-api-key를 같은 방식으로 이 잡에도 주입한다.
```

## 4. Cloud Scheduler (15분마다)
```
gcloud scheduler jobs create http newsstore-collect-all-15min --location=<REGION> --schedule="*/15 * * * *" \
  --uri="https://<REGION>-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/<PROJECT_ID>/jobs/newsstore-collect-all:run" \
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
**인덱스**(gcloud): `firestore.indexes.json`에 정의된 것은 둘이다. `items`의 `source+published_at`은 소스 필터와 리서치 탭이 쓰고, `items`의 `source+fetched_at`은 상태 탭의 소스별 최신 1건 조회가 쓴다.
```
gcloud firestore indexes composite create --collection-group=items \
  --field-config=field-path=source,order=ascending --field-config=field-path=published_at,order=descending --async
gcloud firestore indexes composite create --collection-group=items \
  --field-config=field-path=source,order=ascending --field-config=field-path=fetched_at,order=descending --async
```

## 7. TTL 정책 (content 컬렉션 60일 만료 — 비용 통제)
content 컬렉션(`items`·`item_vectors`)은 각 문서의 `expire_at`을 Firestore TTL 정책이 보고 만료시킨다(저장 시각 + 60일 — 비용 통제). **`feed_state`·`meta`·`job_health`엔 TTL을 걸지 않는다**(폴링 커서·발행 메타·잡 상태는 만료 대상이 아니다). 컬렉션마다 한 번씩 정책을 건다:
```
for c in items item_vectors ; do
  gcloud firestore fields ttl update expire_at --collection-group=$c \
    --enable-ttl --project=<PROJECT_ID>
done
```
(콘솔 → Firestore → TTL에서도 컬렉션 그룹별 `expire_at` 필드를 지정할 수 있다. 새 컬렉션을 계약에 추가하면 이 목록도 함께 늘린다.)

## 8. 백엔드 비밀 (collect_all) — FMP·Gemini·네이버
collect_all의 FMP 뉴스 수집은 FMP REST를 호출하므로 `FMP_API_KEY`(백엔드 전용 비밀)가 필요하다 — Secret Manager로 만들어 §3의 `newsstore-collect-all` 잡에 주입한다(커밋/이미지/로그 금지). (FMP 시장 가격·펀더멘털은 이 repo가 아니라 로컬 레포 `DB-news-data`가 수집한다.)
```
# (a) 비밀 생성 + Job SA에 접근 권한
printf '%s' "<FMP_API_KEY>" | gcloud secrets create fmp-api-key --data-file=- --replication-policy=automatic
gcloud secrets add-iam-policy-binding fmp-api-key \
  --member="serviceAccount:$SA" --role=roles/secretmanager.secretAccessor
# (b) collect_all 잡에 주입
gcloud run jobs update newsstore-collect-all --region=<REGION> \
  --update-secrets=FMP_API_KEY=fmp-api-key:latest
```

**Gemini 키(임베딩)**: collect_all 잡의 임베딩 패스는 Gemini API를 호출하므로 `GEMINI_API_KEY`(백엔드 전용 비밀)가 필요하다 — FMP와 같은 패턴으로 Secret Manager에 만들고 §3에서 생성한 `newsstore-collect-all` 잡에 주입한다.
```
# (a) 비밀 생성 + Job SA에 접근 권한
printf '%s' "<GEMINI_API_KEY>" | gcloud secrets create gemini-api-key --data-file=- --replication-policy=automatic
gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:$SA" --role=roles/secretmanager.secretAccessor
# (b) collect_all 잡에 주입
gcloud run jobs update newsstore-collect-all \
  --set-secrets=GEMINI_API_KEY=gemini-api-key:latest --region=<REGION>
```

**네이버 검색 API 자격증명**: collect_all의 네이버 뉴스 수집은 네이버 검색 API를 호출하므로 `NAVER_CLIENT_ID`·`NAVER_CLIENT_SECRET`(백엔드 전용 비밀)이 필요하다 — 네이버 개발자센터에서 애플리케이션을 등록해 발급받은 뒤 FMP·Gemini와 같은 패턴으로 Secret Manager에 만들고 §3에서 생성한 `newsstore-collect-all` 잡에 주입한다. `run_collect_all`이 두 값을 `os.environ`으로 fail-loud 읽으므로 주입 전에는 §3의 스모크 실행이 그 자리에서 실패한다.
```
# (a) 비밀 생성 + Job SA에 접근 권한
printf '%s' "<NAVER_CLIENT_ID>" | gcloud secrets create naver-client-id --data-file=- --replication-policy=automatic
printf '%s' "<NAVER_CLIENT_SECRET>" | gcloud secrets create naver-client-secret --data-file=- --replication-policy=automatic
for s in naver-client-id naver-client-secret ; do
  gcloud secrets add-iam-policy-binding $s \
    --member="serviceAccount:$SA" --role=roles/secretmanager.secretAccessor
done
# (b) collect_all 잡에 주입
gcloud run jobs update newsstore-collect-all --region=<REGION> \
  --update-secrets=NAVER_CLIENT_ID=naver-client-id:latest,NAVER_CLIENT_SECRET=naver-client-secret:latest
```

## 9. 사이트 배포 (Firebase Hosting, REST)
기본 site(`<PROJECT_ID>`)는 자동 생성됨. 업로드 절차는 `docs/operations.md` **§B** 참조(version → populateFiles → gzip+sha256 업로드 → finalize → release).

→ 완료되면 **https://<PROJECT_ID>.web.app** 에서 서빙된다. 이후 모든 변경은 `docs/operations.md`.
