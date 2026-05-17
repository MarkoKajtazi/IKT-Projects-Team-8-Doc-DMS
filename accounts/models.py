from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    APPLICANT = "applicant", "Applicant"
    EMPLOYEE = "employee", "Employee"
    MANAGER = "manager", "Manager"
    ADMIN = "admin", "Admin"
    SUPERADMIN = "superadmin", "Superadmin"


class User(AbstractUser):
    """
    Single user model covering all roles (FR-1 to FR-6).
    Applicants have no department; staff accounts require one.
    The can_review flag grants approval/rejection capability to employees
    without requiring a separate role (FR-6).
    """

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.APPLICANT)
    department = models.ForeignKey(
        "departments.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="members",
    )
    can_review = models.BooleanField(
        default=False,
        help_text="Grants approve/reject/return capability to employees (FR-6).",
    )
    phone = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
