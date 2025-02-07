#!/bin/bash
set -e

python manage.py makemigrations
python manage.py migrate

if [ "$1" = "worker" ]; then
    echo "Starting Celery worker..."
    celery -A conf.celery worker --loglevel=info
elif [ "$1" = "beat" ]; then
    echo "Starting Celery Beat..."
    celery -A conf.celery beat --loglevel=info --scheduler django_celery_beat.schedulers.DatabaseScheduler
else
    echo "Starting Django server..."
    python manage.py runserver_plus 0.0.0.0:8000 --cert-file cert.crt --key-file cert.key
fi
