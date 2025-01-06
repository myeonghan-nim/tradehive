import time

from django.contrib.auth import get_user_model
from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse

from .models import CustomUser


class HTTPSTest(TestCase):
    def test_https(self):
        response = self.client.get(reverse("login"), secure=False)
        self.assertEqual(response.status_code, 301)
        self.assertTrue(response.url.startswith("https://"))


class SecureClient(Client):
    def get(self, *args, **kwargs):
        kwargs["secure"] = True
        return super().get(*args, **kwargs)

    def post(self, *args, **kwargs):
        kwargs["secure"] = True
        return super().post(*args, **kwargs)


class SignUpTest(TestCase):
    def setUp(self):
        self.client = SecureClient()

    def test_signup_view(self):
        response = self.client.get(reverse("signup"))
        self.assertEqual(response.status_code, 200)

    def test_signup_form(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "testuser",
                "email": "test@example.com",
                "phone_number": "1234567890",
                "password": "testpassword",
                "confirm_password": "testpassword",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CustomUser.objects.filter(username="testuser").exists())


class LoginTest(TestCase):
    def setUp(self):
        self.client = SecureClient()
        self.user = CustomUser.objects.create_user(username="testuser", password="testpassword")

    def test_login_view(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)

    def test_login_form(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "testuser",
                "password": "testpassword",
            },
        )
        self.assertEqual(response.status_code, 302)


class AutoLogoutTest(TestCase):
    def setUp(self):
        self.client = SecureClient()
        self.user = get_user_model().objects.create_user(username="testuser", password="testpassword")

    def test_auto_logout(self):
        self.client.login(username="testuser", password="testpassword")
        self.client.get(reverse("profile"))
        time.sleep(settings.SESSION_SECURITY_EXPIRE_AFTER)
        response = self.client.get(reverse("profile"))
        expected_redirect_url = f"{reverse('login')}?next={reverse('profile')}"
        self.assertRedirects(response, expected_redirect_url)
