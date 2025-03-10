from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email, RegexValidator
from django.core.exceptions import ValidationError
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUserTOTPDevice, Transaction, WalletBalance
from markets.models import CryptoCurrency

PHONE_NUMBER_VALIDATOR = RegexValidator(regex=r"^\d{3}-\d{4}-\d{4}$", message="Phone number must be in the format xxx-xxxx-xxxx.")

User = get_user_model()


def validate_authorization_header(request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise serializers.ValidationError("Refresh token not provided in Authorization header.")
    return auth_header.split(" ")[1]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)
    phone_number = serializers.CharField(validators=[PHONE_NUMBER_VALIDATOR], required=False)

    class Meta:
        model = User
        fields = ("email", "username", "password", "confirm_password", "phone_number")

    def validate(self, data):
        if User.objects.filter(email=data["email"]).exists():
            raise serializers.ValidationError({"email": "A user with this email already exists."})

        try:
            validate_email(data["email"])
        except ValidationError:
            raise serializers.ValidationError({"email": "Invalid email format."})

        try:
            validate_password(data["password"])
        except ValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})

        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        return data

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class LogoutSerializer(serializers.Serializer):
    def validate(self, data):
        request = self.context.get("request")
        refresh_token = validate_authorization_header(request)
        # refresh token을 사용하여 로그아웃을 진행해야 함, refresh token을 사용하는 이유는 access token이 만료되었을 때 refresh token을 사용하여 새로운 access token을 발급받기 때문
        # refresh token을 사용하여 로그아웃을 진행하면 해당 refresh token을 blacklist에 추가하여 해당 refresh token을 사용하여 새로운 access token을 발급받을 수 없도록 함
        # access token: 사용자 인증에 사용되며 일반적으로 짧은 유효기간을 가짐
        # refresh token: access token을 재발급 받기 위한 토큰으로 보통 더 긴 유효기간을 가짐
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception as e:
            raise serializers.ValidationError(f"Invalid token: {str(e)}")
        return data


class CustomTokenRefreshSerializer(serializers.Serializer):
    def validate(self, data):
        request = self.context.get("request")
        refresh_token = validate_authorization_header(request)
        try:
            refresh = RefreshToken(refresh_token)
        except Exception:
            raise serializers.ValidationError("Invalid refresh token.")

        data = {"access": str(refresh.access_token)}
        # ROTATE_REFRESH_TOKENS가 True일 경우 재발급 받은 refresh token을 반환
        if settings.SIMPLE_JWT["ROTATE_REFRESH_TOKENS"]:  # TODO: True일 때만 refresh token 갱신
            data["refresh"] = str(refresh)

        return data


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def validate(self, data):
        if not self.user:
            raise serializers.ValidationError("User not found.")

        if not self.user.check_password(data.get("old_password")):
            raise serializers.ValidationError("Old password is incorrect.")

        try:
            validate_password(data.get("new_password"), user=self.user)
        except ValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})

        return data

    def save(self):
        self.user.set_password(self.validated_data.get("new_password"))
        self.user.save()


class EnableMFASerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUserTOTPDevice
        fields = ("name",)

    def validate(self, data):
        user = self.context.get("request").user
        if not User.objects.filter(id=user.id).exists():
            raise serializers.ValidationError("User does not exist.")

        if CustomUserTOTPDevice.objects.filter(user=user).exists():
            raise serializers.ValidationError("MFA is already enabled for this user.")

        CustomUserTOTPDevice.objects.create(user=user, name=data.get("name"))
        user.mfa_enabled = True
        user.save()

        return data


class DeleteMFASerializer(serializers.Serializer):
    def validate(self, data):
        user = self.context.get("request").user
        device = CustomUserTOTPDevice.objects.filter(user=user).first()
        if not device:
            raise serializers.ValidationError("MFA is not enabled for this user.")

        device.delete()
        user.mfa_enabled = False
        user.save()

        return data


class QRCodeSerializer(serializers.Serializer):
    qr_code_url = serializers.SerializerMethodField()

    class Meta:
        model = CustomUserTOTPDevice
        fields = ("qr_code_url",)

    def get_qr_code_url(self, obj):
        return obj.config_url

    def validate(self, data):
        user = self.context.get("request").user
        device = CustomUserTOTPDevice.objects.filter(user=user).first()
        if not device:
            raise serializers.ValidationError("No MFA device found.")

        data["device"] = device
        return data


class VerifyOTPSerializer(serializers.Serializer):
    otp_code = serializers.CharField(max_length=6, write_only=True)

    def validate(self, data):
        user = self.context.get("request").user
        device = CustomUserTOTPDevice.objects.filter(user=user).first()
        if not device:
            raise serializers.ValidationError("MFA is not enabled for this user.")

        otp_code = data.get("otp_code")
        if not device.verify_token(otp_code):
            raise serializers.ValidationError("Invalid OTP.")

        return data


class UserProfileSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(validators=[PHONE_NUMBER_VALIDATOR], required=False)

    class Meta:
        model = User
        fields = ("email", "username", "phone_number")
        read_only_fields = ("email",)


class UserProfileDeleteSerialzier(serializers.Serializer):
    otp_code = serializers.CharField(write_only=True, max_length=6)

    def validate(self, data):
        user = self.context.get("request").user
        try:
            totp_device = CustomUserTOTPDevice.objects.get(user=user)
        except CustomUserTOTPDevice.DoesNotExist:
            raise serializers.ValidationError("MFA is not enabled for this user.")

        if not totp_device.verify_token(data.get("otp_code")):
            raise serializers.ValidationError("Invalid OTP.")

        return data


class TransactionSerializer(serializers.ModelSerializer):
    MIN_FEE = Decimal("0.0001")  # 0.01%

    currency = serializers.SlugRelatedField(slug_field="symbol", queryset=CryptoCurrency.objects.all())
    fee = serializers.DecimalField(read_only=True, max_digits=20, decimal_places=8, default=MIN_FEE)

    class Meta:
        model = Transaction
        fields = ["id", "transaction_type", "currency", "amount", "fee", "created_at"]

    def validate(self, data):
        transaction_type = data.get("transaction_type")
        if transaction_type not in dict(Transaction.TRANSACTION_TYPE):
            raise serializers.ValidationError("Invalid transaction type.")

        amount = data.get("amount", Decimal("0"))
        fee_input = data.get("fee", self.MIN_FEE)  # TODO: 가상화폐에 따라 fee 차별화
        if fee_input < self.MIN_FEE:
            fee_input = self.MIN_FEE
        data["fee"] = fee_input

        currency = data.get("currency")
        wallet = self.context.get("request").user.wallet
        wallet_balance = wallet.balances.filter(currency=currency).first()
        if transaction_type == "withdraw":
            if not wallet_balance or wallet_balance.amount < (amount * (1 + fee_input)):
                raise serializers.ValidationError("Not enough balance to withdraw.")

        return data

    def create(self, validated_data):
        wallet = self.context.get("request").user.wallet
        transaction_type = validated_data["transaction_type"]
        amount = validated_data["amount"]
        fee = validated_data["fee"]

        currency = validated_data["currency"]
        wallet_balance = wallet.balances.get_or_create(currency=currency)[0]
        # admin_wallet_balance = User.objects.get(is_superuser=True).wallet.balances.get_or_create(currency=currency_instance)[0]  # TODO: 관리자 지갑에 수수료 추가
        if transaction_type == "deposit":
            wallet_balance.amount += amount * (1 - fee)
        elif transaction_type == "withdraw":
            wallet_balance.amount -= amount * (1 + fee)
        # admin_wallet_balance.amount += amount * fee
        wallet_balance.save()
        # admin_wallet_balance.save()

        return Transaction.objects.create(wallet=wallet, transaction_type=transaction_type, currency=currency, amount=wallet_balance.amount, fee=amount * fee)
