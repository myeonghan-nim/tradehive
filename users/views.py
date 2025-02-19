from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenViewBase

from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    LogoutSerializer,
    CustomTokenRefreshSerializer,
    ChangePasswordSerializer,
    EnableMFASerializer,
    DeleteMFASerializer,
    QRCodeSerializer,
    VerifyOTPSerializer,
    UserProfileSerializer,
    UserProfileDeleteSerialzier,
    TransactionSerializer,
)


def process_serializer(serializer, success_status, success_message=None, additional_data=None):
    if serializer.is_valid():
        response_data = {}
        if success_message:
            response_data["detail"] = success_message
        if additional_data:
            response_data.update(additional_data)
        return Response(response_data, status=success_status)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({"refresh": str(refresh), "access": str(refresh.access_token)}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = authenticate(request, **serializer.validated_data)
            if user:
                refresh = RefreshToken.for_user(user)
                return Response({"refresh": str(refresh), "access": str(refresh.access_token)}, status=status.HTTP_200_OK)
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(TokenViewBase):
    def post(self, request):
        serializer = LogoutSerializer(data=request.data, context={"request": request})
        return process_serializer(serializer, status.HTTP_205_RESET_CONTENT, "Logged out successfully.")


class CustomTokenRefreshView(TokenViewBase):
    serializer_class = CustomTokenRefreshSerializer


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, user=request.user, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MFAView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = EnableMFASerializer(data=request.data, context={"request": request})
        return process_serializer(serializer, status.HTTP_200_OK, "MFA enabled successfully.")

    def delete(self, request):
        serializer = DeleteMFASerializer(data=request.data, context={"request": request})
        return process_serializer(serializer, status.HTTP_200_OK, "MFA disabled successfully.")


class QRCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = QRCodeSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            device = serializer.validated_data.get("device")
            qr_code_url = serializer.get_qr_code_url(device)
            return Response({"qr_code_url": qr_code_url}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyOTPView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data, context={"request": request})
        return process_serializer(serializer, status.HTTP_200_OK, "MFA verification successful.")


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        return process_serializer(serializer, status.HTTP_200_OK, "Profile updated successfully.")

    def delete(self, request):
        serializer = UserProfileDeleteSerialzier(data=request.data, context={"request": request})
        if serializer.is_valid():
            request.user.delete()
            return Response({"detail": "User deleted successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TransactionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TransactionSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
