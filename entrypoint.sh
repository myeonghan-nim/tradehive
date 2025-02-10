#!/bin/bash
set -e

if [ "$1" = "worker" ]; then
    echo "Starting Celery worker..."
    celery -A conf.celery worker --loglevel=info
elif [ "$1" = "beat" ]; then
    echo "Starting Celery Beat..."
    celery -A conf.celery beat --loglevel=info --scheduler django_celery_beat.schedulers.DatabaseScheduler
else
    echo "Starting Django server..."

    python manage.py makemigrations
    python manage.py migrate

    gunicorn -c conf/gunicorn/config.py tradehive.wsgi:application
fi
