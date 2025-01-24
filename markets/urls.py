from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import TradingPairViewSet

router = DefaultRouter()
router.register(r"trading-pairs", TradingPairViewSet, basename="order")

urlpatterns = [
    path("", include(router.urls)),
]
