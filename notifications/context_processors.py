def unread_notifications(request):
    """Injects unread_notification_count into every template context."""
    if request.user.is_authenticated:
        count = request.user.notifications.filter(is_read=False).count()
    else:
        count = 0
    return {"unread_notification_count": count}