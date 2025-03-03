import base64

import pyotp
import redis
from django.conf import settings
from asgiref.sync import async_to_sync, sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from .models import Order, Trade
from .tasks import match_orders
from markets.models import CryptoCurrency
from users.models import CustomUserTOTPDevice
from tradehive.asgi import application

USER_DATA = {
    "email": "test@example.com",
    "username": "testuser",
    "password": "StrongPassword123!",
    "phone_number": "123-4567-8901",
}

User = get_user_model()


class SecureClient(APIClient):
    def get(self, *args, **kwargs):
        kwargs["secure"] = True
        return super().get(*args, **kwargs)

    def post(self, *args, **kwargs):
        kwargs["secure"] = True
        return super().post(*args, **kwargs)

    def patch(self, *args, **kwargs):
        kwargs["secure"] = True
        return super().patch(*args, **kwargs)

    def delete(self, *args, **kwargs):
        kwargs["secure"] = True
        return super().delete(*args, **kwargs)


class BaseAPITestCase(APITestCase):
    login_url = "/users/login/"
    user_data = USER_DATA

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.r = redis.StrictRedis.from_url(settings.CACHES["default"]["LOCATION"])

    def setUp(self):
        self.client = SecureClient()
        self.user = User.objects.create_user(**self.user_data)

    def tearDown(self):
        self.flush_redis_rate_limit()
        return super().tearDown()

    def authenticate_user(self):
        response = self.client.post(self.login_url, {"email": self.user_data["email"], "password": self.user_data["password"]})
        self.token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        self.flush_redis_rate_limit()

    def create_mfa_device(self, name="Test Device"):
        return CustomUserTOTPDevice.objects.create(user=self.user, name=name)

    def generate_valid_otp(self, device):
        base32_key = base64.b32encode(device.bin_key).decode("utf-8")
        return pyotp.TOTP(base32_key).now()

    def flush_redis_rate_limit(self):
        for key in self.r.scan_iter("rate-limit:*"):
            self.r.delete(key)


class OrderAPITestCase(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.authenticate_user()

        self.krw = CryptoCurrency.objects.create(symbol="KRW", name="Korean Won")
        self.btc = CryptoCurrency.objects.create(symbol="BTC", name="Bitcoin")

        self.user.wallet.balances.create(currency=self.krw, amount=100000)
        self.user.wallet.balances.create(currency=self.btc, amount=10)

        self.valid_limit_order_data = {"order_type": "limit", "price": "100.00", "amount": "1.5", "base_currency": "BTC", "quote_currency": "KRW"}
        self.valid_market_order_data = {"order_type": "market", "amount": "1.5", "base_currency": "BTC", "quote_currency": "KRW"}

        self.invalid_limit_order_data = {**self.valid_market_order_data, "order_type": "limit"}
        self.invalid_market_order_data = {**self.valid_limit_order_data, "order_type": "market"}

    def test_order_buy_limit_success(self):
        response = self.client.post("/orders/order/", {**self.valid_limit_order_data, "side": "buy"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Order.objects.first().user, self.user)

    def test_order_buy_limit_missing_price(self):
        response = self.client.post("/orders/order/", {**self.invalid_limit_order_data, "side": "buy"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)

    def test_order_buy_limit_insufficient_balance(self):
        krw_balance = self.user.wallet.balances.get(currency=self.krw)
        krw_balance.amount = 0
        krw_balance.save()

        response = self.client.post("/orders/order/", {**self.valid_limit_order_data, "side": "buy"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)

    def test_order_buy_market_success(self):
        response = self.client.post("/orders/order/", {**self.valid_market_order_data, "side": "buy"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Order.objects.first().user, self.user)

    def test_order_buy_market_with_price(self):
        response = self.client.post("/orders/order/", {**self.invalid_market_order_data, "side": "buy"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)

    def test_order_buy_market_insufficient_balance(self):
        krw_balance = self.user.wallet.balances.get(currency=self.krw)
        krw_balance.amount = 0
        krw_balance.save()

        response = self.client.post("/orders/order/", {**self.valid_market_order_data, "side": "buy"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)

    def test_order_sell_limit_success(self):
        response = self.client.post("/orders/order/", {**self.valid_limit_order_data, "side": "sell"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Order.objects.first().user, self.user)

    def test_order_sell_limit_missing_price(self):
        response = self.client.post("/orders/order/", {**self.invalid_limit_order_data, "side": "sell"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)

    def test_order_sell_limit_insufficient_balance(self):
        btc_balance = self.user.wallet.balances.get(currency=self.btc)
        btc_balance.amount = 0
        btc_balance.save()

        response = self.client.post("/orders/order/", {**self.valid_limit_order_data, "side": "sell"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)

    def test_order_sell_market_success(self):
        response = self.client.post("/orders/order/", {**self.valid_market_order_data, "side": "sell"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Order.objects.first().user, self.user)

    def test_order_sell_market_with_price(self):
        response = self.client.post("/orders/order/", {**self.invalid_market_order_data, "side": "sell"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)

    def test_order_sell_market_insufficient_balance(self):
        btc_balance = self.user.wallet.balances.get(currency=self.btc)
        btc_balance.amount = 0
        btc_balance.save()

        response = self.client.post("/orders/order/", {**self.valid_market_order_data, "side": "sell"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)


class TradeAPITestCase(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.authenticate_user()

        krw = CryptoCurrency.objects.create(symbol="KRW", name="Korean Won")
        btc = CryptoCurrency.objects.create(symbol="BTC", name="Bitcoin")

        self.base_krw_amount = 100000
        self.base_btc_amount = 10

        self.price = 100
        self.amount = 1.5

        self.buyer = self.user
        self.buyer.wallet.balances.create(currency=krw, amount=self.base_krw_amount)
        self.buyer.wallet.balances.create(currency=btc, amount=self.base_btc_amount)

        self.seller = User.objects.create_user(**{**USER_DATA, "email": "anothertest@example.com", "username": "anothertestuser"})
        self.seller.wallet.balances.create(currency=krw, amount=self.base_krw_amount)
        self.seller.wallet.balances.create(currency=btc, amount=self.base_btc_amount)

        self.buy_order = Order.objects.create(user=self.buyer, side="buy", order_type="limit", price=self.price, amount=self.amount, base_currency=btc, quote_currency=krw)
        self.sell_order = Order.objects.create(user=self.seller, side="sell", order_type="limit", price=self.price, amount=self.amount, base_currency=btc, quote_currency=krw)

    def test_trade_match_success(self):
        match_orders()
        self.assertEqual(Order.objects.get(id=self.buy_order.id).status, "completed")
        self.assertEqual(Order.objects.get(id=self.sell_order.id).status, "completed")
        self.assertEqual(float(self.buyer.wallet.balances.get(currency__symbol="KRW").amount), self.base_krw_amount - self.price * self.amount)
        self.assertEqual(float(self.buyer.wallet.balances.get(currency__symbol="BTC").amount), self.base_btc_amount + self.amount)
        self.assertEqual(float(self.seller.wallet.balances.get(currency__symbol="KRW").amount), self.base_krw_amount + self.price * self.amount)
        self.assertEqual(float(self.seller.wallet.balances.get(currency__symbol="BTC").amount), self.base_btc_amount - self.amount)

    def test_trade_match_no_match(self):
        self.buy_order.price = "50.00"
        self.buy_order.save()

        match_orders()
        self.assertEqual(Order.objects.get(id=self.buy_order.id).status, "open")
        self.assertEqual(Order.objects.get(id=self.sell_order.id).status, "open")
        self.assertEqual(self.user.wallet.balances.get(currency__symbol="KRW").amount, 100000)
        self.assertEqual(self.user.wallet.balances.get(currency__symbol="BTC").amount, 10)


class TradeConsumerTestCase(TestCase):
    def setUp(self):
        base = CryptoCurrency.objects.create(symbol="BTC", name="Bitcoin")
        quote = CryptoCurrency.objects.create(symbol="KRW", name="Korean Won")

        buyer = User.objects.create_user(**USER_DATA)
        seller = User.objects.create_user(**{**USER_DATA, "email": "anothertest@example.com", "username": "anothertestuser"})

        buyer.wallet.balances.create(currency=quote, amount=1000)
        seller.wallet.balances.create(currency=base, amount=1)

        order_type = "limit"
        self.price = "10000"
        self.amount = "1.5"

        self.buy_order = Order.objects.create(user=buyer, side="buy", order_type=order_type, price=self.price, amount=self.amount, base_currency=base, quote_currency=quote)
        self.sell_order = Order.objects.create(user=seller, side="sell", order_type=order_type, price=self.price, amount=self.amount, base_currency=base, quote_currency=quote)

    def test_trade_consumer(self):
        async def scenario():
            communicator = WebsocketCommunicator(application, "/ws/orders/BTCKRW/")
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            await sync_to_async(Trade.objects.create)(buy_order=self.buy_order, sell_order=self.sell_order, price=self.price, amount=self.amount)

            response = await communicator.receive_json_from()

            self.assertEqual(response["price"], self.price)
            self.assertEqual(response["amount"], self.amount)

            await communicator.disconnect()

        async_to_sync(scenario)()
