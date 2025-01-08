from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class SecureClient(APIClient):
    def get(self, *args, **kwargs):
        kwargs["secure"] = True
        return super().get(*args, **kwargs)

    def post(self, *args, **kwargs):
        kwargs["secure"] = True
        return super().post(*args, **kwargs)


class RegisterAPITestCase(APITestCase):
    def setUp(self):
        self.client = SecureClient()

        self.register_url = "/users/register/"

        self.user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!",
            "phone_number": "123-4567-8901",
        }

        self.invalid_email_data = {**self.user_data, "email": "invalidemail"}
        self.invalid_password_data = {**self.user_data, "password": "weak"}
        self.invalid_phone_number_data = {**self.user_data, "phone_number": "123-4567-890"}
        self.missmatch_password_data = {**self.user_data, "confirm_password": "MissmatchPassword123!"}

        self.exist_user_data = {
            "email": "exist_test@example.com",
            "username": "exist_testuser",
            "password": "exist_StrongPassword123!",
            "phone_number": "234-5678-9012",
        }
        User.objects.create_user(**self.exist_user_data)

    def test_register_user_success(self):
        response = self.client.post(self.register_url, self.user_data)
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

        self.user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "StrongPassword123!",
            "phone_number": "123-4567-8901",
        }
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

        self.user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "StrongPassword123!",
            "phone_number": "123-4567-8901",
        }
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

        self.user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "StrongPassword123!",
            "phone_number": "123-4567-8901",
        }
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
