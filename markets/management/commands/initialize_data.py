import random
from decimal import Decimal

from django.core.management.base import BaseCommand

from markets.models import CryptoCurrency
from orders.models import Order
from users.models import CustomUser, Wallet, WalletBalance


# BaseCommand는 Django에 의해 프로젝트 내 management/commands/ 디렉토리에서 이와 같이 정의된 파일들을 검색해 파일의 이름을 커맨드 이름으로 등록
# python manage.py my_command로 실행 시 Django의 management framework가 해당 파일의 Command 클래스를 찾아 인스턴스화한 후 handle() 메서드를 호출
class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting data initialization..."))

        users = self._create_users()
        cryptos = self._create_cryptocurrencies()

        self._create_wallets_and_balances(users, cryptos)
        self._create_orders(users, cryptos)

        self.stdout.write(self.style.SUCCESS("Data initialization complete!"))

    def _create_users(self):
        user_data = [
            {"email": "alice@example.com", "username": "alice", "password": "alicepassword"},
            {"email": "bob@example.com", "username": "bob", "password": "bobpassword"},
            {"email": "charlie@example.com", "username": "charlie", "password": "charliepassword"},
            # 더 많은 유저 데이터 추가 가능
        ]

        users = []
        for data in user_data:
            user_qs = CustomUser.objects.filter(email=data["email"])
            if user_qs.exists():
                user = user_qs.first()
            else:
                user = CustomUser.objects.create_user(email=data["email"], username=data["username"], password=data["password"])
            users.append(user)

        return users

    def _create_cryptocurrencies(self):
        crypto_data = [
            {"name": "Bitcoin", "symbol": "BTC"},
            {"name": "Ethereum", "symbol": "ETH"},
            {"name": "Ripple", "symbol": "XRP"},
            {"name": "Korean Won", "symbol": "KRW"},
            # 더 많은 암호화폐 데이터 추가 가능
        ]

        cryptos = []
        for data in crypto_data:
            crypto, _ = CryptoCurrency.objects.get_or_create(symbol=data["symbol"], defaults={"name": data["name"], "is_active": True})
            cryptos.append(crypto)
        return cryptos

    def _create_wallets_and_balances(self, users, cryptos):
        for user in users:
            if not hasattr(user, "wallet"):
                wallet = Wallet.objects.create(user=user)
            else:
                wallet = user.wallet

            for crypto in cryptos:
                if not wallet.balances.filter(currency=crypto).exists():
                    random_amount = Decimal(random.uniform(10000, 20000)).quantize(Decimal("0.00000001"))
                    WalletBalance.objects.create(wallet=wallet, currency=crypto, amount=random_amount)

    def _create_orders(self, users, cryptos):
        # KRW를 기준으로 암호화폐를 무작위로 매수/매도 주문 생성
        quote_currency = CryptoCurrency.objects.filter(symbol="KRW").first()
        if not quote_currency:
            return

        for user in users:
            user_wallet = user.wallet

            try:
                quote_balance = user_wallet.balances.get(currency=quote_currency).amount
            except WalletBalance.DoesNotExist:
                quote_balance = Decimal("0")

            for crypto in cryptos:
                if crypto == quote_currency:
                    continue

                try:
                    base_balance = user_wallet.balances.get(currency=crypto).amount
                except WalletBalance.DoesNotExist:
                    base_balance = Decimal("0")

                if base_balance > 0:
                    sell_price = Decimal(random.uniform(10000, 20000)).quantize(Decimal("0.00000001"))
                    min_sell_amt = Decimal("0.001")
                    if base_balance > min_sell_amt:
                        sell_amount = Decimal(random.uniform(float(min_sell_amt), float(base_balance))).quantize(Decimal("0.00000001"))
                        Order.objects.create(user=user, order_type="limit", base_currency=crypto, quote_currency=quote_currency, side="sell", price=sell_price, amount=sell_amount)

                if quote_balance > 0:
                    buy_price = Decimal(random.uniform(10000, 20000)).quantize(Decimal("0.00000001"))
                    max_buy_amt = quote_balance / buy_price
                    min_buy_amt = Decimal("0.001")
                    if max_buy_amt > min_buy_amt:
                        buy_amount = Decimal(random.uniform(float(min_buy_amt), float(max_buy_amt))).quantize(Decimal("0.00000001"))
                        Order.objects.create(user=user, order_type="limit", base_currency=crypto, quote_currency=quote_currency, side="buy", price=buy_price, amount=buy_amount)
