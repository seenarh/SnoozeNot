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
    categories = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='others')
    completed = models.BooleanField(default=False)
    focused_minutes = models.PositiveIntegerField(default=0)
    distraction_count = models.PositiveIntegerField(default=0)
    reminder_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title