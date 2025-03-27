from django.urls import path
from .views import register, signin, home, search, logout_view, forgot_password_view

urlpatterns = [
    path("", home, name="home"),
    path("signup/", register, name="signup"),
    path("signin/", signin, name="signin"),
    path("search/", search, name="search"),
    path("logout/", logout_view, name="logout"),
    path("forgot/", forgot_password_view, name="forgot"),
]
