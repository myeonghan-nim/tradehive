import base64
import random
from datetime import datetime, timedelta

import pyotp
import redis
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from .models import CryptoCurrency, TradingPair
from orders.models import Order, Trade
from users.models import CustomUserTOTPDevice

# TODO: USER_DATA와 같이 다른 테스트에서도 중복으로 사용되는 데이터는 fixtures로 분리
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

    # classmethod: 클래스 메서드로 정의된 메서드는 클래스가 인스턴스화 되지 않아도 호출 가능
    # setUpClass: 테스트 케이스 클래스 전체에 대해 한 번만 실행되는 메서드
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # tearDown에서 redis rate limit을 초기화하기 위해 setUpClass에서 redis 인스턴스 생성
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
        # rate-limit 키를 가진 모든 데이터 삭제
        for key in self.r.scan_iter("rate-limit:*"):
            self.r.delete(key)


class CryptoCurrencyAPITestCase(BaseAPITestCase):
    crypto_currency_url = "/markets/crypto-currencies/"

    def setUp(self):
        super().setUp()
        # Django에서 사용자가 관리자 권한을 가지고 있는지는 is_staff 필드로 확인
        self.user.is_staff = True
        self.user.save()
        self.authenticate_user()

        self.crypto_currency_data = {"name": "Bitcoin", "symbol": "BTC"}
        self.crypto_currency = CryptoCurrency.objects.create(**self.crypto_currency_data)

        self.new_crypto_currency_data = {"name": "Ethereum", "symbol": "ETH"}

    def test_get_crypto_currencies_success(self):
        response = self.client.get(self.crypto_currency_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_crypto_currencies_unauthorized(self):
        # credentials() 메서드를 호출하여 인증 토큰을 제거
        self.client.credentials()
        response = self.client.get(self.crypto_currency_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_crypto_currency_success(self):
        response = self.client.get(f"{self.crypto_currency_url}{self.crypto_currency.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_crypto_currency_unauthorized(self):
        self.client.credentials()
        response = self.client.get(f"{self.crypto_currency_url}{self.crypto_currency.id}/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_crypto_currency_not_found(self):
        response = self.client.get(f"{self.crypto_currency_url}{random.randint(1000, 9999)}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_crypto_currency_success(self):
        response = self.client.post(self.crypto_currency_url, self.new_crypto_currency_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_crypto_currency_unauthorized(self):
        self.client.credentials()
        response = self.client.post(self.crypto_currency_url, self.new_crypto_currency_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_crypto_currency_success(self):
        response = self.client.patch(f"{self.crypto_currency_url}{self.crypto_currency.id}/", {"name": "Bitcoin Cash", "symbol": "BCH"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # refresh_from_db(): 데이터베이스에서 최신 데이터를 가져와서 모델 인스턴스를 업데이트
        # 해당 메서드는 다음 상황에서 유용
        # 1. 데이터베이스에서 직접 데이터를 변경한 경우
        # 2. 다른 사용자가 데이터를 변경한 경우
        self.crypto_currency.refresh_from_db()
        self.assertEqual(self.crypto_currency.name, "Bitcoin Cash")
        self.assertEqual(self.crypto_currency.symbol, "BCH")

    def test_update_crypto_currency_not_found(self):
        response = self.client.patch(f"{self.crypto_currency_url}{random.randint(1000, 9999)}/", {"name": "Bitcoin Cash", "symbol": "BCH"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_crypto_currency_unauthorized(self):
        self.client.credentials()
        response = self.client.patch(f"{self.crypto_currency_url}{self.crypto_currency.id}/", {"name": "Bitcoin Cash", "symbol": "BCH"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_crypto_currency_success(self):
        response = self.client.delete(f"{self.crypto_currency_url}{self.crypto_currency.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CryptoCurrency.objects.filter(id=self.crypto_currency.id).exists())

    def test_delete_crypto_currency_not_found(self):
        response = self.client.delete(f"{self.crypto_currency_url}{random.randint(1000, 9999)}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_crypto_currency_unauthorized(self):
        self.client.credentials()
        response = self.client.delete(f"{self.crypto_currency_url}{self.crypto_currency.id}/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TradingPairAPITestCase(BaseAPITestCase):
    trading_pair_url = "/markets/trading-pairs/"

    def setUp(self):
        super().setUp()
        self.user.is_staff = True
        self.user.save()
        self.authenticate_user()

        btc = CryptoCurrency.objects.create(name="Bitcoin", symbol="BTC")
        usdt = CryptoCurrency.objects.create(name="Tether", symbol="USDT")
        CryptoCurrency.objects.create(name="Ethereum", symbol="ETH")

        self.trading_pair_data = {
            "base_asset": "BTC",
            "quote_asset": "USDT",
            "min_price": "0.01",
            "max_price": "1000000.00",
            "tick_size": "0.01",
            "min_quantity": "0.001",
            "max_quantity": "100.0",
            "step_size": "0.001",
        }
        self.trading_pair = TradingPair.objects.create(**{**self.trading_pair_data, "base_asset": btc, "quote_asset": usdt})

        self.invalid_base_asset_data = {**self.trading_pair_data, "base_asset_symbol": "XRP"}
        self.invalid_quote_asset_data = {**self.trading_pair_data, "quote_asset_symbol": "XRP"}
        self.invalid_price_data = {**self.trading_pair_data, "min_price": "1000000.00", "max_price": "0.01"}
        self.invalid_quantity_data = {**self.trading_pair_data, "min_quantity": "100.0", "max_quantity": "0.001"}

        self.new_trading_pair_data = {
            "base_asset": "ETH",
            "quote_asset": "BTC",
            "min_price": "0.0001",
            "max_price": "100.00",
            "tick_size": "0.0001",
            "min_quantity": "0.01",
            "max_quantity": "50.0",
            "step_size": "0.01",
        }

    def test_get_trading_pairs_success(self):
        response = self.client.get(self.trading_pair_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_trading_pairs_unauthorized(self):
        self.client.credentials()
        response = self.client.get(self.trading_pair_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_trading_pair_success(self):
        response = self.client.get(f"{self.trading_pair_url}{self.trading_pair.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_trading_pair_unauthorized(self):
        self.client.credentials()
        response = self.client.get(f"{self.trading_pair_url}{self.trading_pair.id}/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_trading_pair_not_found(self):
        response = self.client.get(f"{self.trading_pair_url}{random.randint(1000, 9999)}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_trading_pair_success(self):
        response = self.client.post(self.trading_pair_url, self.new_trading_pair_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_trading_pair_invalid_base_asset(self):
        response = self.client.post(self.trading_pair_url, self.invalid_base_asset_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_trading_pair_invalid_quote_asset(self):
        response = self.client.post(self.trading_pair_url, self.invalid_quote_asset_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_trading_pair_invalid_price(self):
        response = self.client.post(self.trading_pair_url, {**self.new_trading_pair_data, "min_price": "100.00", "max_price": "0.0001"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_trading_pair_invalid_quantity(self):
        response = self.client.post(self.trading_pair_url, {**self.new_trading_pair_data, "min_quantity": "50.0", "max_quantity": "0.01"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_trading_pair_unauthorized(self):
        self.client.credentials()
        response = self.client.post(self.trading_pair_url, self.new_trading_pair_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_trading_pair_success(self):
        response = self.client.patch(f"{self.trading_pair_url}{self.trading_pair.id}/", {**self.trading_pair_data, "max_price": "2000000.00"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.trading_pair.refresh_from_db()
        self.assertEqual(str(self.trading_pair.max_price), "2000000.00000000")

    def test_update_trading_pair_not_found(self):
        response = self.client.patch(f"{self.trading_pair_url}{random.randint(1000, 9999)}/", {**self.trading_pair_data, "max_price": "2000000.00"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_trading_pair_invalid_price(self):
        response = self.client.patch(f"{self.trading_pair_url}{self.trading_pair.id}/", {**self.invalid_price_data})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_trading_pair_invalid_quantity(self):
        response = self.client.patch(f"{self.trading_pair_url}{self.trading_pair.id}/", {**self.invalid_quantity_data})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_trading_pair_unauthorized(self):
        self.client.credentials()
        response = self.client.patch(f"{self.trading_pair_url}{self.trading_pair.id}/", {**self.trading_pair_data, "max_price": "2000000.00"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_trading_pair_success(self):
        response = self.client.delete(f"{self.trading_pair_url}{self.trading_pair.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TradingPair.objects.filter(id=self.trading_pair.id).exists())

    def test_delete_trading_pair_not_found(self):
        response = self.client.delete(f"{self.trading_pair_url}{random.randint(1000, 9999)}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_trading_pair_unauthorized(self):
        self.client.credentials()
        response = self.client.delete(f"{self.trading_pair_url}{self.trading_pair.id}/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ChartDataAPIViewTestCase(BaseAPITestCase):
    chart_data_url = "/markets/chart-data/"

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

    def test_chart_data_success_no_indicators(self):
        response = self.client.get(self.chart_data_url, {"symbol": "BTC/KRW", "start": self.start, "end": self.end})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIsInstance(data, dict)

        self.assertIn("symbol", data)
        self.assertIn("interval", data)
        self.assertIn("start", data)
        self.assertIn("end", data)
        self.assertIn("candles", data)
        self.assertIn("indicators", data)

        candles = data["candles"]
        self.assertIsInstance(candles, list)
        self.assertGreater(len(candles), 0)
        for candle in candles:
            self.assertIn("timestamp", candle)
            self.assertIn("open", candle)
            self.assertIn("high", candle)
            self.assertIn("low", candle)
            self.assertIn("close", candle)
            self.assertIn("volume", candle)

        self.assertEqual(data["indicators"], {})

    def test_chart_data_success_valid_indicators(self):
        response = self.client.get(self.chart_data_url, {"symbol": "BTC/KRW", "start": self.start, "end": self.end, "interval": "1d", "indicators": "ma,bollinger_bands"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIsInstance(data, dict)
        self.assertIn("indicators", data)

        indicators = data["indicators"]
        self.assertIn("ma", indicators)
        self.assertIn("bollinger_bands", indicators)

        self.assertIsInstance(indicators["ma"], list)
        self.assertIsInstance(indicators["bollinger_bands"], dict)

        self.assertIn("upper_bands", indicators["bollinger_bands"])
        self.assertIn("middle_bands", indicators["bollinger_bands"])
        self.assertIn("lower_bands", indicators["bollinger_bands"])

    def test_chart_data_invalid_indicator(self):
        response = self.client.get(self.chart_data_url, {"symbol": "BTC/KRW", "start": self.start, "end": self.end, "indicators": "unknown_indicator"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = response.json()
        self.assertIn("error", data)
        self.assertIn("Invalid indicator", data["error"])

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
