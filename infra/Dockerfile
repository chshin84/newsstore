FROM python:3.12-slim

# ePrism SSL 프록시 인증서 설치 (사내망 전용)
COPY ePrism-SSL-ROOT-CA.crt /usr/local/share/ca-certificates/ePrism-SSL-ROOT-CA.crt
RUN update-ca-certificates

ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install -e ".[dev]"

COPY . .

CMD ["python", "-m", "src.run", "--slot", "am"]
