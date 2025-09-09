from django.contrib import admin
from .models import *

@admin.register(VisaApplication)
class VisaApplicationAdmin(admin.ModelAdmin):
    list_display = ("reference_no", "client", "country", "visa_type",  "assigned_officer", "status", "submission_date", "decision_date")
    search_fields = ("reference_no", "client__full_name", "visa_type", "country")
    list_filter = ("reference_no", "status", "country")


@admin.register(EmbassySubmission)
class EmbassySubmissionAdmin(admin.ModelAdmin):
    list_display = ("application", "submitted_by", "submission_channel", "submission_date")
    search_fields = ("application", "submitted_by", "submission_channel")
    list_filter = ("application", "submission_channel", "submission_date")


@admin.register(Decision)
class DecisionAdmin(admin.ModelAdmin):
    list_display = ("application", "decision_status", "decision_date", "notes")
    search_fields = ("application", "application__reference_no", "decision_status", "decision_date")
    list_filter = ("application", "decision_date")