from django import forms

from templates_cfg.models import DocumentTemplate


class NewSubmissionForm(forms.Form):
    template = forms.ModelChoiceField(
        queryset=DocumentTemplate.objects.filter(is_active=True),
        label="Document type",
        empty_label="-- Select document type --",
    )
    main_pdf = forms.FileField(
        label="Upload main PDF",
        help_text="PDF format, max 10 MB.",
    )

    def clean_main_pdf(self):
        pdf = self.cleaned_data["main_pdf"]
        if not pdf.name.lower().endswith(".pdf"):
            raise forms.ValidationError("Only PDF files are accepted.")
        if pdf.size > 10 * 1024 * 1024:
            raise forms.ValidationError("File size must not exceed 10 MB.")
        return pdf


class AttachmentForm(forms.Form):
    file = forms.FileField(label="Upload attachment")


class ResubmitCaseForm(forms.Form):
    """Applicant re-uploads corrected documents (FR-23)."""
    main_pdf = forms.FileField(
        label="Replace main PDF",
        required=False,
        help_text="Upload a new PDF to replace the current one. Leave blank to keep the existing file.",
    )

    def clean_main_pdf(self):
        pdf = self.cleaned_data.get("main_pdf")
        if pdf:
            if not pdf.name.lower().endswith(".pdf"):
                raise forms.ValidationError("Only PDF files are accepted.")
            if pdf.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File size must not exceed 10 MB.")
        return pdf


class StaffCommentForm(forms.Form):
    """Employee/manager adds a comment to a case."""
    text = forms.CharField(
        label="Comment",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Write your comment…"}),
    )
    is_internal = forms.BooleanField(
        label="Internal only (not visible to applicant)",
        required=False,
        initial=False,
    )


class StaffStatusForm(forms.Form):
    """Employee/manager changes the status of a case."""
    new_status = forms.ChoiceField(label="Change status to")
    notes = forms.CharField(
        label="Notes (optional)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Reason for status change…"}),
    )

    def __init__(self, current_status, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from cases.models import VALID_TRANSITIONS, CaseStatus
        self._current_status = current_status
        self._allowed = VALID_TRANSITIONS.get(current_status, set())
        # Show all statuses so staff see the full workflow;
        # unavailable ones are labelled clearly and rejected on clean.
        self.fields["new_status"].choices = [
            (s, CaseStatus(s).label + ("" if s in self._allowed else " (not available)"))
            for s in CaseStatus.values
            if s != current_status
        ]

    def clean_new_status(self):
        chosen = self.cleaned_data["new_status"]
        if chosen not in self._allowed:
            from cases.models import CaseStatus
            raise forms.ValidationError(
                f"Cannot move to {CaseStatus(chosen).label!r} from the current status."
            )
        return chosen


class AssignCaseForm(forms.Form):
    """Admin assigns a case to an employee in the same department."""
    assigned_to = forms.ModelChoiceField(
        queryset=None,  # set in __init__
        label="Assign to",
        empty_label="-- Unassigned --",
        required=False,
    )

    def __init__(self, department, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from accounts.models import User, Role
        self.fields["assigned_to"].queryset = User.objects.filter(
            department=department,
            role__in=[Role.EMPLOYEE, Role.MANAGER],
        )