from django.contrib import admin
from .models import *

# @admin.register(DocumentRequirement)
# class DocumentRequirementAdmin(admin.ModelAdmin):
#     list_display = ("country", "visa_type", "name", "category", "is_mandatory")
#     search_fields = ("country", "visa_type", "category")
#     list_filter = ("country", "visa_type")


@admin.register(DocumentRequirement)
class DocumentRequirementAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "visa_type", "is_mandatory", "category")
    list_filter = ("country", "visa_type", "category", "is_mandatory")
    search_fields = ("country", "visa_type", "category", "name", "description")
    fieldsets = (
        (None, {
            "fields": (
                "country", "visa_type", "name", "description",
                "category", "is_mandatory", "form_file"
            )
        }),
    )



@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("application", "requirement", "status", "verified_by")
    search_fields = ("application", "application__reference_no")
    list_filter = ("status", "verified_by")