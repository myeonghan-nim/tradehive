FROM python:3.12-slim

WORKDIR /tradehive

RUN apt-get update && apt-get install -y build-essential libpq-dev curl

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
ENTRYPOINT ["/tradehive/entrypoint.sh"]
