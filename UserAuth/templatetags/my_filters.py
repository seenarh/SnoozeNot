from datetime import timedelta

from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def dict_get(d, key):
    return d.get(key)


@register.filter
def due_urgency(dt):
    if not dt:
        return ''
    now = timezone.now()
    if dt < now:
        return 'is-overdue'
    if dt <= now + timedelta(hours=6):
        return 'is-soon'
    return ''


def _duration_chunk(seconds):
    if seconds < 60:
        return 'less than a minute'
    if seconds < 3600:
        minutes = seconds // 60
        return f'{minutes} min'
    if seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes and hours < 6:
            return f'{hours} hr {minutes} min'
        return '1 hr' if hours == 1 else f'{hours} hrs'
    days = seconds // 86400
    return '1 day' if days == 1 else f'{days} days'


@register.filter
def relative_due(dt):
    if not dt:
        return ''
    seconds = int((dt - timezone.now()).total_seconds())
    span = abs(seconds)
    chunk = _duration_chunk(span)
    if seconds < 0:
        if span < 60:
            return 'Overdue just now'
        return f'Overdue by {chunk}'
    if span < 60:
        return 'Due now'
    return f'In {chunk}'
