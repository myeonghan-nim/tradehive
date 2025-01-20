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


class RegisterAPITestCase(BaseAPITestCase):
    register_url = "/users/register/"
    register_data = {**USER_DATA, "confirm_password": USER_DATA["password"]}

    def test_register_user_success(self):
        User.objects.all().delete()

        response = self.client.post(self.register_url, self.register_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("refresh", response.data)
        self.assertIn("access", response.data)

    def test_register_user_invalid_email(self):
        response = self.client.post(self.register_url, {**self.register_data, "email": "invalid_email"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_user_invalid_phone_number(self):
        response = self.client.post(self.register_url, {**self.register_data, "phone_number": "invalid_number"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data)

    def test_register_user_invalid_password(self):
        response = self.client.post(self.register_url, {**self.register_data, "password": "weak"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_register_user_password_mismatch(self):
        response = self.client.post(self.register_url, {**self.register_data, "confirm_password": "weak"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("confirm_password", response.data)

    def test_register_user_exists(self):
        response = self.client.post(self.register_url, self.register_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginAPITestCase(BaseAPITestCase):
    login_url = "/users/login/"
    login_data = {"email": USER_DATA["email"], "password": USER_DATA["password"]}

    def test_login_user_success(self):
        response = self.client.post(self.login_url, self.login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("refresh", response.data)
        self.assertIn("access", response.data)

    def test_login_user_invalid_credentials(self):
        response = self.client.post(self.login_url, {**self.login_data, "password": "WrongPassword!"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("error", response.data)


class LogoutAPITestCase(BaseAPITestCase):
    logout_url = "/users/logout/"

    def test_logout_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.user)}")
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)

    def test_logout_invalid_token(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid_token")
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_no_token(self):
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RefreshAPITestCase(BaseAPITestCase):
    refresh_url = "/users/refresh/"

    def test_token_refresh_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.user)}")
        response = self.client.post(self.refresh_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_token_refresh_invalid_token(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid_token")
        response = self.client.post(self.refresh_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MFAAPITestCase(BaseAPITestCase):
    enable_mfa_url = "/users/enable-mfa/"
    delete_mfa_url = "/users/delete-mfa/"

    def setUp(self):
        super().setUp()
        self.authenticate_user()

    def test_enable_mfa_success(self):
        response = self.client.post(self.enable_mfa_url, {"name": "Test Device"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_enable_mfa_already_enabled(self):
        self.create_mfa_device()
        response = self.client.post(self.enable_mfa_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_mfa_success(self):
        self.create_mfa_device()
        response = self.client.delete(self.delete_mfa_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(CustomUserTOTPDevice.objects.filter(user=self.user).exists())
        self.assertFalse(self.user.mfa_enabled)

    def test_delete_mfa_no_device(self):
        response = self.client.delete(self.delete_mfa_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class QRCodeAPITestCase(BaseAPITestCase):
    qr_code_url = "/users/qr-code/"

    def setUp(self):
        super().setUp()
        self.authenticate_user()
        self.create_mfa_device()

    def test_qr_code_success(self):
        response = self.client.get(self.qr_code_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("qr_code_url", response.data)

    def test_qr_code_mfa_not_enabled(self):
        CustomUserTOTPDevice.objects.all().delete()
        response = self.client.get(self.qr_code_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class VerifyOTPAPITestCase(BaseAPITestCase):
    verify_otp_url = "/users/verify-otp/"

    def setUp(self):
        super().setUp()
        self.authenticate_user()
        self.device = self.create_mfa_device()

    def test_verify_otp_success(self):
        response = self.client.post(self.verify_otp_url, {"otp_code": self.generate_valid_otp(self.device)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_verify_otp_invalid_otp(self):
        response = self.client.post(self.verify_otp_url, {"otp_code": "123456"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_otp_mfa_not_enabled(self):
        CustomUserTOTPDevice.objects.all().delete()
        response = self.client.post(self.verify_otp_url, {"otp_code": "123456"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserProfileAPITestCase(BaseAPITestCase):
    profile_url = "/users/profile/"

    def setUp(self):
        super().setUp()
        self.authenticate_user()

    def test_get_profile_success(self):
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.user_data["email"])
        self.assertEqual(response.data["username"], self.user_data["username"])
        self.assertEqual(response.data["phone_number"], self.user_data["phone_number"])

    def test_get_profile_no_auth(self):
        self.client.credentials()
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_profile_success(self):
        response = self.client.patch(self.profile_url, {"username": "newusername", "phone_number": "987-6543-2109"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_profile_invalid_phone(self):
        response = self.client.patch(self.profile_url, {"phone_number": "invalid_number"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_profile_success(self):
        device = self.create_mfa_device()
        response = self.client.delete(self.profile_url, {"otp_code": self.generate_valid_otp(device)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(User.objects.filter(email=self.user_data["email"]).exists())

    def test_delete_profile_invalid_otp(self):
        self.create_mfa_device()
        response = self.client.delete(self.profile_url, {"otp_code": "123456"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ChangePasswordAPITestCase(BaseAPITestCase):
    change_password_url = "/users/change-password/"

    def setUp(self):
        super().setUp()
        self.authenticate_user()

    def test_change_password_success(self):
        responst = self.client.post(self.change_password_url, {"old_password": self.user_data["password"], "new_password": "NewStrongPassword123!"})
        self.assertEqual(responst.status_code, status.HTTP_200_OK)

    def test_change_password_invalid_old_password(self):
        responst = self.client.post(self.change_password_url, {"old_password": "InvalidPassword123!", "new_password": "NewStrongPassword123!"})
        self.assertEqual(responst.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_weak_password(self):
        responst = self.client.post(self.change_password_url, {"old_password": self.user_data["password"], "new_password": "weak"})
        self.assertEqual(responst.status_code, status.HTTP_400_BAD_REQUEST)
