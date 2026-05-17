from django.contrib import admin

from .models import AuditTrail


@admin.register(AuditTrail)
class AuditTrailAdmin(admin.ModelAdmin):
    list_display = ("case", "action", "performed_by", "old_value", "new_value", "timestamp")
    list_filter = ("action",)
    search_fields = ("case__case_number", "performed_by__username")
    readonly_fields = ("case", "action", "performed_by", "old_value", "new_value", "notes", "timestamp")
    ordering = ("-timestamp",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
