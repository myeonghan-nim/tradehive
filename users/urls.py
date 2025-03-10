from django.urls import path

from .views import RegisterView, LoginView, LogoutView, CustomTokenRefreshView, MFAView, QRCodeView, VerifyOTPView, UserProfileView, ChangePasswordView, TransactionView

urlpatterns = [
    # 사용자 관리
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("refresh/", CustomTokenRefreshView.as_view(), name="refresh"),
    path("change-password/", ChangePasswordView.as_view(), name="change_password"),
    # MFA
    path("enable-mfa/", MFAView.as_view(), name="enable-mfa"),
    path("delete-mfa/", MFAView.as_view(), name="delete-mfa"),
    path("qr-code/", QRCodeView.as_view(), name="qr-code"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify-otp"),
    # 프로필
    path("profile/", UserProfileView.as_view(), name="profile"),
    # transactions
    path("transactions/", TransactionView.as_view(), name="transactions"),
]
