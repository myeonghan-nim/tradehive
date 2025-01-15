from django.contrib.auth.models import AbstractUser
from django.db import models
from django_otp.plugins.otp_totp.models import TOTPDevice


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    mfa_enabled = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.username


class CustomUserTOTPDevice(TOTPDevice):
    pass

    def __str__(self):
        return f"{self.user.username} - {self.name}"
