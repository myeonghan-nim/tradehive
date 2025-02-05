from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser

from .models import CryptoCurrency, TradingPair
from .serializers import CryptoCurrencySerializer, TradingPairSerializer


class CryptoCurrencyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    queryset = CryptoCurrency.objects.all()
    serializer_class = CryptoCurrencySerializer


class TradingPairViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    queryset = TradingPair.objects.all()
    serializer_class = TradingPairSerializer
