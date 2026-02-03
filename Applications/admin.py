from django.contrib import admin
from .models import *

@admin.register(VisaApplication)
class VisaApplicationAdmin(admin.ModelAdmin):
    list_display = ("reference_no", "client", "country", "visa_type",  "assigned_officer", "status", "submission_date", "decision_date")
    search_fields = ("reference_no", "client__full_name", "visa_type", "country")
    list_filter = ("reference_no", "status", "country")

@admin.register(PreviousRefusalLetter)
class PreviousRefusalLetterAdmin(admin.ModelAdmin):
    list_display = ("application", "file", "uploaded_at")
    search_fields = ("application", "file")
    list_filter = ("application", "file")


@admin.register(RejectionLetter)
class RejectionLetterAdmin(admin.ModelAdmin):
    list_display = ("application", "file", "uploaded_at")
    search_fields = ("application", "file")
    list_filter = ("application", "file")

# @admin.register(FormProcessing)
# class FormProcessingAdmin(admin.ModelAdmin):
#     list_display = ("application", "application_url", "visa_application_username", "file")
#     search_fields = ("application", "application_url", "visa_application_username")
#     list_filter = ("application", "file")

@admin.register(StageDefinition)
class StageDefinitionAdmin(admin.ModelAdmin):
    list_display = ("country", "stage", "order")
    search_fields = ("country", "stage", "order")
    list_filter = ("country", "stage")



@admin.register(EmbassySubmission)
class EmbassySubmissionAdmin(admin.ModelAdmin):
    list_display = ("application", "reviewed_by", "submitted_by", "review_date", "submission_channel", "submission_date")
    search_fields = ("application", "reviewed_by", "submitted_by", "submission_channel")
    list_filter = ("application", "submission_channel", "submission_date")


@admin.register(Decision)
class DecisionAdmin(admin.ModelAdmin):
    list_display = ("application", "decision_status", "decision_date", "notes")
    search_fields = ("application", "application__reference_no", "decision_status", "decision_date")
    list_filter = ("application", "decision_date")