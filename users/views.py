from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenViewBase

from .serializers import RegisterSerializer, LoginSerializer, LogoutSerializer, CustomTokenRefreshSerializer, EnableMFASerializer, QRCodeSerializer, VerifyOTPSerializer


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
    serializer_class = LogoutSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
            return Response({"detail": "Logged out successfully."}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenRefreshView(TokenViewBase):
    serializer_class = CustomTokenRefreshSerializer


class EnableMFAView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = EnableMFASerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            return Response({"detail": "MFA enabled successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class QRCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = QRCodeSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            device = serializer.validated_data.get("device")
            qr_code_url = serializer.get_qr_code_url(device)
            return Response({"qr_code_url": qr_code_url}, status=status.HTTP_200_OK)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            return Response({"detail": "MFA verification successful."}, status=status.HTTP_200_OK)
        return Response({"error": "Invalid OTP code."}, status=status.HTTP_400_BAD_REQUEST)
