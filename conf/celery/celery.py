from __future__ import absolute_import, unicode_literals
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tradehive.settings")

app = Celery("tradehive")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    from django_celery_beat.models import PeriodicTask, IntervalSchedule

    schedule, _ = IntervalSchedule.objects.get_or_create(
        every=10,
        period=IntervalSchedule.SECONDS,
    )

    task, created = PeriodicTask.objects.get_or_create(
        interval=schedule,
        name="Run Match Orders Task",
        task="orders.tasks.run_matching_engine",
    )

    if created:
        print("Periodic task created.")
    else:
        print("Periodic task already exists.")
