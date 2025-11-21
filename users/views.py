from django.contrib.auth import get_user_model, login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import CustomUserCreationForm


class CustomLoginView(LoginView):
    template_name = "users/login.html"
    redirect_authenticated_user = True


class RegisterView(CreateView):
    model = get_user_model()
    form_class = CustomUserCreationForm
    template_name = "users/register.html"
    success_url = reverse_lazy("packages")

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect("packages")
