# stage를 나누어 빌드 환경과 실행 환경을 분리
# 빌드 환경에서는 빌드에 필요한 패키지를 설치하고, 실행 환경에서는 빌드 환경에서 생성된 파일만 복사하여 실행
FROM python:3.12-slim AS base

WORKDIR app

RUN apt-get update && apt-get install -y build-essential libpq-dev curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && rm -rf /root/.cache/pip

FROM base AS web

WORKDIR /app

COPY conf/ conf/
COPY markets/ markets/
COPY orders/ orders/
COPY tradehive/ tradehive/
COPY users/ users/
COPY ssl/web/web.crt web.crt
COPY ssl/web/web.key web.key
COPY entrypoint.sh entrypoint.sh
COPY manage.py manage.py
COPY private.pem private.pem
COPY public.pem public.pem

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ENTRYPOINT ["/app/entrypoint.sh"]
