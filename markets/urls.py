from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CryptoCurrencyViewSet, TradingPairViewSet, ChartDataView

router = DefaultRouter()
router.register(r"crypto-currencies", CryptoCurrencyViewSet, basename="crypto-currencies")
router.register(r"trading-pairs", TradingPairViewSet, basename="trading-pairs")

urlpatterns = [
    path("chart-data/", ChartDataView.as_view(), name="chart-data"),
    path("", include(router.urls)),
]
