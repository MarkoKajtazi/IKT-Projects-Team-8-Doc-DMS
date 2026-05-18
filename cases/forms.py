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