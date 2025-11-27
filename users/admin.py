from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group

from .forms import CustomUserChangeForm
from .models import User


class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    model = User

    list_display = (
        "username",
        "avatar",
        "is_staff",
        "is_active",
        "is_superuser",
    )
    list_filter = ("is_staff", "is_active", "is_superuser")
    search_fields = ("username",)
    ordering = ("username",)

    fieldsets = (
        (None, {"fields": ("username", "avatar", "password")}),
        (
            "Permissions",
            {"fields": ("is_staff", "is_active", "is_superuser")},
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "password1", "password2"),
            },
        ),
    )

    filter_horizontal = []


admin.site.register(User, CustomUserAdmin)
admin.site.unregister(Group)
