<#
사내(ePrism MITM 프록시) 환경 배포 — gcloud 우회.

문제: 사내 ePrism이 SSL을 가로채는데, 최신 gcloud의 urllib3 v2가 strict 모드로
      AKI(Authority Key Identifier) 부재를 거부 → 호스트 gcloud·Cloud Shell 모두 차단
      (certificate verify failed: Missing Authority Key Identifier). CA 추가로도 안 풀림.
해결: 옛 gcloud(402.0.0, httplib2 — strict 아님) 컨테이너 + ePrism CA를 시스템 신뢰저장소에
      심고 core/custom_ca_certs_file로 지정 → 통과(검증 2026-06-29). Cloud Run Jobs는
      이 버전에선 beta 트랙이라 `gcloud beta run jobs`.

사용:
  pwsh scripts/deploy-office.ps1 auth     # 1회: 브라우저 인증(자격증명은 docker volume에 저장)
  pwsh scripts/deploy-office.ps1 deploy   # 빌드 → newsstore-collect-all Job 이미지 갱신 → 그 Job 실행
  pwsh scripts/deploy-office.ps1 backfill-ttl [-DryRun]
      # 이미 저장된 문서의 expire_at을 현행 TTL 계약으로 재계산(멱등). 잡을 만들거나 갱신한 뒤 실행한다.
      # -DryRun은 쓰기 없이 규모만 보고한다. 배포된 이미지의 _TTL을 기준으로 도니 deploy를 먼저 하라.
#>
param([Parameter(Position=0)][ValidateSet("auth","deploy","backfill-ttl")][string]$cmd = "deploy",
      [switch]$DryRun)

$IMG    = "google/cloud-sdk:402.0.0-slim"
$VOL    = "gcloud-cfg"
$REPO   = (Resolve-Path "$PSScriptRoot\..").Path

# 프로젝트/리전은 .env(GOOGLE_CLOUD_PROJECT·GCP_REGION)에서 도출 — 하드코딩 이중 정의 금지(SSOT)
$envFile = Join-Path $REPO ".env"
if (-not (Test-Path $envFile)) { throw ".env 없음 — cp .env.example .env 후 값을 채워라" }
$envMap = @{}
foreach ($line in Get-Content $envFile) {
  if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') { $envMap[$Matches[1]] = $Matches[2].Trim() }
}
$PROJECT = $envMap["GOOGLE_CLOUD_PROJECT"]
$REGION  = $envMap["GCP_REGION"]
if (-not $PROJECT -or -not $REGION) { throw ".env에 GOOGLE_CLOUD_PROJECT·GCP_REGION이 필요하다" }
$PROC   = "$REGION-docker.pkg.dev/$PROJECT/newsstore/collector:latest"

# 컨테이너 진입 시 ePrism CA 신뢰 + gcloud CA 지정(모든 호출 공통)
$setup = "cp /work/ePrism-SSL-ROOT-CA.crt /usr/local/share/ca-certificates/eprism.crt && update-ca-certificates >/dev/null 2>&1 && gcloud config set core/custom_ca_certs_file /etc/ssl/certs/ca-certificates.crt >/dev/null && gcloud config set project $PROJECT >/dev/null"

if ($cmd -eq "auth") {
  docker run --rm -it -v "${VOL}:/root/.config/gcloud" -v "${REPO}:/work" $IMG bash -c "$setup && gcloud auth login --no-launch-browser"
}
elseif ($cmd -eq "backfill-ttl") {
  # 잡 이름·서비스계정은 기존 백필 잡(newsstore-backfill-embed)의 관례를 따른다.
  $JOB = "newsstore-backfill-ttl"
  $SA  = "newsstore-job@$PROJECT.iam.gserviceaccount.com"
  $jobArgs = "-m,newsstore.entrypoints.run_backfill_ttl"
  if ($DryRun) { $jobArgs = "$jobArgs,--dry-run" }
  # 십만 건대 전수 페이징이라 기본 600초로는 모자란다. 멱등이라 도중에 끊겨도 재실행이 이어받지만,
  # 한 번에 끝나는 편이 읽기 재과금이 없다. 재시도는 끄고 실패를 그대로 드러낸다(Fail-Loud).
  $common = "--image=$PROC --region=$REGION --service-account=$SA --task-timeout=21600 " +
            "--max-retries=0 --command=python --args=$jobArgs " +
            "--set-env-vars=GOOGLE_CLOUD_PROJECT=$PROJECT"
  # 있으면 갱신하고 없으면 만든다 — 여러 번 돌려도 같은 상태에 이른다(멱등).
  $run = "$setup && " +
    "if gcloud beta run jobs describe $JOB --region=$REGION >/dev/null 2>&1; then " +
    "  gcloud --quiet beta run jobs update $JOB $common; " +
    "else " +
    "  gcloud --quiet beta run jobs create $JOB $common; " +
    "fi && " +
    "gcloud --quiet beta run jobs execute $JOB --region=$REGION --wait"
  docker run --rm -v "${VOL}:/root/.config/gcloud" -v "${REPO}:/work" -w /work $IMG bash -c "$run"
}
else {
  $deploy = "$setup && " +
    "gcloud builds submit --config infra/cloudbuild.yaml --substitutions=_IMAGE=$PROC . && " +
    "gcloud --quiet beta run jobs update newsstore-collect-all --image=$PROC --region=$REGION && " +
    "gcloud --quiet beta run jobs execute newsstore-collect-all --region=$REGION --wait"
  docker run --rm -v "${VOL}:/root/.config/gcloud" -v "${REPO}:/work" -w /work $IMG bash -c "$deploy"
}
