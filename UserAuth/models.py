from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

CATEGORY_CHOICES = [
    ('work', 'Work'),
    ('study', 'Study'),
    ('personal', 'Personal'),
    ('others', 'Others'),
]

class Task(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    details = models.TextField(blank=True)
    due_time = models.DateTimeField(null=True, blank=True)
    categories = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='Inbox')
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    focused_minutes = models.PositiveIntegerField(default=0)
    distraction_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title


class FocusSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='focus_sessions')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='sessions')  # <-- important
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    minutes = models.PositiveIntegerField(null=True, blank=True)

    def end_session(self):
        if not self.end_time:
            self.end_time = timezone.now()
            delta = self.end_time - self.start_time
            self.minutes = int(delta.total_seconds() // 60)
            self.save()
            if self.task and self.minutes:
                self.task.focused_minutes += self.minutes
                self.task.save()

    def __str__(self):
        return f"{self.task.title} session ({self.minutes or 0} mins)"
