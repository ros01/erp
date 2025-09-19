from django.contrib import admin
from .models import *

@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin):
    list_display = ("application", "assigned_to", "status", "description", "due_date", "completed")
    search_fields = ("application__reference_no", "assigned_to", "description")
    list_filter = ("completed", "due_date")


# 

@admin.register(ReassignmentLog)
class ReassignmentLogAdmin(admin.ModelAdmin):
    list_display = ("application", "from_officer", "to_officer", "reassigned_by", "strategy", "created_at")
    list_filter = ("strategy", "created_at")
    search_fields = ("application__reference_no", "from_officer__user__username", "to_officer__user__username", "reassigned_by__username")

