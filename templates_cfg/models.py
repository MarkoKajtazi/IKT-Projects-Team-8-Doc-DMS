from django.db import models


class DocumentTemplate(models.Model):
    """
    Predefined government form type with known mandatory fields and
    required attachments (FR-35, FR-36).
    The type_code feeds into the case-number format: YY-TTT-NNNNN (Appendix B).
    """

    name = models.CharField(max_length=200)
    type_code = models.CharField(
        max_length=10,
        unique=True,
        help_text="3-character code used in case numbers, e.g. '100'.",
    )
    description = models.TextField(blank=True)
    default_department = models.ForeignKey(
        "departments.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="default_templates",
        help_text="Default destination department for this template.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.type_code})"

    class Meta:
        ordering = ["name"]


class TemplateField(models.Model):
    """Mandatory metadata fields that must be present in the main PDF (FR-36)."""

    template = models.ForeignKey(
        DocumentTemplate, on_delete=models.CASCADE, related_name="required_fields"
    )
    field_name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    is_required = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.template.type_code} - {self.field_name}"

    class Meta:
        unique_together = ("template", "field_name")


class TemplateAttachmentType(models.Model):
    """Required attachment types per template, e.g. 'Proof of income' (FR-36)."""

    template = models.ForeignKey(
        DocumentTemplate, on_delete=models.CASCADE, related_name="required_attachment_types"
    )
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=255, blank=True)
    is_required = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.template.type_code} - {self.name}"

    class Meta:
        unique_together = ("template", "name")


class RoutingRule(models.Model):
    """
    Maps a template to a destination department (FR-16, FR-37).
    Lowest priority number wins.
    """

    template = models.ForeignKey(
        DocumentTemplate, on_delete=models.CASCADE, related_name="routing_rules"
    )
    department = models.ForeignKey(
        "departments.Department", on_delete=models.CASCADE, related_name="routing_rules"
    )
    priority = models.PositiveSmallIntegerField(default=10)
    is_active = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.template.type_code} -> {self.department.code} (priority {self.priority})"

    class Meta:
        ordering = ["template", "priority"]
        unique_together = ("template", "department")
