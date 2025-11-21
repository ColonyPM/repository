from django.contrib.auth import get_user_model, login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView

from .forms import CustomUserCreationForm

User = get_user_model()


class CustomLoginView(LoginView):
    template_name = "users/login.html"
    redirect_authenticated_user = True


class RegisterView(CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = "users/register.html"
    success_url = reverse_lazy("packages")

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect("packages")


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
