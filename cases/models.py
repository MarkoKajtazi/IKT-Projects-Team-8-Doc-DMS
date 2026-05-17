from django.conf import settings
from django.db import models
from django.utils import timezone

from accounts.models import Role


class CaseStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    AI_ANALYZED = "ai_analyzed", "AI Analyzed"
    NEEDS_CORRECTION = "needs_correction", "Needs Correction"
    ACCEPTED = "accepted", "Accepted"
    UNDER_REVIEW = "under_review", "Under Review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    ARCHIVED = "archived", "Archived"


# Valid status transitions from Appendix C
VALID_TRANSITIONS = {
    CaseStatus.DRAFT: {CaseStatus.SUBMITTED},
    CaseStatus.SUBMITTED: {CaseStatus.AI_ANALYZED},
    CaseStatus.AI_ANALYZED: {CaseStatus.NEEDS_CORRECTION, CaseStatus.ACCEPTED},
    CaseStatus.NEEDS_CORRECTION: {CaseStatus.SUBMITTED},
    CaseStatus.ACCEPTED: {CaseStatus.UNDER_REVIEW},
    CaseStatus.UNDER_REVIEW: {
        CaseStatus.APPROVED,
        CaseStatus.REJECTED,
        CaseStatus.NEEDS_CORRECTION,
    },
    CaseStatus.APPROVED: {CaseStatus.ARCHIVED},
    CaseStatus.REJECTED: {CaseStatus.ARCHIVED},
    CaseStatus.ARCHIVED: set(),
}


def generate_case_number(template_type_code: str) -> str:
    """
    Generate the next case number in the format YY-TTT-NNNNN (Appendix B).
    Example: 26-100-00003
    """
    year = timezone.now().strftime("%y")
    prefix = f"{year}-{template_type_code}-"

    last = (
        Case.objects.filter(case_number__startswith=prefix)
        .order_by("-case_number")
        .values_list("case_number", flat=True)
        .first()
    )

    last_seq = int(last.split("-")[-1]) if last else 0
    return f"{prefix}{last_seq + 1:05d}"


class Case(models.Model):
    """
    Central entity representing one citizen submission (FR-7 to FR-18).
    Case number format: YY-TTT-NNNNN (Appendix B).
    """

    case_number = models.CharField(max_length=20, unique=True, blank=True)
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_cases",
        limit_choices_to={"role": Role.APPLICANT},
    )
    template = models.ForeignKey(
        "templates_cfg.DocumentTemplate", on_delete=models.PROTECT, related_name="cases"
    )

    # Routing
    department = models.ForeignKey(
        "departments.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cases",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_cases",
    )

    # Workflow
    status = models.CharField(
        max_length=30, choices=CaseStatus.choices, default=CaseStatus.DRAFT
    )

    # AI analysis results (FR-13 to FR-15)
    ai_classification = models.CharField(max_length=200, blank=True)
    ai_confidence_score = models.FloatField(null=True, blank=True)
    ai_validation_notes = models.TextField(blank=True)
    ai_analyzed_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.case_number or f"Draft #{self.pk}"

    def save(self, *args, **kwargs):
        if self.status == CaseStatus.SUBMITTED and not self.case_number:
            self.case_number = generate_case_number(self.template.type_code)
        if self.status == CaseStatus.SUBMITTED and not self.submitted_at:
            self.submitted_at = timezone.now()
        if self.status == CaseStatus.ARCHIVED and not self.archived_at:
            self.archived_at = timezone.now()
        super().save(*args, **kwargs)

    def transition_status(self, new_status: str, performed_by=None, notes: str = "") -> None:
        """
        Move the case to new_status if allowed by VALID_TRANSITIONS (Appendix C).
        Records an AuditTrail entry automatically.
        Raises ValueError on an invalid transition.
        """
        from audit.models import AuditAction, AuditTrail

        allowed = VALID_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Cannot move case from '{self.status}' to '{new_status}'. "
                f"Allowed: {allowed or 'none (terminal state)'}."
            )
        old_status = self.status
        self.status = new_status
        self.save()

        AuditTrail.objects.create(
            case=self,
            action=AuditAction.STATUS_CHANGE,
            performed_by=performed_by,
            old_value=old_status,
            new_value=new_status,
            notes=notes,
        )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["case_number"]),
            models.Index(fields=["applicant", "status"]),
            models.Index(fields=["department", "status"]),
        ]


# ---------------------------------------------------------------------------
# Case Files
# ---------------------------------------------------------------------------


def main_document_upload_path(instance, filename):
    return f"cases/{instance.case.case_number}/main/{filename}"


def attachment_upload_path(instance, filename):
    return f"cases/{instance.case.case_number}/attachments/{filename}"


class CaseDocument(models.Model):
    """The single main PDF for a case (FR-9). Old versions kept, one marked current."""

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(upload_to=main_document_upload_path)
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="Size in bytes.")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_current = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.case} - {self.file_name}"

    class Meta:
        ordering = ["-uploaded_at"]


class CaseAttachment(models.Model):
    """Supporting attachments, up to 5 per case (FR-10)."""

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="attachments")
    attachment_type = models.ForeignKey(
        "templates_cfg.TemplateAttachmentType",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    file = models.FileField(upload_to=attachment_upload_path)
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="Size in bytes.")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.case} - {self.file_name}"

    class Meta:
        ordering = ["uploaded_at"]


# ---------------------------------------------------------------------------
# Validation Result
# ---------------------------------------------------------------------------


class ValidationResult(models.Model):
    """AI/system validation outcome stored for employee review (FR-13, FR-14, FR-17, FR-20)."""

    case = models.OneToOneField(Case, on_delete=models.CASCADE, related_name="validation_result")
    is_complete = models.BooleanField(default=False)
    missing_fields = models.JSONField(default=list, blank=True)
    missing_attachments = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    validated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Validation for {self.case} - {'ok' if self.is_complete else 'incomplete'}"


# ---------------------------------------------------------------------------
# Comment
# ---------------------------------------------------------------------------


class Comment(models.Model):
    """
    Staff comments on a case (FR-21).
    is_internal=False surfaces the comment in the applicant's simplified history (FR-31).
    """

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    text = models.TextField()
    is_internal = models.BooleanField(
        default=True, help_text="If False, visible to the applicant."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author} on {self.case}"

    class Meta:
        ordering = ["created_at"]
