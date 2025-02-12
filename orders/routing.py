from django.urls import re_path

from .consumers import TradeConsumer

websocket_urlpatterns = [
    re_path(r"ws/orders/(?P<symbol>\w+)/$", TradeConsumer.as_asgi()),
]
