from django.contrib import admin

from .models import DownloadEvent, Package


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    # Columns in list view
    list_display = (
        "name",
        "version",
        "author",
        "download_count",
        "deprecated",
        "created_at",
    )

    readonly_fields = ("download_count",)


@admin.register(DownloadEvent)
class DownloadEventAdmin(admin.ModelAdmin):
    list_display = ("package", "timestamp")
    list_filter = ("package",)
