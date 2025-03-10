from django.db import models


class CryptoCurrency(models.Model):
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=10)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # db_table은 DB에 생성되는 테이블 이름을 지정, 만약 이렇게 지정하지 않으면 앱이름_모델이름 형태로 테이블이 생성됨
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
        # unique_together는 두 개 이상의 필드를 조합하여 유니크한 제약조건을 걸 수 있음
        unique_together = ("base_asset", "quote_asset")
        db_table = "trading_pairs"

    def __str__(self):
        return f"{self.base_asset}/{self.quote_asset}"
