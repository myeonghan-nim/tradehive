from rest_framework import serializers

from .models import TradingPair


class TradingPairSerializer(serializers.ModelSerializer):
    class Meta:
        model = TradingPair
        fields = "__all__"

    def validate(self, data):
        min_price = data.get("min_price")
        max_price = data.get("max_price")
        if min_price and max_price and min_price >= max_price:
            raise serializers.ValidationError({"min_price": "min_price must be less than max_price.", "max_price": "max_price must be greater than min_price."})

        min_quantity = data.get("min_quantity")
        max_quantity = data.get("max_quantity")
        if min_quantity and max_quantity and min_quantity >= max_quantity:
            raise serializers.ValidationError({"min_quantity": "min_quantity must be less than max_quantity.", "max_quantity": "max_quantity must be greater than min_quantity."})

        return data
