import base64

import pyotp
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUserTOTPDevice

USER_DATA = {
    "email": "test@example.com",
    "username": "testuser",
    "password": "StrongPassword123!",
    "phone_number": "123-4567-8901",
}
EXIST_USER_DATA = {
    "email": "exist_test@example.com",
    "username": "exist_testuser",
    "password": "exist_StrongPassword123!",
    "phone_number": "234-5678-9012",
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


class RegisterAPITestCase(APITestCase):
    def setUp(self):
        self.client = SecureClient()

        self.register_url = "/users/register/"

        self.user_data = USER_DATA

        self.invalid_email_data = {**self.user_data, "email": "invalidemail"}
        self.invalid_password_data = {**self.user_data, "password": "weak"}
        self.invalid_phone_number_data = {**self.user_data, "phone_number": "123-4567-890"}
        self.missmatch_password_data = {**self.user_data, "confirm_password": "MissmatchPassword123!"}

        self.exist_user_data = EXIST_USER_DATA
        User.objects.create_user(**self.exist_user_data)

    def test_register_user_success(self):
        user_data = {**self.user_data, "confirm_password": self.user_data["password"]}
        response = self.client.post(self.register_url, user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("refresh", response.data)
        self.assertIn("access", response.data)

    def test_register_user_invalid_email_format(self):
        response = self.client.post(self.register_url, self.invalid_email_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_user_invalid_phone_number(self):
        response = self.client.post(self.register_url, self.invalid_phone_number_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data)

    def test_register_user_invalid_password(self):
        response = self.client.post(self.register_url, self.invalid_password_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_register_user_password_mismatch(self):
        response = self.client.post(self.register_url, self.missmatch_password_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("confirm_password", response.data)

    def test_register_user_email_exists(self):
        response = self.client.post(self.register_url, self.exist_user_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)


class LoginAPITestCase(APITestCase):
    def setUp(self):
        self.client = SecureClient()

        self.login_url = "/users/login/"

        self.user_data = USER_DATA
        User.objects.create_user(**self.user_data)

    def test_login_user_success(self):
        login_data = {"email": self.user_data["email"], "password": self.user_data["password"]}
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("refresh", response.data)
        self.assertIn("access", response.data)

    def test_login_user_invalid_credentials(self):
        login_data = {"email": self.user_data["email"], "password": "WrongPassword!"}
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("error", response.data)


class LogoutAPITestCase(APITestCase):
    def setUp(self):
        self.client = SecureClient()

        self.logout_url = "/users/logout/"

        self.user_data = USER_DATA
        self.user = User.objects.create_user(**self.user_data)
        self.refresh = RefreshToken.for_user(self.user)

    def test_logout_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.refresh}")
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)

    def test_logout_invalid_token(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalidtoken")
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_no_token(self):
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RefreshAPITestCase(APITestCase):
    def setUp(self):
        self.client = SecureClient()

        self.refresh_url = "/users/refresh/"

        self.user_data = USER_DATA
        self.user = User.objects.create_user(**self.user_data)
        self.refresh = RefreshToken.for_user(self.user)

    def test_token_refresh_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.refresh}")
        response = self.client.post(self.refresh_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_token_refresh_invalid_token(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalidtoken")
        response = self.client.post(self.refresh_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class EnableMFAAPITestCase(APITestCase):
    def setUp(self):
        self.client = SecureClient()

        self.enable_mfa_url = "/users/enable-mfa/"

        self.user_data = USER_DATA
        self.user = User.objects.create_user(**self.user_data)

        response = self.client.post("/users/login/", {"email": self.user_data["email"], "password": self.user_data["password"]})
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_enable_mfa_success(self):
        response = self.client.post(self.enable_mfa_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_enable_mfa_already_enabled(self):
        CustomUserTOTPDevice.objects.create(user=self.user, name="Test Device")
        response = self.client.post(self.enable_mfa_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class QRCodeAPITestCase(APITestCase):
    def setUp(self):
        self.client = SecureClient()

        self.qr_code_url = "/users/qr-code/"

        self.user_data = USER_DATA
        self.user = User.objects.create_user(**self.user_data)

        response = self.client.post("/users/login/", {"email": self.user_data["email"], "password": self.user_data["password"]})
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        CustomUserTOTPDevice.objects.create(user=self.user, name="Test Device")

    def test_qr_code_success(self):
        response = self.client.get(self.qr_code_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("qr_code_url", response.data)

    def test_qr_code_mfa_not_enabled(self):
        CustomUserTOTPDevice.objects.all().delete()
        response = self.client.get(self.qr_code_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class VerifyOTPAPITestCase(APITestCase):
    def setUp(self):
        self.client = SecureClient()

        self.verify_otp_url = "/users/verify-otp/"

        self.user_data = USER_DATA
        self.user = User.objects.create_user(**self.user_data)

        response = self.client.post("/users/login/", {"email": self.user_data["email"], "password": self.user_data["password"]})
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        CustomUserTOTPDevice.objects.create(user=self.user, name="Test Device")

    def test_verify_otp_success(self):
        device = CustomUserTOTPDevice.objects.get(user=self.user)
        base32_key = base64.b32encode(device.bin_key).decode("utf-8")
        otp_code = pyotp.TOTP(base32_key).now()
        response = self.client.post(self.verify_otp_url, {"otp_code": otp_code})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_verify_otp_invalid_otp(self):
        response = self.client.post(self.verify_otp_url, {"otp_code": "123456"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_otp_mfa_not_enabled(self):
        CustomUserTOTPDevice.objects.all().delete()
        response = self.client.post(self.verify_otp_url, {"otp_code": "123456"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class DeleteMFAAPITestCase(APITestCase):
    def setUp(self):
        self.client = SecureClient()

        self.delete_mfa_url = "/users/delete-mfa/"

        self.user_data = USER_DATA
        self.user = User.objects.create_user(**self.user_data)

        response = self.client.post("/users/login/", {"email": self.user_data["email"], "password": self.user_data["password"]})
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        CustomUserTOTPDevice.objects.create(user=self.user, name="Test Device")

    def test_delete_mfa_success(self):
        response = self.client.delete(self.delete_mfa_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(CustomUserTOTPDevice.objects.filter(user=self.user).exists())
        self.assertFalse(self.user.mfa_enabled)

    def test_delete_mfa_no_device(self):
        CustomUserTOTPDevice.objects.all().delete()
        response = self.client.delete(self.delete_mfa_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserProfileAPITestCase(APITestCase):
    def setUp(self):
        self.client = SecureClient()

        self.profile_url = "/users/profile/"

        self.user_data = USER_DATA
        self.user = User.objects.create_user(**self.user_data)

        response = self.client.post("/users/login/", {"email": self.user_data["email"], "password": self.user_data["password"]})
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_get_profile(self):
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.user_data["email"])
        self.assertEqual(response.data["username"], self.user_data["username"])
        self.assertEqual(response.data["phone_number"], self.user_data["phone_number"])

    def test_update_profile(self):
        data = {
            "username": "newusername",
            "phone_number": "987-6543-2109",
        }
        response = self.client.patch(self.profile_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.user_data["email"])
        self.assertEqual(response.data["username"], data["username"])
        self.assertEqual(response.data["phone_number"], data["phone_number"])

    def test_update_with_invalid_phone(self):
        data = {
            "phone_number": "invalid_number",
        }
        response = self.client.patch(self.profile_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
