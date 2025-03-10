from celery import shared_task

from .services import match_orders


# shared_task는 celery가 해당 함수를 task로 인식
@shared_task
def run_matching_engine():
    match_orders()
