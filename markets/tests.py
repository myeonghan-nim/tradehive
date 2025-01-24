import base64
import random

import pyotp
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from .models import TradingPair
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


class TradingPairAPITestCase(BaseAPITestCase):
    trading_pair_url = "/markets/trading-pairs/"

    def setUp(self):
        super().setUp()
        self.authenticate_user()

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
        self.trading_pair = TradingPair.objects.create(**self.trading_pair_data)

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
