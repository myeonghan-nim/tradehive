import base64

import pyotp
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from .models import Order
from .tasks import match_orders
from markets.models import CryptoCurrency
from users.models import CustomUserTOTPDevice

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
