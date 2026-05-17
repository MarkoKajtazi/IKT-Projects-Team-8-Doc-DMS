from django.conf import settings
from django.db import models


class AuditAction(models.TextChoices):
    STATUS_CHANGE = "status_change", "Status Change"
    ROUTING = "routing", "Routing Action"
    COMMENT_ADDED = "comment_added", "Comment Added"
    ASSIGNMENT = "assignment", "Assignment"
    ESCALATION = "escalation", "Escalation"
    FORWARDING = "forwarding", "Forwarding"
    CORRECTION = "correction", "Correction Requested"
    FILE_UPLOADED = "file_uploaded", "File Uploaded"


class AuditTrail(models.Model):
    """Append-only record of all significant case actions (FR-30)."""

    case = models.ForeignKey(
        "cases.Case", on_delete=models.CASCADE, related_name="audit_trail"
    )
    action = models.CharField(max_length=30, choices=AuditAction.choices)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    old_value = models.CharField(max_length=100, blank=True)
    new_value = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.case} - {self.action} at {self.timestamp:%Y-%m-%d %H:%M}"

    class Meta:
        ordering = ["timestamp"]
