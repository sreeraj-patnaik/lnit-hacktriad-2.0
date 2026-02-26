from django.urls import path

from .views import dashboard_view, login_view, logout_view, profile_view, signup_view

urlpatterns = [
    path("", dashboard_view, name="dashboard"),
    path("signup/", signup_view, name="signup"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("profile/", profile_view, name="profile"),
]
