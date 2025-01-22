from celery import shared_task

from .services import match_orders


@shared_task
def run_matching_engine():
    match_orders()
