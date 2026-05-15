from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    AuditTrail,
    Case,
    CaseAttachment,
    CaseDocument,
    Comment,
    Department,
    DocumentTemplate,
    Notification,
    RoutingRule,
    TemplateAttachmentType,
    TemplateField,
    User,
    ValidationResult,
)


# ---------------------------------------------------------------------------
# Department
# ---------------------------------------------------------------------------

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display  = ("name", "code", "is_active", "created_at")
    list_filter   = ("is_active",)
    search_fields = ("name", "code")
    ordering      = ("name",)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Extend Django's built-in UserAdmin to expose custom fields
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Role & Department", {"fields": ("role", "department", "can_review", "phone")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Role & Department", {"fields": ("role", "department", "can_review", "phone")}),
    )
    list_display   = ("username", "get_full_name", "email", "role", "department", "can_review", "is_active")
    list_filter    = ("role", "department", "can_review", "is_active")
    search_fields  = ("username", "first_name", "last_name", "email")
    ordering       = ("username",)


# ---------------------------------------------------------------------------
# Document Template
# ---------------------------------------------------------------------------

class TemplateFieldInline(admin.TabularInline):
    model  = TemplateField
    extra  = 1


class TemplateAttachmentTypeInline(admin.TabularInline):
    model  = TemplateAttachmentType
    extra  = 1


class RoutingRuleInline(admin.TabularInline):
    model  = RoutingRule
    extra  = 1


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display  = ("name", "type_code", "default_department", "is_active", "created_at")
    list_filter   = ("is_active", "default_department")
    search_fields = ("name", "type_code")
    ordering      = ("name",)
    inlines       = [TemplateFieldInline, TemplateAttachmentTypeInline, RoutingRuleInline]


# ---------------------------------------------------------------------------
# Routing Rule (standalone, in addition to inline)
# ---------------------------------------------------------------------------

@admin.register(RoutingRule)
class RoutingRuleAdmin(admin.ModelAdmin):
    list_display  = ("template", "department", "priority", "is_active")
    list_filter   = ("is_active", "department")
    search_fields = ("template__name", "department__name")
    ordering      = ("template", "priority")


# ---------------------------------------------------------------------------
# Case
# ---------------------------------------------------------------------------

class CaseDocumentInline(admin.TabularInline):
    model  = CaseDocument
    extra  = 0
    readonly_fields = ("uploaded_at", "file_size")


class CaseAttachmentInline(admin.TabularInline):
    model  = CaseAttachment
    extra  = 0
    readonly_fields = ("uploaded_at", "file_size")


class CommentInline(admin.TabularInline):
    model  = Comment
    extra  = 0
    readonly_fields = ("created_at",)


class AuditTrailInline(admin.TabularInline):
    model  = AuditTrail
    extra  = 0
    readonly_fields = ("action", "performed_by", "old_value", "new_value", "notes", "timestamp")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display   = ("case_number", "applicant", "template", "department", "assigned_to", "status", "submitted_at")
    list_filter    = ("status", "department", "template")
    search_fields  = ("case_number", "applicant__username", "applicant__first_name", "applicant__last_name")
    ordering       = ("-created_at",)
    readonly_fields = (
        "case_number", "created_at", "submitted_at", "updated_at", "archived_at",
        "ai_analyzed_at", "ai_classification", "ai_confidence_score", "ai_validation_notes",
    )
    inlines = [CaseDocumentInline, CaseAttachmentInline, CommentInline, AuditTrailInline]

    fieldsets = (
        ("Identity", {"fields": ("case_number", "applicant", "template")}),
        ("Routing", {"fields": ("department", "assigned_to")}),
        ("Workflow", {"fields": ("status",)}),
        ("AI Analysis", {
            "classes": ("collapse",),
            "fields": ("ai_classification", "ai_confidence_score", "ai_validation_notes", "ai_analyzed_at"),
        }),
        ("Timestamps", {
            "classes": ("collapse",),
            "fields": ("created_at", "submitted_at", "updated_at", "archived_at"),
        }),
    )


# ---------------------------------------------------------------------------
# Validation Result
# ---------------------------------------------------------------------------

@admin.register(ValidationResult)
class ValidationResultAdmin(admin.ModelAdmin):
    list_display  = ("case", "is_complete", "validated_at")
    list_filter   = ("is_complete",)
    search_fields = ("case__case_number",)
    readonly_fields = ("validated_at",)


# ---------------------------------------------------------------------------
# Comment
# ---------------------------------------------------------------------------

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display  = ("case", "author", "is_internal", "created_at")
    list_filter   = ("is_internal",)
    search_fields = ("case__case_number", "author__username")
    readonly_fields = ("created_at",)


# ---------------------------------------------------------------------------
# Audit Trail
# ---------------------------------------------------------------------------

@admin.register(AuditTrail)
class AuditTrailAdmin(admin.ModelAdmin):
    list_display  = ("case", "action", "performed_by", "old_value", "new_value", "timestamp")
    list_filter   = ("action",)
    search_fields = ("case__case_number", "performed_by__username")
    readonly_fields = ("case", "action", "performed_by", "old_value", "new_value", "notes", "timestamp")
    ordering      = ("-timestamp",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ("recipient", "notification_type", "case", "is_read", "created_at")
    list_filter   = ("notification_type", "is_read")
    search_fields = ("recipient__username", "case__case_number")
    readonly_fields = ("created_at", "read_at")
    ordering      = ("-created_at",)