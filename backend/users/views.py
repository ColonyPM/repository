from django.contrib.auth import get_user_model
from django.db.models import Count, OuterRef, Q, Subquery
from django.shortcuts import render
from django.views.generic import DetailView
from packages.models import Package, PackageVersion

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

        latest_version_sq = (
            PackageVersion.objects.filter(package=OuterRef("pk"))
            .order_by("-major", "-minor", "-patch")
            .values("version")[:1]
        )

        context["packages"] = (
            Package.objects.filter(owner=profile_user)
            .annotate(
                latest_version=Subquery(latest_version_sq),
                download_count=Count("versions__downloads"),
            )
            .order_by("-created_at")
        )

        context["is_own_profile"] = (
            self.request.user.is_authenticated
            and self.request.user.pk == profile_user.pk
        )

        return context
