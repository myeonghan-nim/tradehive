from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import TradingPair
from .serializers import TradingPairSerializer


class TradingPairViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = TradingPair.objects.all()
    serializer_class = TradingPairSerializer
