from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ApplicantRegistrationForm


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        form = ApplicantRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard")
    else:
        form = ApplicantRegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


@login_required
def dashboard(request):
    role = request.user.role
    if request.user.is_superuser or role in ("admin", "superadmin"):
        return redirect("/admin/")
    elif role in ("employee", "manager"):
        return redirect("work_queue")
    else:
        return redirect("my_cases")