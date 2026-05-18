from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from templates_cfg.models import RoutingRule

from .forms import NewSubmissionForm
from .models import Case, CaseAttachment, CaseDocument, CaseStatus


@login_required
def my_cases(request):
    cases = Case.objects.filter(applicant=request.user)
    return render(request, "cases/my_cases.html", {"cases": cases})


@login_required
def work_queue(request):
    cases = Case.objects.filter(department=request.user.department).exclude(status="draft")
    return render(request, "cases/work_queue.html", {"cases": cases})


@login_required
def new_submission(request):
    if request.method == "POST":
        form = NewSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            template = form.cleaned_data["template"]
            main_pdf = form.cleaned_data["main_pdf"]

            # Create case as draft
            case = Case.objects.create(
                applicant=request.user,
                template=template,
                status=CaseStatus.DRAFT,
            )

            # Save main PDF
            CaseDocument.objects.create(
                case=case,
                file=main_pdf,
                file_name=main_pdf.name,
                file_size=main_pdf.size,
                uploaded_by=request.user,
            )

            # Save attachments (up to 5)
            attachments = request.FILES.getlist("attachments")
            for att in attachments[:5]:
                CaseAttachment.objects.create(
                    case=case,
                    file=att,
                    file_name=att.name,
                    file_size=att.size,
                    uploaded_by=request.user,
                )

            # Auto-route to department via RoutingRule (FR-16)
            routing = (
                RoutingRule.objects.filter(template=template, is_active=True)
                .order_by("priority")
                .first()
            )
            if routing:
                case.department = routing.department
            elif template.default_department:
                case.department = template.default_department

            # Submit the case (Draft -> Submitted)
            case.transition_status(CaseStatus.SUBMITTED, performed_by=request.user)

            messages.success(request, f"Case {case.case_number} submitted successfully.")
            return redirect("case_detail", pk=case.pk)
    else:
        form = NewSubmissionForm()
    return render(request, "cases/new_submission.html", {"form": form})


@login_required
def case_detail(request, pk):
    case = get_object_or_404(Case, pk=pk)

    # Applicants can only see their own cases
    if request.user.role == "applicant" and case.applicant != request.user:
        messages.error(request, "You do not have access to this case.")
        return redirect("my_cases")

    documents = case.documents.all()
    attachments = case.attachments.all()
    comments = case.comments.filter(is_internal=False) if request.user.role == "applicant" else case.comments.all()

    return render(request, "cases/case_detail.html", {
        "case": case,
        "documents": documents,
        "attachments": attachments,
        "comments": comments,
    })
