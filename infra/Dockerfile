# infra/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# INSTALL_DEV=true(기본)면 pytest 포함(테스트 워크플로), prod 이미지는
#   docker build --build-arg INSTALL_DEV=false ... 로 [dev] 제외.
ARG INSTALL_DEV=true
# 클라우드(Cloud Run) 이미지는 INSTALL_DEV=false INSTALL_GCP=true 로 빌드 → google-cloud-firestore 포함.
ARG INSTALL_GCP=false

# 의존성 먼저 (캐시). requirements.lock을 constraints로 걸어 재현 가능 빌드.
COPY pyproject.toml ./
COPY infra/requirements.lock ./infra/requirements.lock
COPY src/ ./src/
RUN pip install --upgrade pip && \
    EXTRAS="" ; \
    if [ "$INSTALL_DEV" = "true" ]; then EXTRAS="dev" ; fi ; \
    if [ "$INSTALL_GCP" = "true" ]; then EXTRAS="${EXTRAS:+$EXTRAS,}gcp" ; fi ; \
    if [ -n "$EXTRAS" ]; then \
      pip install -e ".[$EXTRAS]" -c infra/requirements.lock ; \
    else \
      pip install -e . -c infra/requirements.lock ; \
    fi

# 소스
COPY . .

# APP_ENV=office(사내 ePrism)면 루트 CA 설치, home이면 파일이 없어 스킵 → 동일 이미지로 양쪽 빌드.
# (.crt 는 .gitignore/.dockerignore로 git 제외; office 로컬에는 파일이 존재해 COPY . . 로 포함됨)
RUN if [ -f ePrism-SSL-ROOT-CA.crt ]; then \
      cp ePrism-SSL-ROOT-CA.crt /usr/local/share/ca-certificates/ && update-ca-certificates ; \
    fi
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    PYTHONUNBUFFERED=1

CMD ["python", "-m", "newsstore.run", "--force"]
