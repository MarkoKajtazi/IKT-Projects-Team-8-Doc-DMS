from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Notification


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(recipient=request.user)

    # Mark all as read when the page is opened
    unread = notifications.filter(is_read=False)
    for n in unread:
        n.mark_read()

    return render(request, "notifications/list.html", {
        "notifications": notifications,
        "unread_count": unread.count(),
    })


@login_required
def mark_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.mark_read()
    return redirect("notification_list")