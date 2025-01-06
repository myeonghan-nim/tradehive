from django.contrib.auth.views import LoginView
from django.urls import path

from .views import signup_view, profile_view

urlpatterns = [
    path("signup/", signup_view, name="signup"),
    path("login/", LoginView.as_view(template_name="users/login.html"), name="login"),  # TODO: Change LoginView to a custom view
    path("profile/", profile_view, name="profile"),
]
