from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views
from .views import PackageDetailView

urlpatterns = [
    path("", views.package_list_view, name="packages"),
    path(
        "results/",
        views.package_list_search_results_view,
        name="packages_search_results",
    ),
    path("<slug:slug>/", PackageDetailView.as_view(), name="package-details"),
    path(
        "<slug:slug>/<str:version>/",
        PackageDetailView.as_view(),
        name="package-version-details",
    ),
]
