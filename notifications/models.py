from django.conf import settings
from django.db import models
from django.utils import timezone


class NotificationType(models.TextChoices):
    SUBMISSION_RECEIVED = "submission_received", "Submission Received"
    NEEDS_CORRECTION = "needs_correction", "Needs Correction"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    ARCHIVED = "archived", "Archived"
    ASSIGNED = "assigned", "Case Assigned"
    REASSIGNED = "reassigned", "Case Reassigned"
    ESCALATED = "escalated", "Case Escalated"
    FORWARDED = "forwarded", "Case Forwarded"


class Notification(models.Model):
    """In-app notifications for applicants and staff (FR-25 to FR-27). No email/SMS in v1."""

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    case = models.ForeignKey(
        "cases.Case",
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

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
