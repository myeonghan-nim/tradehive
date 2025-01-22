from rest_framework import serializers

from .models import Order


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["id", "order_type", "side", "price", "amount", "created_at", "status"]

    def validate(self, data):
        if data["order_type"] == "market" and data.get("price"):
            raise serializers.ValidationError("Market orders should not include a price.")
        if data["order_type"] == "limit" and not data.get("price"):
            raise serializers.ValidationError("Limit orders must include a price.")
        return data
