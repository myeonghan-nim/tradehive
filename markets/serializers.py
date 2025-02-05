from rest_framework import serializers

from .models import CryptoCurrency, TradingPair


class CryptoCurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = CryptoCurrency
        fields = "__all__"

    def validate(self, data):
        name, symbol = data.get("name"), data.get("symbol")
        if CryptoCurrency.objects.filter(name=name).exists():
            raise serializers.ValidationError({"name": f"{name} already exists."})
        if CryptoCurrency.objects.filter(symbol=symbol).exists():
            raise serializers.ValidationError({"symbol": f"{symbol} already exists."})
        return data


class TradingPairSerializer(serializers.ModelSerializer):
    base_asset = serializers.CharField()
    quote_asset = serializers.CharField()

    class Meta:
        model = TradingPair
        fields = "__all__"

    def validate(self, data):
        base_asset_symbol, quote_asset_symbol = data.get("base_asset"), data.get("quote_asset")
        if not CryptoCurrency.objects.filter(symbol=base_asset_symbol).exists():
            raise serializers.ValidationError({"base_asset": f"{base_asset_symbol} does not exist."})
        if not CryptoCurrency.objects.filter(symbol=quote_asset_symbol).exists():
            raise serializers.ValidationError({"quote_asset": f"{quote_asset_symbol} does not exist."})

        if not self.instance:
            if TradingPair.objects.filter(base_asset__symbol=base_asset_symbol, quote_asset__symbol=quote_asset_symbol).exists():
                raise serializers.ValidationError({"trading_pair": f"{base_asset_symbol}/{quote_asset_symbol} already exists."})

        min_price, max_price = data.get("min_price"), data.get("max_price")
        if min_price and max_price and min_price >= max_price:
            raise serializers.ValidationError({"min_price": "min_price must be less than max_price.", "max_price": "max_price must be greater than min_price."})

        min_quantity, max_quantity = data.get("min_quantity"), data.get("max_quantity")
        if min_quantity and max_quantity and min_quantity >= max_quantity:
            raise serializers.ValidationError({"min_quantity": "min_quantity must be less than max_quantity.", "max_quantity": "max_quantity must be greater than min_quantity."})

        return data

    def create(self, validated_data):
        base_asset_symbol, quote_asset_symbol = validated_data.pop("base_asset"), validated_data.pop("quote_asset")
        base_asset, quote_asset = CryptoCurrency.objects.get(symbol=base_asset_symbol), CryptoCurrency.objects.get(symbol=quote_asset_symbol)
        return TradingPair.objects.create(base_asset=base_asset, quote_asset=quote_asset, **validated_data)

    def update(self, instance, validated_data):
        base_asset_symbol, quote_asset_symbol = validated_data.pop("base_asset"), validated_data.pop("quote_asset")
        base_asset, quote_asset = CryptoCurrency.objects.get(symbol=base_asset_symbol), CryptoCurrency.objects.get(symbol=quote_asset_symbol)
        instance.base_asset, instance.quote_asset = base_asset, quote_asset
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
