from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CryptoCurrencyViewSet, TradingPairViewSet

router = DefaultRouter()
router.register(r"crypto-currencies", CryptoCurrencyViewSet, basename="crypto-currencies")
router.register(r"trading-pairs", TradingPairViewSet, basename="trading-pairs")

urlpatterns = [
    path("", include(router.urls)),
]
