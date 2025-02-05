from django.db import models


class CryptoCurrency(models.Model):
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=10)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cryptocurrencies"

    def __str__(self):
        return self.name


class TradingPair(models.Model):
    base_asset = models.ForeignKey(CryptoCurrency, on_delete=models.CASCADE, related_name="base_asset")
    quote_asset = models.ForeignKey(CryptoCurrency, on_delete=models.CASCADE, related_name="quote_asset")
    min_price = models.DecimalField(max_digits=20, decimal_places=8)
    max_price = models.DecimalField(max_digits=20, decimal_places=8)
    tick_size = models.DecimalField(max_digits=20, decimal_places=8)
    min_quantity = models.DecimalField(max_digits=20, decimal_places=8)
    max_quantity = models.DecimalField(max_digits=20, decimal_places=8)
    step_size = models.DecimalField(max_digits=20, decimal_places=8)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("base_asset", "quote_asset")
        db_table = "trading_pairs"

    def __str__(self):
        return f"{self.base_asset}/{self.quote_asset}"
