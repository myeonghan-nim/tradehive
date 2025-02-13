FROM python:3.12-slim

WORKDIR app

RUN apt-get update && apt-get install -y build-essential libpq-dev curl

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY conf/ conf/
COPY markets/ markets/
COPY orders/ orders/
COPY tradehive/ tradehive/
COPY users/ users/
COPY cert.crt cert.crt
COPY cert.key cert.key
COPY entrypoint.sh entrypoint.sh
COPY manage.py manage.py
COPY private.pem private.pem
COPY public.pem public.pem

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ENTRYPOINT ["/app/entrypoint.sh"]
