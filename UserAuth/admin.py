from django.contrib import admin
from .models import Task, FocusSession

# Register your models here.
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'categories','completed', 'focused_minutes','distraction_count','created_at')
    list_filter = ('categories','completed',)
    search_fields = ('title',)

@admin.register(FocusSession)
class FocusSessionAdmin(admin.ModelAdmin):
    list_display = ('task','start_time','end_time','minutes')
    list_filter = ('start_time',)