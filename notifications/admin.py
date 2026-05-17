from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "notification_type", "case", "is_read", "created_at")
    list_filter = ("notification_type", "is_read")
    search_fields = ("recipient__username", "case__case_number")
    readonly_fields = ("created_at", "read_at")
    ordering = ("-created_at",)
