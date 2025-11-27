from allauth.account.views import LoginView
from django.contrib.auth import get_user_model, login
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView

from .forms import CustomUserCreationForm

User = get_user_model()


def login_view(request):
    return render(request, "users/login.html")


class ProfileView(DetailView):
    model = User
    template_name = "users/profile.html"
    context_object_name = "profile_user"
    slug_field = "username"
    slug_url_kwarg = "username"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        profile_user = self.object

        context["packages"] = profile_user.packages.all().order_by("-created_at")

        context["is_own_profile"] = (
            self.request.user.is_authenticated
            and self.request.user.pk == profile_user.pk
        )

        return context
