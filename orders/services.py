import logging

from django.db import transaction

from .models import Order, Trade

logger = logging.getLogger(__name__)


def match_orders():
    buy_orders = Order.objects.filter(order_type="limit", side="buy", status="open").order_by("-price", "created_at")
    sell_orders = Order.objects.filter(order_type="limit", side="sell", status="open").order_by("price", "created_at")

    if not buy_orders.exists() or not sell_orders.exists():
        logger.info("No orders available for matching.")
        return

    for buy_order in buy_orders:
        for sell_order in sell_orders:
            if buy_order.price >= sell_order.price:
                trade_amount = min(buy_order.amount, sell_order.amount)
                match_price = sell_order.price

                with transaction.atomic():
                    Trade.objects.create(buy_order=buy_order, sell_order=sell_order, price=match_price, amount=trade_amount)

                    buy_order.amount -= trade_amount
                    sell_order.amount -= trade_amount

                    if buy_order.amount == 0:
                        buy_order.status = "completed"
                    if sell_order.amount == 0:
                        sell_order.status = "completed"

                    buy_order.save()
                    sell_order.save()

                if buy_order.amount == 0:
                    break
