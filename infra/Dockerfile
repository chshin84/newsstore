# infra/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 의존성 먼저 (캐시)
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --upgrade pip && pip install -e ".[dev]"

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
