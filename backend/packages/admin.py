from django.contrib import admin

from .models import DownloadEvent, Package, PackageVersion


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    # Columns in list view
    list_display = (
        "name",
        "author",
        "deprecated",
        "created_at",
    )


@admin.register(DownloadEvent)
class DownloadEventAdmin(admin.ModelAdmin):
    list_display = ("version", "timestamp")
    list_filter = ("version",)


admin.site.register(PackageVersion)
