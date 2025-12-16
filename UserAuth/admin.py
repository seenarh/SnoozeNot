from django.contrib import admin
from .models import Task

# Register your models here.
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'categories','completed','due_time')
    list_filter = ('categories','completed',)
    search_fields = ('title',)
