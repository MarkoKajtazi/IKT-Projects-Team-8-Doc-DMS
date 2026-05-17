from django.contrib import admin

from audit.models import AuditTrail

from .models import Case, CaseAttachment, CaseDocument, Comment, ValidationResult


class CaseDocumentInline(admin.TabularInline):
    model = CaseDocument
    extra = 0
    readonly_fields = ("uploaded_at", "file_size")


class CaseAttachmentInline(admin.TabularInline):
    model = CaseAttachment
    extra = 0
    readonly_fields = ("uploaded_at", "file_size")


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ("created_at",)


class AuditTrailInline(admin.TabularInline):
    model = AuditTrail
    extra = 0
    readonly_fields = ("action", "performed_by", "old_value", "new_value", "notes", "timestamp")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = (
        "case_number",
        "applicant",
        "template",
        "department",
        "assigned_to",
        "status",
        "submitted_at",
    )
    list_filter = ("status", "department", "template")
    search_fields = (
        "case_number",
        "applicant__username",
        "applicant__first_name",
        "applicant__last_name",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "case_number",
        "created_at",
        "submitted_at",
        "updated_at",
        "archived_at",
        "ai_analyzed_at",
        "ai_classification",
        "ai_confidence_score",
        "ai_validation_notes",
    )
    inlines = [CaseDocumentInline, CaseAttachmentInline, CommentInline, AuditTrailInline]

    fieldsets = (
        ("Identity", {"fields": ("case_number", "applicant", "template")}),
        ("Routing", {"fields": ("department", "assigned_to")}),
        ("Workflow", {"fields": ("status",)}),
        (
            "AI Analysis",
            {
                "classes": ("collapse",),
                "fields": (
                    "ai_classification",
                    "ai_confidence_score",
                    "ai_validation_notes",
                    "ai_analyzed_at",
                ),
            },
        ),
        (
            "Timestamps",
            {
                "classes": ("collapse",),
                "fields": ("created_at", "submitted_at", "updated_at", "archived_at"),
            },
        ),
    )


@admin.register(ValidationResult)
class ValidationResultAdmin(admin.ModelAdmin):
    list_display = ("case", "is_complete", "validated_at")
    list_filter = ("is_complete",)
    search_fields = ("case__case_number",)
    readonly_fields = ("validated_at",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("case", "author", "is_internal", "created_at")
    list_filter = ("is_internal",)
    search_fields = ("case__case_number", "author__username")
    readonly_fields = ("created_at",)
