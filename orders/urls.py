from django.urls import path

from .views import OrderView, ChartDataView

urlpatterns = [
    path("order/", OrderView.as_view(), name="order"),
    path("chart-data/", ChartDataView.as_view(), name="chart-data"),
]
