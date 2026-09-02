from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from UserAuth.email_utils import gmail_sender_mismatch, smtp_is_configured
from UserAuth.models import Task
from UserAuth.reminders import web_alarm_schedule


def email_settings(request):
    ctx = {
        'smtp_configured': smtp_is_configured(),
        'gmail_sender_mismatch': gmail_sender_mismatch(),
        'smtp_sender_email': settings.EMAIL_HOST_USER if smtp_is_configured() else '',
    }
    if request.user.is_authenticated:
        ctx['reminder_email'] = request.user.email or ''
    return ctx


def web_alarms(request):
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {}

    now = timezone.now()
    soonest = now - timedelta(minutes=15)
    latest = now + timedelta(hours=24)
    alarms = []
    tasks = Task.objects.filter(
        user=request.user,
        completed=False,
        due_time__isnull=False,
    ).only('id', 'title', 'details', 'due_time')

    for task in tasks:
        due_local = timezone.localtime(task.due_time)
        due_display = due_local.strftime('%b %d, %Y · %I:%M %p')
        for item in web_alarm_schedule(task.due_time):
            when = item['when']
            if when < soonest or when > latest:
                continue
            alarms.append({
                'id': f"{task.id}:{item['key']}",
                'taskId': task.id,
                'title': task.title,
                'details': task.details or '',
                'label': item['label'],
                'alarm': when.isoformat(),
                'display': f"{item['label']} · due {due_display}",
            })
    return {'web_alarms': alarms}
