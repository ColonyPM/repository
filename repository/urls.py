from django.contrib import admin
from django.urls import include, path
from ninja import NinjaAPI

from packages.api import router as packages_router
from users.api import router as users_router

api = NinjaAPI(title="CPM API")

api.add_router("/users/", users_router)
api.add_router("/packages/", packages_router)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    path("users/", include("users.urls")),
    path("packages/", include("packages.urls")),
]
