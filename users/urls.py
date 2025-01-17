from django.urls import path

from .views import RegisterView, LoginView, LogoutView, CustomTokenRefreshView, EnableMFAView, QRCodeView, VerifyOTPView, DeleteMFAView, UserProfileView

urlpatterns = [
    # login, logout, and refresh
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("refresh/", CustomTokenRefreshView.as_view(), name="refresh"),
    # MFA
    path("enable-mfa/", EnableMFAView.as_view(), name="enable-mfa"),
    path("qr-code/", QRCodeView.as_view(), name="qr-code"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify-otp"),
    path("delete-mfa/", DeleteMFAView.as_view(), name="delete-mfa"),
    # profile
    path("profile/", UserProfileView.as_view(), name="profile"),
]
