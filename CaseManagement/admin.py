from django.contrib import admin
from .models import *

@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin):
    list_display = ("application", "assigned_to", "status", "description", "due_date", "completed")
    search_fields = ("application__reference_no", "assigned_to", "description")
    list_filter = ("completed", "due_date")


@admin.register(ReassignmentHistory)
class ReassignmentHistoryAdmin(admin.ModelAdmin):
    list_display = ("application", "from_officer", "to_officer", "reason", "reassigned_by", "created_at")
    search_fields = ("application__reference_no", "from_officer", "reassigned_by")
    list_filter = ("application", "created_at")