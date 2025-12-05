from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from ninja import NinjaAPI
from packages.api import router as packages_router
from users.api import router as users_router

api = NinjaAPI(title="CPM API", urls_namespace="api")

api.add_router("/users/", users_router)
api.add_router("/packages/", packages_router)

urlpatterns = [
    path("", RedirectView.as_view(url="/packages/", permanent=False)),
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    path("users/", include("users.urls")),
    path("packages/", include("packages.urls")),
    path("accounts/", include("allauth.urls")),
]
