from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import CustomLoginView, RegisterView, profile_placeholder

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("<slug:username>/", profile_placeholder, name="user-profile"),
]
