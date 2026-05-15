"""
Django models for AI-Assisted Government Document Management and Workflow System
Based on SRS — ICT Team 8

Status flow (Appendix C):
  Draft → Submitted → AI Analyzed → Needs Correction
  Draft → Submitted → AI Analyzed → Accepted → Under Review → Approved → Archived
  Draft → Submitted → AI Analyzed → Accepted → Under Review → Rejected → Archived
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------

class Role(models.TextChoices):
    APPLICANT   = "applicant",   "Applicant"
    EMPLOYEE    = "employee",    "Employee"
    MANAGER     = "manager",     "Manager"
    ADMIN       = "admin",       "Admin"
    SUPERADMIN  = "superadmin",  "Superadmin"


class CaseStatus(models.TextChoices):
    DRAFT            = "draft",            "Draft"
    SUBMITTED        = "submitted",        "Submitted"
    AI_ANALYZED      = "ai_analyzed",      "AI Analyzed"
    NEEDS_CORRECTION = "needs_correction", "Needs Correction"
    ACCEPTED         = "accepted",         "Accepted"
    UNDER_REVIEW     = "under_review",     "Under Review"
    APPROVED         = "approved",         "Approved"
    REJECTED         = "rejected",         "Rejected"
    ARCHIVED         = "archived",         "Archived"


# Valid status transitions from Appendix C
VALID_TRANSITIONS = {
    CaseStatus.DRAFT:            {CaseStatus.SUBMITTED},
    CaseStatus.SUBMITTED:        {CaseStatus.AI_ANALYZED},
    CaseStatus.AI_ANALYZED:      {CaseStatus.NEEDS_CORRECTION, CaseStatus.ACCEPTED},
    CaseStatus.NEEDS_CORRECTION: {CaseStatus.SUBMITTED},          # applicant resubmits
    CaseStatus.ACCEPTED:         {CaseStatus.UNDER_REVIEW},
    CaseStatus.UNDER_REVIEW:     {CaseStatus.APPROVED, CaseStatus.REJECTED, CaseStatus.NEEDS_CORRECTION},
    CaseStatus.APPROVED:         {CaseStatus.ARCHIVED},
    CaseStatus.REJECTED:         {CaseStatus.ARCHIVED},
    CaseStatus.ARCHIVED:         set(),                            # terminal state
}


class NotificationType(models.TextChoices):
    SUBMISSION_RECEIVED  = "submission_received",  "Submission Received"
    NEEDS_CORRECTION     = "needs_correction",     "Needs Correction"
    APPROVED             = "approved",             "Approved"
    REJECTED             = "rejected",             "Rejected"
    ARCHIVED             = "archived",             "Archived"
    ASSIGNED             = "assigned",             "Case Assigned"
    REASSIGNED           = "reassigned",           "Case Reassigned"
    ESCALATED            = "escalated",            "Case Escalated"
    FORWARDED            = "forwarded",            "Case Forwarded"


class AuditAction(models.TextChoices):
    STATUS_CHANGE  = "status_change",  "Status Change"
    ROUTING        = "routing",        "Routing Action"
    COMMENT_ADDED  = "comment_added",  "Comment Added"
    ASSIGNMENT     = "assignment",     "Assignment"
    ESCALATION     = "escalation",     "Escalation"
    FORWARDING     = "forwarding",     "Forwarding"
    CORRECTION     = "correction",     "Correction Requested"
    FILE_UPLOADED  = "file_uploaded",  "File Uploaded"


# ---------------------------------------------------------------------------
# Department
# ---------------------------------------------------------------------------

class Department(models.Model):
    """Organizational unit responsible for handling cases (FR-34)."""

    name        = models.CharField(max_length=200, unique=True)
    code        = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


# ---------------------------------------------------------------------------
# Custom User
# ---------------------------------------------------------------------------

class User(AbstractUser):
    """
    Single user model covering all roles (FR-1 to FR-6).
    Applicants have no department; staff accounts require one.
    The can_review flag grants approval/rejection capability to employees
    without requiring a separate role (FR-6).
    """

    role        = models.CharField(max_length=20, choices=Role.choices, default=Role.APPLICANT)
    department  = models.ForeignKey(
        Department,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="members",
    )
    can_review  = models.BooleanField(
        default=False,
        help_text="Grants approve/reject/return capability to employees (FR-6).",
    )
    phone       = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"


# ---------------------------------------------------------------------------
# Document Template
# ---------------------------------------------------------------------------

class DocumentTemplate(models.Model):
    """
    Predefined government form type with known mandatory fields and
    required attachments (FR-35, FR-36).
    The type_code feeds into the case-number format: YY-TTT-NNNNN (Appendix B).
    """

    name               = models.CharField(max_length=200)
    type_code          = models.CharField(
        max_length=10, unique=True,
        help_text="3-character code used in case numbers, e.g. '100'.",
    )
    description        = models.TextField(blank=True)
    default_department = models.ForeignKey(
        Department,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="default_templates",
        help_text="Default destination department for this template.",
    )
    is_active          = models.BooleanField(default=True)
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.type_code})"

    class Meta:
        ordering = ["name"]


class TemplateField(models.Model):
    """Mandatory metadata fields that must be present in the main PDF (FR-36)."""

    template    = models.ForeignKey(DocumentTemplate, on_delete=models.CASCADE, related_name="required_fields")
    field_name  = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    is_required = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.template.type_code} - {self.field_name}"

    class Meta:
        unique_together = ("template", "field_name")


class TemplateAttachmentType(models.Model):
    """Required attachment types per template, e.g. 'Proof of income' (FR-36)."""

    template    = models.ForeignKey(DocumentTemplate, on_delete=models.CASCADE, related_name="required_attachment_types")
    name        = models.CharField(max_length=200)
    description = models.CharField(max_length=255, blank=True)
    is_required = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.template.type_code} - {self.name}"

    class Meta:
        unique_together = ("template", "name")


# ---------------------------------------------------------------------------
# Routing Rule
# ---------------------------------------------------------------------------

class RoutingRule(models.Model):
    """
    Maps a template to a destination department (FR-16, FR-37).
    Lowest priority number wins.
    """

    template    = models.ForeignKey(DocumentTemplate, on_delete=models.CASCADE, related_name="routing_rules")
    department  = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="routing_rules")
    priority    = models.PositiveSmallIntegerField(default=10)
    is_active   = models.BooleanField(default=True)
    notes       = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.template.type_code} -> {self.department.code} (priority {self.priority})"

    class Meta:
        ordering = ["template", "priority"]
        unique_together = ("template", "department")


# ---------------------------------------------------------------------------
# Case
# ---------------------------------------------------------------------------

def generate_case_number(template_type_code: str) -> str:
    """
    Generate the next case number in the format YY-TTT-NNNNN (Appendix B).
    Example: 26-100-00003

    The sequence is scoped per (year, type_code) so counters reset each year.
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

    case_number  = models.CharField(max_length=20, unique=True, blank=True)
    applicant    = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="submitted_cases",
        limit_choices_to={"role": Role.APPLICANT},
    )
    template     = models.ForeignKey(DocumentTemplate, on_delete=models.PROTECT, related_name="cases")

    # Routing
    department   = models.ForeignKey(
        Department,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="cases",
    )
    assigned_to  = models.ForeignKey(
        User,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_cases",
    )

    # Workflow
    status       = models.CharField(max_length=30, choices=CaseStatus.choices, default=CaseStatus.DRAFT)

    # AI analysis results (FR-13 to FR-15)
    ai_classification    = models.CharField(max_length=200, blank=True)
    ai_confidence_score  = models.FloatField(null=True, blank=True)
    ai_validation_notes  = models.TextField(blank=True)
    ai_analyzed_at       = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at   = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    updated_at   = models.DateTimeField(auto_now=True)
    archived_at  = models.DateTimeField(null=True, blank=True)

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

        Usage:
            case.transition_status(CaseStatus.ACCEPTED, performed_by=request.user)
        """
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

    case        = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="documents")
    file        = models.FileField(upload_to=main_document_upload_path)
    file_name   = models.CharField(max_length=255)
    file_size   = models.PositiveIntegerField(help_text="Size in bytes.")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_current  = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.case} - {self.file_name}"

    class Meta:
        ordering = ["-uploaded_at"]


class CaseAttachment(models.Model):
    """Supporting attachments, up to 5 per case (FR-10)."""

    case             = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="attachments")
    attachment_type  = models.ForeignKey(TemplateAttachmentType, null=True, blank=True, on_delete=models.SET_NULL)
    file        = models.FileField(upload_to=attachment_upload_path)
    file_name   = models.CharField(max_length=255)
    file_size   = models.PositiveIntegerField(help_text="Size in bytes.")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
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

    case                = models.OneToOneField(Case, on_delete=models.CASCADE, related_name="validation_result")
    is_complete         = models.BooleanField(default=False)
    missing_fields      = models.JSONField(default=list, blank=True)
    missing_attachments = models.JSONField(default=list, blank=True)
    notes               = models.TextField(blank=True)
    validated_at        = models.DateTimeField(auto_now_add=True)

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

    case        = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="comments")
    author      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    text        = models.TextField()
    is_internal = models.BooleanField(default=True, help_text="If False, visible to the applicant.")
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author} on {self.case}"

    class Meta:
        ordering = ["created_at"]


# ---------------------------------------------------------------------------
# Audit Trail
# ---------------------------------------------------------------------------

class AuditTrail(models.Model):
    """Append-only record of all significant case actions (FR-30)."""

    case          = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="audit_trail")
    action        = models.CharField(max_length=30, choices=AuditAction.choices)
    performed_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    old_value     = models.CharField(max_length=100, blank=True)
    new_value     = models.CharField(max_length=100, blank=True)
    notes         = models.TextField(blank=True)
    timestamp     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.case} - {self.action} at {self.timestamp:%Y-%m-%d %H:%M}"

    class Meta:
        ordering = ["timestamp"]


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------

class Notification(models.Model):
    """In-app notifications for applicants and staff (FR-25 to FR-27). No email/SMS in v1."""

    recipient          = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    case               = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="notifications", null=True, blank=True)
    notification_type  = models.CharField(max_length=30, choices=NotificationType.choices)
    message            = models.TextField()
    is_read            = models.BooleanField(default=False)
    created_at         = models.DateTimeField(auto_now_add=True)
    read_at            = models.DateTimeField(null=True, blank=True)

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])

    def __str__(self):
        return f"Notification to {self.recipient} [{self.notification_type}]"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
        ]