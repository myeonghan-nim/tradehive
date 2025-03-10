import logging

from django.db import transaction

from .models import Order, Trade
from users.models import WalletBalance

logger = logging.getLogger(__name__)


def match_orders():
    buy_orders = Order.objects.filter(order_type="limit", side="buy", status="open").order_by("-price", "created_at")
    sell_orders = Order.objects.filter(order_type="limit", side="sell", status="open").order_by("price", "created_at")

    if not buy_orders.exists() or not sell_orders.exists():
        logger.info("No orders available for matching.")
        return

    # TODO: market 주문 처리 로직 추가
    for buy_order in buy_orders:
        for sell_order in sell_orders:
            buy_order_trading_pair = f"{buy_order.base_currency.symbol}/{buy_order.quote_currency.symbol}"
            sell_order_trading_pair = f"{sell_order.base_currency.symbol}/{sell_order.quote_currency.symbol}"
            if buy_order_trading_pair == sell_order_trading_pair:
                if buy_order.price >= sell_order.price:
                    trade_amount = min(buy_order.amount, sell_order.amount)
                    match_price = sell_order.price

                    # atomic으로 처리하지 않으면 동시에 여러 거래가 발생할 때 문제가 발생할 수 있음
                    with transaction.atomic():
                        Trade.objects.create(buy_order=buy_order, sell_order=sell_order, price=match_price, amount=trade_amount)

                        buyer_wallet = buy_order.user.wallet
                        buyer_quote_balance = WalletBalance.objects.select_for_update().get(wallet=buyer_wallet, currency=buy_order.quote_currency)
                        buyer_base_balance = WalletBalance.objects.select_for_update().get(wallet=buyer_wallet, currency=buy_order.base_currency)

                        required_quote = trade_amount * match_price

                        buyer_quote_balance.amount -= required_quote
                        buyer_base_balance.amount += trade_amount

                        buyer_quote_balance.save()
                        buyer_base_balance.save()

                        seller_wallet = sell_order.user.wallet
                        seller_quote_balance = WalletBalance.objects.select_for_update().get(wallet=seller_wallet, currency=sell_order.quote_currency)
                        seller_base_balance = WalletBalance.objects.select_for_update().get(wallet=seller_wallet, currency=sell_order.base_currency)

                        seller_quote_balance.amount += required_quote
                        seller_base_balance.amount -= trade_amount

                        seller_quote_balance.save()
                        seller_base_balance.save()

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
