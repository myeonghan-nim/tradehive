from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CryptoCurrencyViewSet, TradingPairViewSet, ChartDataView

# DefaultRouter는 ViewSet을 사용하여 URL을 자동으로 생성하는 라우터, 일반적으로 URI 접미사를 사용하여 URL을 생성
router = DefaultRouter()
router.register(r"crypto-currencies", CryptoCurrencyViewSet, basename="crypto-currencies")
router.register(r"trading-pairs", TradingPairViewSet, basename="trading-pairs")

urlpatterns = [
    path("chart-data/", ChartDataView.as_view(), name="chart-data"),
    path("", include(router.urls)),
]
