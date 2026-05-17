from django.contrib import admin

from .models import DocumentTemplate, RoutingRule, TemplateAttachmentType, TemplateField


class TemplateFieldInline(admin.TabularInline):
    model = TemplateField
    extra = 1


class TemplateAttachmentTypeInline(admin.TabularInline):
    model = TemplateAttachmentType
    extra = 1


class RoutingRuleInline(admin.TabularInline):
    model = RoutingRule
    extra = 1


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "type_code", "default_department", "is_active", "created_at")
    list_filter = ("is_active", "default_department")
    search_fields = ("name", "type_code")
    ordering = ("name",)
    inlines = [TemplateFieldInline, TemplateAttachmentTypeInline, RoutingRuleInline]


@admin.register(RoutingRule)
class RoutingRuleAdmin(admin.ModelAdmin):
    list_display = ("template", "department", "priority", "is_active")
    list_filter = ("is_active", "department")
    search_fields = ("template__name", "department__name")
    ordering = ("template", "priority")
