from __future__ import absolute_import, unicode_literals

from .celery.celery import app as celery_app
from .celery.beat_schedule import app as celery_beat_schedule

__all__ = (
    "celery_app",
    "celery_beat_schedule",
)
