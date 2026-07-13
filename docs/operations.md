# 운영 / 재배포 런북

이 문서는 **변경분을 클라우드에 반영**하는 명령 모음이다.
**0→배포 최초 셋업 절차(프로젝트/Firestore/Cloud Run/Scheduler/IAM/Firebase/규칙/Hosting/TTL 생성)는 `docs/setup.md` 참조.**

newsstore는 **수집 전용**이다 — 뉴스 수집기, 가격 수집기(FMP), 펀더멘털 수집기(FMP), 정적 사이트만 운영한다. 분석/LLM 잡은 없다.

## 전제
- `gcloud`가 사용자 프로필에 인증돼 있어야 함 (`chshin84@gmail.com`, 프로젝트 `daily-recap-498506`).
  - gcloud 풀경로(머신별): 집=`C:\Users\ho381\...`, 사내=`C:\Users\CHSHIN\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd`.
  - **사내(office)에서 gcloud SSL 차단 시 우회:** ePrism MITM 프록시가 최신 gcloud(urllib3 v2 strict)의 AKI 검증(`certificate verify failed: Missing Authority Key Identifier`)을 막으면 **옛 gcloud(402) 컨테이너 + ePrism CA** 편법으로 우회한다(`scripts/deploy-office.ps1`, Cloud Run Jobs는 `beta` 트랙). 집은 MITM 없어 평범하게 §A/§E, 사내는 위 스크립트.
- **Firebase 관리/규칙/호스팅 REST 호출 시 quota project 헤더 필수**: `x-goog-user-project: daily-recap-498506` (없으면 403). 토큰은 `gcloud auth print-access-token`.
- 프로젝트/리전 변수는 루트 **`.env`**(`GOOGLE_CLOUD_PROJECT`, `GCP_REGION`). PowerShell 로드법은 `docs/setup.md` 참조.
- 가격·펀더멘털 잡은 `FMP_API_KEY`(백엔드 전용 비밀)를 **Secret Manager**(`fmp-api-key`)로 주입한다. 커밋/이미지/로그 금지.

## 리소스 인벤토리
| 종류 | 이름 |
|------|------|
| GCP 프로젝트 | `daily-recap-498506` (asia-northeast3) |
| Firestore | `(default)` Native — 컬렉션 `items`·`feed_state`·`meta`·`prices`·`price_bars` + 팩터 계약 컬렉션(`income`·`ratios`·`prices_eod`·… — docs/firestore-contract.md) |
| Artifact Registry | `newsstore` → 이미지 `asia-northeast3-docker.pkg.dev/daily-recap-498506/newsstore/collector:latest` |
| Cloud Run Job | `newsstore-collector` — 뉴스 수집(`run_collect`) |
| Cloud Run Job | `newsstore-prices` — 가격 5분봉(`run_prices`, secret `fmp-api-key`) |
| Cloud Run Job | `newsstore-factors` — 팩터·펀더멘털 수집(`run_factors`, secret `fmp-api-key`) |
| Cloud Scheduler | `newsstore-5min` (`*/5 * * * *`) — 수집기 |
| Cloud Scheduler | `newsstore-prices-5min` (`*/5 * * * *`) — 가격 5분봉 |
| Cloud Scheduler | `newsstore-factors-weekly` (예 `30 6 * * 0`) — 팩터·펀더멘털 (배당조정 EOD는 daily로 별도) |
| Secret Manager | `fmp-api-key` (prices·factors Job에 `--update-secrets`로 주입; SA에 secretAccessor) |
| 서비스계정 | `newsstore-job@daily-recap-498506.iam.gserviceaccount.com` (roles: `datastore.user`, `run.invoker`) |
| Firebase Hosting | site `daily-recap-498506` → https://daily-recap-498506.web.app |
| Firebase 웹앱 | appId `1:754646487603:web:19e77fba52a8aacf1b0946` (config는 `web/index.html`에 인라인) |

---

## A. 수집기 재배포 (config/feeds.yaml 또는 수집기 코드 변경 시)
`config/feeds.yaml`은 이미지에 `COPY` 되므로 **반드시 재빌드 후 Job 갱신**해야 반영된다. 세 수집 Job(collector·prices·factors)이 같은 이미지를 쓰므로, 코드 변경 시 이미지 1개를 재빌드하고 세 Job 모두를 새 이미지로 갱신한다.
```
# 1) 이미지 재빌드 ([gcp] 타깃 = google-cloud-firestore 포함)
gcloud builds submit --config infra/cloudbuild.yaml \
  --substitutions=_IMAGE=asia-northeast3-docker.pkg.dev/daily-recap-498506/newsstore/collector:latest .
# 2) 세 Job을 새 이미지 digest로 재고정
for j in newsstore-collector newsstore-prices newsstore-factors; do
  gcloud run jobs update "$j" \
    --image=asia-northeast3-docker.pkg.dev/daily-recap-498506/newsstore/collector:latest \
    --region=asia-northeast3
done
# 3) 즉시 1회 실행 (안 하면 다음 스케줄에 반영)
gcloud run jobs execute newsstore-collector --region=asia-northeast3 --wait
# 4) 확인 (실패 피드 / 수집 수)
gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="newsstore-collector"' \
  --freshness=5m --format="value(textPayload)" | Select-String "feed\(s\) failed|collected .* new item"
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
$deployFiles=@{ "/index.html"="D:\projects\news-store\newsstore\web\index.html"; "/config.js"="D:\projects\news-store\newsstore\web\config.js" }
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
`firebaserules` REST로 ruleset 생성 + `cloud.firestore` release 갱신 (PowerShell, 헤더 `x-goog-user-project` 필수). 또는 Firebase 콘솔 → Firestore → 규칙에 붙여넣기. 공개 read 컬렉션은 `items`·`meta`·`prices`(웹 확인 UI). 팩터 컬렉션과 `price_bars`는 다운스트림 전용(공개 read 아님), `feed_state`는 비공개다.

## D. 복합 인덱스 추가
```
gcloud firestore indexes composite create --collection-group=items \
  --field-config=field-path=source,order=ascending \
  --field-config=field-path=published_at,order=descending --async
gcloud firestore indexes composite list --format="value(state,fields.fieldPath)"
```
현재 인덱스: `source+published_at`(소스 필터). 가격·펀더멘털은 문서 키 직접 조회라 복합 인덱스가 없다.

## E. 가격·펀더멘털 수집 재배포 (FMP)
가격(`run_prices`)·펀더멘털(`run_factors`)은 **수집기와 같은 이미지**를 쓰고 CMD만 다르다. 코드 변경 반영은 §A의 재빌드 → 세 Job 이미지 갱신으로 함께 처리된다. 아래는 각 잡의 수동 실행·확인이다.
```
# 수동 1회 실행
gcloud run jobs execute newsstore-prices --region=asia-northeast3 --wait
gcloud run jobs execute newsstore-factors --region=asia-northeast3 --wait
# 확인 (수집 수 / FMP·Yahoo 소스 / 상식범위 플래그)
gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="newsstore-prices"' \
  --freshness=10m --format="value(textPayload)"
```
- **비밀**: `FMP_API_KEY`는 Secret Manager `fmp-api-key`로 주입한다(생성은 `docs/setup.md §8`). 키를 재발급했으면 새 버전을 올리고 잡을 재실행한다:
  ```
  printf '%s' "<NEW_FMP_API_KEY>" | gcloud secrets versions add fmp-api-key --data-file=-
  ```
- **커버리지**: 대부분 심볼은 FMP 5분봉(`historical-chart/5min`), 국채(us2y/us10y/us30y)는 FMP treasury-rates에서 도출(5분봉이 없어 일봉 1바/일), kosdaq·dxy·wti 3종만 Yahoo 5분봉 폴백이다(FMP Premium 미커버). 심볼·소스 매핑 SSOT는 `config/prices.yaml`.
- **저장**: 5분봉 완전 스트림은 `price_bars`에 바 1개=문서 1개로 적재(새 바만 write), 웹 확인용 최신 스냅샷은 `prices/{key}`에 갱신한다. `price_bars`는 문서가 가장 빨리 늘어 TTL(§F)이 특히 중요하다.

## F. TTL 정책 (content 컬렉션 30일 만료)
모든 content 컬렉션(`items`·`prices`·`price_bars` + 팩터 계약 컬렉션)은 `expire_at`을 TTL 정책이 보고 만료시킨다(비용 통제 — `price_bars`는 바 날짜 + 30일, 나머지는 저장 시각 + 30일). **`feed_state`·`meta`엔 TTL을 걸지 않는다**(폴링 커서 만료 시 증분 수집 어긋남). 최초 프로비저닝은 `docs/setup.md §7`(전 컬렉션 루프). 현재 상태 확인:
```
gcloud firestore fields ttl list --collection-group=items
```

## G. 잡 실패 알림 (Cloud Monitoring)
**왜:** Cloud Scheduler는 잡을 `:run`으로 **시작**시키고 HTTP 200(=시작 수락)만 받는다. 잡이 시작 직후 죽어도 스케줄러는 초록(성공)으로 보여 **조용한 실패**가 된다(Fail-Loud 위반). → Cloud Run Job **실패 실행 수>0**이면 알림.

지표: `run.googleapis.com/job/completed_execution_count` (resource `cloud_run_job`, metric label `result="failed"`). 세 잡(collector·prices·factors) 공통 적용(job_name 필터 없이 전체).

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
- **가격 데이터 무결성**: 받은 숫자를 의심한다 — 가격·펀더멘털 doc에 `fetched_at`(신선도)을 남겨 스케줄러가 조용히 멈춰도 낡은 값을 실시간처럼 표시하지 않게 한다. %등락이 상식 밖이면 삭제하지 않고 `flags`에 표시(비파괴). 스냅샷의 값·등락은 라이브 시세가 아니라 5분봉 시계열에서 도출한다(각 봉의 종가는 그 봉 자체의 값이라 stale-라이브 오답이 없다).
- **피드 추가 전 curl 실측**(HTTP·item수·desc 유무) → 되는 것만 등록 → A 재배포.
- **콘솔 수동 대신 REST**로 GCP/Firebase 운영(인증 공유).
- 환경(`APP_ENV`=home/office, 저장소=Firestore 단일)은 `README.md` 표 참조.

## 알아둘 함정
- 수집기는 **Cloud Run 데이터센터 IP**라 일부 사이트가 차단함(fxstreet 제거됨, Bloomberg 기사본문 403). → 기사 본문 fetch는 **도달 실증된 화이트리스트만**(한경 OK; Investing/Bloomberg/FT 기사페이지 403). 화이트리스트 fetch가 IP를 막히게 하면 RSS 수집까지 영향이므로 **바운드(상한·타임아웃·스로틀)+배포 스모크**로 관리(본문 정책 §접근 방식).
- 피드 추가는 "되는지 curl 테스트 → feeds.yaml → A 재배포" 순서.
- 가격 결측은 정상 신호일 수 있다 — 일봉엔 주말·공휴일이 없고, KR과 US 휴장일이 다르다. 결측과 소스 파손을 혼동하지 않는다.
