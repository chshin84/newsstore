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
  pwsh scripts/deploy-office.ps1 deploy   # 빌드 → 두 Job 이미지 갱신 → enricher 실행
#>
param([Parameter(Position=0)][ValidateSet("auth","deploy")][string]$cmd = "deploy")

$IMG    = "google/cloud-sdk:402.0.0-slim"
$VOL    = "gcloud-cfg"
$REPO   = (Resolve-Path "$PSScriptRoot\..").Path
$PROC   = "asia-northeast3-docker.pkg.dev/daily-recap-498506/newsstore/processor:latest"
$REGION = "asia-northeast3"
$PROJECT= "daily-recap-498506"

# 컨테이너 진입 시 ePrism CA 신뢰 + gcloud CA 지정(모든 호출 공통)
$setup = "cp /work/ePrism-SSL-ROOT-CA.crt /usr/local/share/ca-certificates/eprism.crt && update-ca-certificates >/dev/null 2>&1 && gcloud config set core/custom_ca_certs_file /etc/ssl/certs/ca-certificates.crt >/dev/null && gcloud config set project $PROJECT >/dev/null"

if ($cmd -eq "auth") {
  docker run --rm -it -v "${VOL}:/root/.config/gcloud" -v "${REPO}:/work" $IMG bash -c "$setup && gcloud auth login --no-launch-browser"
}
else {
  $deploy = "$setup && " +
    "gcloud builds submit --config infra/cloudbuild.processor.yaml --substitutions=_IMAGE=$PROC . && " +
    "gcloud --quiet beta run jobs update newsstore-enricher  --image=$PROC --region=$REGION && " +
    "gcloud --quiet beta run jobs update newsstore-summarizer --image=$PROC --region=$REGION && " +
    "gcloud --quiet beta run jobs execute newsstore-enricher --region=$REGION --wait"
  docker run --rm -v "${VOL}:/root/.config/gcloud" -v "${REPO}:/work" -w /work $IMG bash -c "$deploy"
}
