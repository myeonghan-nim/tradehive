from django.conf import settings
from django.db import models

from markets.models import CryptoCurrency


class Order(models.Model):
    ORDER_TYPE_CHOICES = [
        ("market", "Market"),
        ("limit", "Limit"),
    ]
    SIDE_CHOICES = [
        ("buy", "Buy"),
        ("sell", "Sell"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    order_type = models.CharField(max_length=10, choices=ORDER_TYPE_CHOICES)
    base_currency = models.ForeignKey(CryptoCurrency, on_delete=models.CASCADE, related_name="base_currency_orders")
    quote_currency = models.ForeignKey(CryptoCurrency, on_delete=models.CASCADE, related_name="quote_currency_orders")
    side = models.CharField(max_length=10, choices=SIDE_CHOICES)
    price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default="open")


class Trade(models.Model):
    buy_order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="buy_trades")
    sell_order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="sell_trades")
    price = models.DecimalField(max_digits=20, decimal_places=8)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    created_at = models.DateTimeField(auto_now_add=True)
