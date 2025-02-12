from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Trade


@receiver(post_save, sender=Trade)
def send_trade_to_websocket(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        symbol = f"{instance.buy_order.base_currency.symbol}{instance.buy_order.quote_currency.symbol}"
        group_name = f"orders_{symbol}"

        trade_data = {
            "price": str(instance.price),
            "amount": str(instance.amount),
            "timestamp": instance.created_at.isoformat(),
        }
        async_to_sync(channel_layer.group_send)(group_name, {"type": "send_trade_data", "data": trade_data})
