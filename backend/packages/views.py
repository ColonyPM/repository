from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone
from django.views.generic import ListView
from django.views.generic.detail import DetailView

from .models import Package


def package_list_view(request):
    query = request.GET.get("q", "")
    if query:
        packages = Package.objects.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(author__icontains=query)
        )
    else:
        packages = Package.objects.all()

    context = {"object_list": packages}
    return render(request, "packages/packages.html", context)


def package_list_search_results_view(request):
    package = Package.objects.all()

    context = {"package": package, "package_count": package.count()}
    return render(request, "packages/packages_search_results.html", context)


class PackageDetailView(DetailView):
    model = Package
    template_name = "packages/package_details.html"
