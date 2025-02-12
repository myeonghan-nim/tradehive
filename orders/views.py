from datetime import datetime

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import OrderSerializer
from .utils import get_candle_data
from markets.models import CryptoCurrency


class OrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = OrderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChartDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        symbol = request.query_params.get("symbol")
        if not symbol:
            return Response({"error": "Missing required query parameters"}, status=status.HTTP_400_BAD_REQUEST)

        base, quote = symbol.split("/")
        if not CryptoCurrency.objects.filter(symbol=base).exists() or not CryptoCurrency.objects.filter(symbol=quote).exists():
            return Response({"error": "Invalid symbol"}, status=status.HTTP_400_BAD_REQUEST)

        start = request.query_params.get("start")
        end = request.query_params.get("end")
        if not start or not end:
            return Response({"error": "Missing required query parameters"}, status=status.HTTP_400_BAD_REQUEST)

        interval = request.query_params.get("interval", "1d")

        try:
            start = datetime.fromisoformat(start)
            end = datetime.fromisoformat(end)
        except ValueError:
            return Response({"error": "Invalid date format"}, status=status.HTTP_400_BAD_REQUEST)

        candle_data = get_candle_data(symbol, start, end, interval)

        return Response(candle_data)
