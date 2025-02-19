from django.db.models import Q
from rest_framework import serializers

from .models import Order, Trade
from markets.models import CryptoCurrency


# TODO: add fee calculation
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

        base_currency_instance = CryptoCurrency.objects.filter(symbol=base_currency).first()
        quote_currency_instance = CryptoCurrency.objects.filter(symbol=quote_currency).first()
        if not base_currency_instance:
            raise serializers.ValidationError(f"Base currency '{base_currency}' does not exist.")
        if not quote_currency_instance:
            raise serializers.ValidationError(f"Quote currency '{quote_currency}' does not exist.")

        order_type = data.get("order_type")
        if order_type not in dict(Order.ORDER_TYPE_CHOICES):
            raise serializers.ValidationError(f"Order type must be one of {Order.ORDER_TYPE_CHOICES}.")

        if order_type == "market" and data.get("price"):
            raise serializers.ValidationError("Market orders should not include a price.")
        if order_type == "limit" and not data.get("price"):
            raise serializers.ValidationError("Limit orders must include a price.")

        price = None
        if order_type == "market":
            last_trade = Trade.objects.filter(
                Q(buy_order__base_currency=base_currency_instance, buy_order__quote_currency=quote_currency_instance)
                & Q(sell_order__base_currency=base_currency_instance, sell_order__quote_currency=quote_currency_instance)
            ).last()
            if last_trade:
                price = last_trade.price
            else:
                price = 0  # TODO: set default price
        elif order_type == "limit":
            price = float(data.get("price"))

        if price is None or (order_type == "limit" and price <= 0):
            raise serializers.ValidationError("Price must be greater than zero.")

        side = data.get("side")
        if side not in dict(Order.SIDE_CHOICES):
            raise serializers.ValidationError(f"Side must be one of {Order.SIDE_CHOICES}.")

        amount = float(data.get("amount"))
        user = self.context.get("request").user
        wallet = user.wallet
        if side == "buy":
            wallet_balance = wallet.balances.filter(currency__symbol=quote_currency).first()
            required_quote = amount
            if order_type == "limit":
                required_quote *= price
            if not wallet_balance or wallet_balance.amount < required_quote:
                raise serializers.ValidationError("Not enough balance to buy.")
        elif side == "sell":
            wallet_balance = wallet.balances.filter(currency__symbol=base_currency).first()
            if not wallet_balance or wallet_balance.amount < amount:
                raise serializers.ValidationError("Not enough balance to sell.")

        return data

    def create(self, validated_data):
        base_currency_symbol, quote_currency_symbol = validated_data.pop("base_currency"), validated_data.pop("quote_currency")
        base_currency, quote_currency = CryptoCurrency.objects.get(symbol=base_currency_symbol), CryptoCurrency.objects.get(symbol=quote_currency_symbol)
        return Order.objects.create(base_currency=base_currency, quote_currency=quote_currency, **validated_data)
