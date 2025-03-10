from datetime import datetime

from rest_framework import viewsets, status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CryptoCurrency, TradingPair
from .serializers import CryptoCurrencySerializer, TradingPairSerializer
from .utils import get_candle_data, calculate_ma, calculate_bollinger_bands


# ModelViewSet은 Django의 View와 유사하며 Model을 기반으로 CRUD(Create, Read, Update, Delete) API를 자동으로 생성해준다.
# create: View에서 POST 요청을 받아 새로운 객체를 생성한다.
# retrieve: View에서 GET 요청을 받아 특정 객체를 조회한다.
# update: View에서 PUT 요청을 받아 특정 객체를 수정한다.
# partial_update: View에서 PATCH 요청을 받아 특정 객체를 수정한다.
# destroy: View에서 DELETE 요청을 받아 특정 객체를 삭제한다.
# list: View에서 GET 요청을 받아 모든 객체를 조회한다.
class CryptoCurrencyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    queryset = CryptoCurrency.objects.all()
    serializer_class = CryptoCurrencySerializer


class TradingPairViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    queryset = TradingPair.objects.all()
    serializer_class = TradingPairSerializer


class ChartDataView(APIView):
    permission_classes = [IsAuthenticated]
    valid_indicators = {"ma": calculate_ma, "bollinger_bands": calculate_bollinger_bands}

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

        result = {"symbol": symbol, "interval": interval, "start": start, "end": end, "candles": candle_data, "indicators": {}}

        indicators = request.query_params.get("indicators")
        if indicators:
            indicators_list = [indicator.strip().lower() for indicator in indicators.split(",") if indicator.strip()]
            for indicator in indicators_list:
                if indicator in self.valid_indicators:
                    result["indicators"][indicator] = self.valid_indicators[indicator](candle_data)
                else:
                    return Response({"error": f"Invalid indicator: {indicator}"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_200_OK)
