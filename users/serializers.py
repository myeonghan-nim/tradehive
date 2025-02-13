from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email, RegexValidator
from django.core.exceptions import ValidationError
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUserTOTPDevice

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
        user = User.objects.create_user(
            email=validated_data["email"], username=validated_data["username"], password=validated_data["password"], phone_number=validated_data.get("phone_number")
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class LogoutSerializer(serializers.Serializer):
    def validate(self, data):
        request = self.context.get("request")
        refresh_token = validate_authorization_header(request)
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
        if settings.SIMPLE_JWT["ROTATE_REFRESH_TOKENS"]:
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
