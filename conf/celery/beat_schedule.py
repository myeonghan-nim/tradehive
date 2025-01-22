from celery import Celery

app = Celery("tradehive")

app.conf.beat_schedule = {
    "run-matching-engine-every-second": {
        "task": "orders.tasks.run_matching_engine",
        "schedule": 1.0,
    },
}
