import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Role
from templates_cfg.models import DocumentTemplate, RoutingRule

from .forms import (
    AssignCaseForm,
    NewSubmissionForm,
    ResubmitCaseForm,
    StaffCommentForm,
    StaffStatusForm,
)
from .models import Case, CaseAttachment, CaseDocument, CaseStatus, Comment


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_superuser(user):
    return user.is_superuser or user.role == Role.SUPERADMIN

def _is_admin_or_above(user):
    return _is_superuser(user) or user.role == Role.ADMIN

def _is_staff(user):
    return user.role in (Role.EMPLOYEE, Role.MANAGER, Role.ADMIN, Role.SUPERADMIN) or user.is_superuser

def _can_access_case(user, case):
    """Return True if the user is allowed to view this case at all."""
    if _is_superuser(user):
        return True
    if user.role == Role.APPLICANT:
        return case.applicant == user
    if user.role == Role.ADMIN:
        return case.department == user.department
    # employee / manager: must belong to the case's department
    return case.department == user.department

def _can_act_on_case(user, case):
    """Return True if the user can change status / add comments."""
    if _is_superuser(user):
        return True
    if user.role == Role.ADMIN:
        return case.department == user.department
    if user.role in (Role.EMPLOYEE, Role.MANAGER):
        return case.department == user.department
    return False


# ---------------------------------------------------------------------------
# Applicant views
# ---------------------------------------------------------------------------

@login_required
def my_cases(request):
    cases = Case.objects.filter(applicant=request.user)
    return render(request, "cases/my_cases.html", {"cases": cases})


@login_required
def new_submission(request):
    if request.method == "POST":
        form = NewSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            template = form.cleaned_data["template"]
            main_pdf  = form.cleaned_data["main_pdf"]

            case = Case.objects.create(
                applicant=request.user,
                template=template,
                status=CaseStatus.DRAFT,
            )
            CaseDocument.objects.create(
                case=case, file=main_pdf,
                file_name=main_pdf.name, file_size=main_pdf.size,
                uploaded_by=request.user,
            )
            for att in request.FILES.getlist("attachments")[:5]:
                CaseAttachment.objects.create(
                    case=case, file=att,
                    file_name=att.name, file_size=att.size,
                    uploaded_by=request.user,
                )

            routing = (
                RoutingRule.objects.filter(template=template, is_active=True)
                .order_by("priority").first()
            )
            if routing:
                case.department = routing.department
            elif template.default_department:
                case.department = template.default_department

            case.transition_status(CaseStatus.SUBMITTED, performed_by=request.user)
            messages.success(request, f"Case {case.case_number} submitted successfully.")
            return redirect("case_detail", pk=case.pk)
    else:
        form = NewSubmissionForm()

    requirements = {}
    for tmpl in DocumentTemplate.objects.filter(is_active=True).prefetch_related(
        "required_fields", "required_attachment_types"
    ):
        requirements[tmpl.pk] = {
            "description": tmpl.description,
            "fields": [
                {"name": f.field_name, "description": f.description, "required": f.is_required}
                for f in tmpl.required_fields.all()
            ],
            "attachments": [
                {"name": a.name, "description": a.description, "required": a.is_required}
                for a in tmpl.required_attachment_types.all()
            ],
        }

    return render(request, "cases/new_submission.html", {
        "form": form,
        "template_requirements_json": json.dumps(requirements),
    })


@login_required
def resubmit_case(request, pk):
    case = get_object_or_404(Case, pk=pk, applicant=request.user)

    if case.status != CaseStatus.NEEDS_CORRECTION:
        messages.error(request, "This case cannot be edited at this stage.")
        return redirect("case_detail", pk=pk)

    if request.method == "POST":
        form = ResubmitCaseForm(request.POST, request.FILES)
        if form.is_valid():
            new_pdf = form.cleaned_data.get("main_pdf")
            if new_pdf:
                case.documents.update(is_current=False)
                CaseDocument.objects.create(
                    case=case, file=new_pdf,
                    file_name=new_pdf.name, file_size=new_pdf.size,
                    uploaded_by=request.user, is_current=True,
                )
            slots = max(0, 5 - case.attachments.count())
            for att in request.FILES.getlist("attachments")[:slots]:
                CaseAttachment.objects.create(
                    case=case, file=att,
                    file_name=att.name, file_size=att.size,
                    uploaded_by=request.user,
                )
            case.transition_status(CaseStatus.SUBMITTED, performed_by=request.user)
            messages.success(request, "Your case has been resubmitted successfully.")
            return redirect("case_detail", pk=pk)
    else:
        form = ResubmitCaseForm()

    documents   = case.documents.all()
    attachments = case.attachments.all()
    comments    = case.comments.filter(is_internal=False)
    return render(request, "cases/case_detail.html", {
        "case": case, "documents": documents,
        "attachments": attachments, "comments": comments,
        "resubmit_form": form,
    })


# ---------------------------------------------------------------------------
# Shared case detail (role-aware)
# ---------------------------------------------------------------------------

@login_required
def case_detail(request, pk):
    case = get_object_or_404(Case, pk=pk)
    user = request.user

    if not _can_access_case(user, case):
        messages.error(request, "You do not have access to this case.")
        return redirect("my_cases" if user.role == Role.APPLICANT else "work_queue")

    documents   = case.documents.all()
    attachments = case.attachments.all()

    # Applicants only see public comments; staff see all
    if user.role == Role.APPLICANT:
        comments = case.comments.filter(is_internal=False)
    else:
        comments = case.comments.all()

    ctx = {
        "case": case,
        "documents": documents,
        "attachments": attachments,
        "comments": comments,
        "can_act": _can_act_on_case(user, case),
        "is_staff": _is_staff(user),
        "is_admin": _is_admin_or_above(user),
    }

    # Applicant resubmit form
    if user.role == Role.APPLICANT and case.status == CaseStatus.NEEDS_CORRECTION:
        ctx["resubmit_form"] = ResubmitCaseForm()

    # Staff action forms
    if _can_act_on_case(user, case):
        ctx["comment_form"] = StaffCommentForm()
        ctx["status_form"]  = StaffStatusForm(current_status=case.status)

    # Admin assignment form — only for admins viewing their department's case
    if _is_admin_or_above(user) and case.department == user.department:
        ctx["assign_form"] = AssignCaseForm(
            department=case.department,
            initial={"assigned_to": case.assigned_to},
        )

    return render(request, "cases/case_detail.html", ctx)


# ---------------------------------------------------------------------------
# Staff actions (POST-only)
# ---------------------------------------------------------------------------

@login_required
def add_comment(request, pk):
    case = get_object_or_404(Case, pk=pk)
    if not _can_act_on_case(request.user, case):
        messages.error(request, "You do not have permission to comment on this case.")
        return redirect("case_detail", pk=pk)

    if request.method == "POST":
        form = StaffCommentForm(request.POST)
        if form.is_valid():
            Comment.objects.create(
                case=case,
                author=request.user,
                text=form.cleaned_data["text"],
                is_internal=form.cleaned_data["is_internal"],
            )
            messages.success(request, "Comment added.")
        else:
            messages.error(request, "Invalid comment.")
    return redirect("case_detail", pk=pk)


@login_required
def change_status(request, pk):
    case = get_object_or_404(Case, pk=pk)
    if not _can_act_on_case(request.user, case):
        messages.error(request, "You do not have permission to change this case's status.")
        return redirect("case_detail", pk=pk)

    if request.method == "POST":
        form = StaffStatusForm(current_status=case.status, data=request.POST)
        if form.is_valid():
            new_status = form.cleaned_data["new_status"]
            notes      = form.cleaned_data.get("notes", "")
            try:
                case.transition_status(new_status, performed_by=request.user, notes=notes)
                messages.success(request, f"Status updated to {CaseStatus(new_status).label}.")
            except ValueError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Invalid status transition.")
    return redirect("case_detail", pk=pk)


@login_required
def assign_case(request, pk):
    case = get_object_or_404(Case, pk=pk)

    # Only admins of the same department (or superusers) can assign
    if not (_is_admin_or_above(request.user) and (
        _is_superuser(request.user) or case.department == request.user.department
    )):
        messages.error(request, "You do not have permission to assign this case.")
        return redirect("case_detail", pk=pk)

    if request.method == "POST":
        form = AssignCaseForm(department=case.department, data=request.POST)
        if form.is_valid():
            case.assigned_to = form.cleaned_data["assigned_to"]
            case.save(update_fields=["assigned_to"])
            name = case.assigned_to.get_full_name() if case.assigned_to else "nobody"
            messages.success(request, f"Case assigned to {name}.")
        else:
            messages.error(request, "Invalid assignment.")
    return redirect("case_detail", pk=pk)


# ---------------------------------------------------------------------------
# Staff queue (employee / manager / admin)
# ---------------------------------------------------------------------------

@login_required
def work_queue(request):
    user = request.user

    if not _is_staff(user):
        return redirect("my_cases")

    # Superuser sees everything; others scoped to their department
    if _is_superuser(user):
        qs = Case.objects.exclude(status=CaseStatus.DRAFT)
    else:
        qs = Case.objects.filter(department=user.department).exclude(status=CaseStatus.DRAFT)

    # Employees only see cases assigned to them or unassigned in their dept
    if user.role == Role.EMPLOYEE:
        qs = qs.filter(assigned_to__in=[user, None])

    # Filtering
    q      = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    if q:
        qs = qs.filter(case_number__icontains=q) | qs.filter(
            applicant__first_name__icontains=q
        ) | qs.filter(applicant__last_name__icontains=q)
    if status:
        qs = qs.filter(status=status)

    cases = qs.select_related("applicant", "template", "assigned_to", "department")

    return render(request, "cases/work_queue.html", {"cases": cases})