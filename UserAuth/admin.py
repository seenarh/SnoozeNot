from django.contrib import admin
from .models import Task, FocusLog


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'categories', 'completed', 'due_time')
    list_filter = ('categories', 'completed')
    search_fields = ('title',)


@admin.register(FocusLog)
class FocusLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'minutes', 'task', 'created_at')
    list_filter = ('created_at',)
