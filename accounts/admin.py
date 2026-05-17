from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Role & Department", {"fields": ("role", "department", "can_review", "phone")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Role & Department", {"fields": ("role", "department", "can_review", "phone")}),
    )
    list_display = (
        "username",
        "get_full_name",
        "email",
        "role",
        "department",
        "can_review",
        "is_active",
    )
    list_filter = ("role", "department", "can_review", "is_active")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("username",)
