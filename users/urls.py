from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import CustomLoginView, ProfileView, RegisterView

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("<str:username>/", ProfileView.as_view(), name="user-profile"),
]
