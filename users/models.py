from django.contrib.auth.models import AbstractUser
from django.db import models
from django_otp.plugins.otp_totp.models import TOTPDevice

from markets.models import CryptoCurrency


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


class Wallet(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="wallet")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email}'s Wallet"


class WalletBalance(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="balances")
    currency = models.ForeignKey(CryptoCurrency, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=20, decimal_places=8, default=0)

    class Meta:
        unique_together = ("wallet", "currency")

    def __str__(self):
        return f"{self.wallet.user.email} - {self.currency.symbol}: {self.amount}"


class Transaction(models.Model):
    TRANSACTION_TYPE = [
        ("deposit", "Deposit"),
        ("withdraw", "Withdraw"),
    ]
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    currency = models.ForeignKey(CryptoCurrency, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    fee = models.DecimalField(max_digits=20, decimal_places=8)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.wallet.user.email} {self.transaction_type} {self.amount} {self.currency.symbol}"


class SuspiciousRequest(models.Model):
    ip_address = models.GenericIPAddressField()
    url = models.URLField()
    user_agent = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.ip_address} at {self.timestamp}"
