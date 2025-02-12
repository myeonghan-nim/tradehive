import json
import base64
from datetime import datetime, timedelta

import pyotp
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

    def setUp(self):
        self.client = SecureClient()
        self.user = User.objects.create_user(**self.user_data)

    def authenticate_user(self):
        response = self.client.post(self.login_url, {"email": self.user_data["email"], "password": self.user_data["password"]})
        self.token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def create_mfa_device(self, name="Test Device"):
        return CustomUserTOTPDevice.objects.create(user=self.user, name=name)

    def generate_valid_otp(self, device):
        base32_key = base64.b32encode(device.bin_key).decode("utf-8")
        return pyotp.TOTP(base32_key).now()


class OrderAPITestCase(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.authenticate_user()

        CryptoCurrency.objects.create(symbol="KRW", name="Korean Won")
        CryptoCurrency.objects.create(symbol="BTC", name="Bitcoin")

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

    def test_order_buy_market_success(self):
        response = self.client.post("/orders/order/", {**self.valid_market_order_data, "side": "buy"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Order.objects.first().user, self.user)

    def test_order_buy_market_with_price(self):
        response = self.client.post("/orders/order/", {**self.invalid_market_order_data, "side": "buy"})
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

    def test_order_sell_market_success(self):
        response = self.client.post("/orders/order/", {**self.valid_market_order_data, "side": "sell"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Order.objects.first().user, self.user)

    def test_order_sell_market_with_price(self):
        response = self.client.post("/orders/order/", {**self.invalid_market_order_data, "side": "sell"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)


class TradeAPITestCase(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.authenticate_user()

        krw = CryptoCurrency.objects.create(symbol="KRW", name="Korean Won")
        btc = CryptoCurrency.objects.create(symbol="BTC", name="Bitcoin")

        self.buy_order = Order.objects.create(user=self.user, side="buy", order_type="limit", price="100.00", amount="1.5", base_currency=btc, quote_currency=krw)
        self.sell_order = Order.objects.create(user=self.user, side="sell", order_type="limit", price="100.00", amount="1.5", base_currency=btc, quote_currency=krw)

    def test_trade_match_success(self):
        match_orders()
        self.assertEqual(Order.objects.get(id=self.buy_order.id).status, "completed")
        self.assertEqual(Order.objects.get(id=self.sell_order.id).status, "completed")

    def test_trade_match_no_match(self):
        self.buy_order.price = "50.00"
        self.buy_order.save()

        match_orders()
        self.assertEqual(Order.objects.get(id=self.buy_order.id).status, "open")
        self.assertEqual(Order.objects.get(id=self.sell_order.id).status, "open")


class TradeConsumerTestCase(TestCase):
    def setUp(self):
        base = CryptoCurrency.objects.create(symbol="BTC", name="Bitcoin")
        quote = CryptoCurrency.objects.create(symbol="KRW", name="Korean Won")

        buyer = User.objects.create_user(**USER_DATA)
        seller = User.objects.create_user(**{**USER_DATA, "email": "anothertest@example.com", "username": "anothertestuser"})

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


class ChartDataAPIViewTestCase(BaseAPITestCase):
    chart_data_url = "/orders/chart-data/"

    def setUp(self):
        super().setUp()
        self.authenticate_user()

        btc = CryptoCurrency.objects.create(symbol="BTC", name="Bitcoin")
        krw = CryptoCurrency.objects.create(symbol="KRW", name="Korean Won")

        order = Order.objects.create(user=self.user, side="buy", order_type="market", amount="3", base_currency=btc, quote_currency=krw)

        now = datetime.now()
        Trade.objects.create(buy_order=order, sell_order=order, price="10000", amount="2", created_at=now)
        Trade.objects.create(buy_order=order, sell_order=order, price="11000", amount="1", created_at=now + timedelta(minutes=1))

        self.start = (datetime.now() - timedelta(days=1)).isoformat()
        self.end = (datetime.now() + timedelta(days=1)).isoformat()

    def test_chart_data_success(self):
        response = self.client.get(self.chart_data_url, {"symbol": "BTC/KRW", "start": self.start, "end": self.end})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

        for candle in data:
            self.assertIn("timestamp", candle)
            self.assertIn("open", candle)
            self.assertIn("high", candle)
            self.assertIn("low", candle)
            self.assertIn("close", candle)
            self.assertIn("volume", candle)

    def test_chart_data_missing_params(self):
        response = self.client.get(self.chart_data_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_chart_data_invalid_symbol(self):
        response = self.client.get(self.chart_data_url, {"symbol": "ETH/KRW", "start": self.start, "end": self.end})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_chart_data_invalid_date_format(self):
        start = datetime.now().strftime("%Y/%m/%d")
        end = (datetime.now() + timedelta(days=1)).strftime("%Y/%m/%d")
        response = self.client.get(self.chart_data_url, {"symbol": "BTC/KRW", "start": start, "end": end})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
