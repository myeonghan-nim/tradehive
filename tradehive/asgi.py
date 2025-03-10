"""
ASGI config for tradehive project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

import orders.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tradehive.settings")

# websocket를 사용하기 위해 ProtocolTypeRouter를 사용
application = ProtocolTypeRouter(
    {
        # http는 기존의 get_asgi_application()을 사용
        "http": get_asgi_application(),
        # websocket은 URLRouter를 사용하여 orders.routing.websocket_urlpatterns를 사용
        "websocket": URLRouter(orders.routing.websocket_urlpatterns),
    }
)
