# celery는 django와 함께 사용할 수 있는 task queue
from __future__ import absolute_import, unicode_literals
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tradehive.settings")

app = Celery("tradehive")
app.config_from_object("django.conf:settings", namespace="CELERY")
# task 모듈을 모든 django app에서 찾도록 함
app.autodiscover_tasks()


# celery beat 설정
# on_after_finalize: celery가 초기화된 후 실행할 함수를 지정(connect: signal 연결)
# setup_periodic_tasks: celery beat가 초기화된 후 실행할 함수를 지정
@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    from django_celery_beat.models import PeriodicTask, IntervalSchedule

    # beat가 주기적으로 실행할 task의 주기를 설정하고 이를 db에 저장
    schedule, _ = IntervalSchedule.objects.get_or_create(every=1, period=IntervalSchedule.SECONDS)
    _, created = PeriodicTask.objects.get_or_create(interval=schedule, name="Run Match Orders Task", task="orders.tasks.run_matching_engine")

    print("Periodic task created." if created else "Periodic task already exists.")
