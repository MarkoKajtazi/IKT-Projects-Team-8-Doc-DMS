"""
Notification signals — satellites pattern.
cases never import from notifications; notifications listen to cases via signals.
All triggers live here so the wiring is in one place.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from cases.models import Case, CaseStatus, Comment
from notifications.models import Notification, NotificationType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _notify(recipient, case, ntype, message):
    """Create a notification, silently skip if recipient is None."""
    if recipient is None:
        return
    Notification.objects.create(
        recipient=recipient,
        case=case,
        notification_type=ntype,
        message=message,
    )


# ---------------------------------------------------------------------------
# Case status changes
# ---------------------------------------------------------------------------

@receiver(post_save, sender=Case)
def on_case_save(sender, instance, created, **kwargs):
    case = instance

    if created:
        # New case submitted — notify department staff (employees + manager)
        # The case may not have a department yet on first save (draft),
        # so we only fire once it has one and is submitted.
        if case.status == CaseStatus.SUBMITTED and case.department:
            _notify_department_on_submission(case)
        return

    # For updates check what changed by comparing to DB value.
    # We use update_fields if available, otherwise check status directly.
    # transition_status() always calls save(), so post_save fires after every transition.
    _handle_status_change(case)


def _notify_department_on_submission(case):
    """Tell every employee/manager in the target department a new case arrived."""
    from accounts.models import Role
    members = case.department.members.filter(
        role__in=[Role.EMPLOYEE, Role.MANAGER, Role.ADMIN]
    )
    for member in members:
        _notify(
            member, case,
            NotificationType.SUBMISSION_RECEIVED,
            f"New case {case.case_number} has been submitted to your department "
            f"({case.department.name}).",
        )


def _handle_status_change(case):
    """Fire the right notification(s) based on current status."""
    status = case.status

    if status == CaseStatus.SUBMITTED:
        # Re-submission after correction — notify assigned employee or department
        target = case.assigned_to
        if target:
            _notify(
                target, case,
                NotificationType.SUBMISSION_RECEIVED,
                f"Case {case.case_number} has been resubmitted by the applicant "
                f"and is ready for review.",
            )

    elif status == CaseStatus.NEEDS_CORRECTION:
        # Applicant must fix something — notify them
        _notify(
            case.applicant, case,
            NotificationType.NEEDS_CORRECTION,
            f"Your case {case.case_number} has been returned and requires corrections. "
            f"Please review the comments and resubmit.",
        )

    elif status == CaseStatus.APPROVED:
        _notify(
            case.applicant, case,
            NotificationType.APPROVED,
            f"Your case {case.case_number} has been approved.",
        )

    elif status == CaseStatus.REJECTED:
        _notify(
            case.applicant, case,
            NotificationType.REJECTED,
            f"Your case {case.case_number} has been rejected. "
            f"Please review the comments for more information.",
        )

    elif status == CaseStatus.ARCHIVED:
        _notify(
            case.applicant, case,
            NotificationType.ARCHIVED,
            f"Your case {case.case_number} has been archived.",
        )


# ---------------------------------------------------------------------------
# Assignment changes
# ---------------------------------------------------------------------------

@receiver(post_save, sender=Case)
def on_case_assigned(sender, instance, created, update_fields, **kwargs):
    """
    Fires when a case is saved with update_fields containing 'assigned_to'.
    assign_case() view calls save(update_fields=['assigned_to']).
    """
    if created:
        return
    if update_fields and "assigned_to" in update_fields and instance.assigned_to:
        _notify(
            instance.assigned_to, instance,
            NotificationType.ASSIGNED,
            f"Case {instance.case_number} has been assigned to you "
            f"({instance.department.name if instance.department else ''}).",
        )


# ---------------------------------------------------------------------------
# Public comments — notify applicant when staff leaves a visible comment
# ---------------------------------------------------------------------------

@receiver(post_save, sender=Comment)
def on_comment_added(sender, instance, created, **kwargs):
    if not created:
        return
    comment = instance
    # Only notify if the comment is visible to the applicant
    if not comment.is_internal:
        _notify(
            comment.case.applicant, comment.case,
            NotificationType.SUBMISSION_RECEIVED,  # closest type; no "comment" type in model
            f"A new comment has been added to your case {comment.case.case_number}. "
            f"Please log in to review it.",
        )