from rest_framework import serializers

from .models import Order
from markets.models import CryptoCurrency


class OrderSerializer(serializers.ModelSerializer):
    base_currency = serializers.CharField()
    quote_currency = serializers.CharField()

    class Meta:
        model = Order
        fields = ["id", "order_type", "base_currency", "quote_currency", "side", "price", "amount", "created_at", "status"]

    def validate(self, data):
        base_currency, quote_currency = data.get("base_currency"), data.get("quote_currency")
        if base_currency == quote_currency:
            raise serializers.ValidationError("Base currency and quote currency must be different.")

        if not CryptoCurrency.objects.filter(symbol=base_currency).exists():
            raise serializers.ValidationError(f"Base currency '{base_currency}' does not exist.")
        if not CryptoCurrency.objects.filter(symbol=quote_currency).exists():
            raise serializers.ValidationError(f"Quote currency '{quote_currency}' does not exist.")

        order_type = data.get("order_type")
        if order_type == "market" and data.get("price"):
            raise serializers.ValidationError("Market orders should not include a price.")
        if order_type == "limit" and not data.get("price"):
            raise serializers.ValidationError("Limit orders must include a price.")

        return data

    def create(self, validated_data):
        base_currency_symbol, quote_currency_symbol = validated_data.pop("base_currency"), validated_data.pop("quote_currency")
        base_currency, quote_currency = CryptoCurrency.objects.get(symbol=base_currency_symbol), CryptoCurrency.objects.get(symbol=quote_currency_symbol)
        return Order.objects.create(base_currency=base_currency, quote_currency=quote_currency, **validated_data)
