from django.db.models import Count, OuterRef, Prefetch, Q, Subquery
from django.shortcuts import render
from django.utils import timezone
from django.views.generic import ListView
from django.views.generic.detail import DetailView

from .models import Package, PackageVersion


def package_list_view(request):
    query = request.GET.get("q", "")

    latest_version_sq = (
        PackageVersion.objects.filter(package=OuterRef("pk"))
        .order_by("-major", "-minor", "-patch")
        .values("version")[:1]
    )

    packages = Package.objects.annotate(
        latest_version=Subquery(latest_version_sq),
        download_count=Count("versions__downloads"),
    )

    if query:
        packages = packages.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(author__icontains=query)
        )

    context = {"object_list": packages}
    return render(request, "packages/packages.html", context)


def package_list_search_results_view(request):
    package = Package.objects.all()

    context = {"package": package, "package_count": package.count()}
    return render(request, "packages/packages_search_results.html", context)


class PackageDetailView(DetailView):
    model = Package
    template_name = "packages/package_details.html"

    def get_queryset(self):
        versions_qs = PackageVersion.objects.order_by("-major", "-minor", "-patch")
        return (
            Package.objects.select_related("owner")
            .annotate(download_count=Count("versions__downloads"))
            .prefetch_related(Prefetch("versions", queryset=versions_qs))
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        versions = list(self.object.versions.all())  # already ordered by prefetch
        ctx["versions"] = versions

        version_str = self.kwargs.get("version")

        if not versions:
            ctx["selected_version"] = None
            return ctx

        if version_str is None:
            selected = versions[0]  # latest
        else:
            selected = next((v for v in versions if v.version == version_str), None)
            if selected is None:
                raise Http404("Version not found")

        ctx["selected_version"] = selected
        return ctx
