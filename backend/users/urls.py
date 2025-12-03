from django.urls import path

from .views import ProfileView, login_view

urlpatterns = [
    path("<str:username>/", ProfileView.as_view(), name="user-profile"),
]
