import json
import statistics
from datetime import datetime

from django.db.models import Min, Max, Sum
from django.db.models.functions import TruncMinute, TruncHour, TruncDay
from django_redis import get_redis_connection

from orders.models import Trade


def get_candle_data(symbol: str, start: datetime, end: datetime, interval: str):
    redis_conn = get_redis_connection("default")
    cache_key = f"candles:{symbol}:{interval}:{start.isoformat()}:{end.isoformat()}"
    cached_data = redis_conn.get(cache_key)
    if cached_data:
        return json.loads(cached_data)

    base, quote = symbol.split("/")
    queryset = Trade.objects.filter(
        buy_order__base_currency__symbol=base,
        buy_order__quote_currency__symbol=quote,
        created_at__gte=start,
        created_at__lt=end,
    )

    if interval == "1m":
        grouped_qs = queryset.annotate(time_group=TruncMinute("created_at"))
    elif interval == "1h":
        grouped_qs = queryset.annotate(time_group=TruncHour("created_at"))
    elif interval == "1d":
        grouped_qs = queryset.annotate(time_group=TruncDay("created_at"))
    else:
        grouped_qs = queryset.annotate(time_group=TruncMinute("created_at"))

    aggregated = (
        grouped_qs.values("time_group")
        .annotate(
            open_price=Min("price"),
            high_price=Max("price"),
            low_price=Min("price"),
            close_price=Max("price"),
            volume=Sum("amount"),
        )
        .order_by("time_group")
    )

    candle_list = []
    for item in aggregated:
        candle_list.append(
            {
                "timestamp": item["time_group"].isoformat(),
                "open": str(item["open_price"]),
                "high": str(item["high_price"]),
                "low": str(item["low_price"]),
                "close": str(item["close_price"]),
                "volume": str(item["volume"]),
            }
        )

    redis_conn.set(cache_key, json.dumps(candle_list), ex=60)

    return candle_list


def calculate_ma(candle_list, window_size=20):
    mas = []
    for i in range(len(candle_list)):
        if i < window_size - 1:
            mas.append(None)
            continue
        window = candle_list[i - window_size + 1 : i + 1]
        closes = [float(candle["close"]) for candle in window]
        ma = sum(closes) / window_size
        mas.append(ma)
    return mas


def calculate_bollinger_bands(candle_list, window_size=20, std=2):
    mas = calculate_ma(candle_list, window_size)
    upper_bands, lower_bands = [], []
    for i in range(len(candle_list)):
        if i < window_size - 1:
            upper_bands.append(None)
            lower_bands.append(None)
            continue
        window = candle_list[i - window_size + 1 : i + 1]
        closes = [float(c["close"]) for c in window]
        pstdev = statistics.pstdev(closes)
        mb = mas[i]
        ub, lb = mb + std * pstdev, mb - std * pstdev
        upper_bands.append(ub)
        lower_bands.append(lb)
    return {"upper_bands": upper_bands, "middle_bands": mas, "lower_bands": lower_bands}
