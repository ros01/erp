import uuid
from django.db import models
from django.conf import settings
from Applications.models import VisaApplication

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class DocumentRequirement(BaseModel):
    STAGES = [
        ("ADMISSION", "Admission"),
        ("CAS", "CAS"),
        ("VISA", "Visa"),
    ]

    DOCUMENT_CATEGORIES = [
        ("IDENTITY", "Identity Document"),
        ("FINANCIAL", "Financial Document"),
        ("EMPLOYMENT", "Employment Document"),
        ("ADMISSION", "Admission Document"),
        ("FAMILY", "Family/Dependent Document"),
        ("OTHER", "Other"),
    ]

    VISA_TYPES = [
        ("TOURIST - EMPLOYED", "Tourist Visa - Employed"),
        ("TOURIST - SELF EMPLOYED", "Tourist Visa - Self Employed"),
        ("STUDENT", "Student Visa"),
        ("WORK", "Work Visa"),
        ("BUSINESS", "Business Visa"),
        ("TRANSIT", "Transit Visa"),
        ("RESIDENCY", "Residency / PR"),
        ("DIPLOMATIC", "Diplomatic Visa"),
        ("OTHER", "Other"),
    ]

    COUNTRIES = [
        ("UK", "United Kingdom"),
        ("USA", "United States"),
        ("CANADA", "Canada"),
        ("FRANCE", "France"),
        ("QATAR", "Qatar"),
        ("DUBAI", "Dubai"),
        ("SOUTH AFRICA", "South Africa"),
    ]

    stage = models.CharField(max_length=20, choices=STAGES)
    country = models.CharField(max_length=20, choices=COUNTRIES)
    visa_type = models.CharField(max_length=50, choices=VISA_TYPES, default="OTHER")
    name = models.CharField(max_length=255)  # e.g. "Passport", "Bank Statement"
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=DOCUMENT_CATEGORIES, default="OTHER")
    is_mandatory = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["country", "visa_type", "stage", "name"],
                name="unique_requirement_per_stage"
            )
        ]


    # class Meta:
    #     unique_together = ("country", "visa_type", "stage", "name")



    # 🆕 Optional visa form upload for this requirement
    form_file = models.FileField(
        upload_to="pdf_forms/",
        blank=True,
        null=True,
        help_text="Optional PDF form to download or fill for this requirement."
    )

    def __str__(self):
        return f"{self.get_country_display()} | {self.get_visa_type_display()} | {self.name}"

# class Document(BaseModel):
#     application = models.ForeignKey(VisaApplication, on_delete=models.CASCADE, related_name="documents")
#     doc_type = models.CharField(max_length=100)
#     file_path = models.FileField(upload_to="documents/")
#     verified = models.BooleanField(default=False)
#     remarks = models.TextField(blank=True, null=True)

#     def __str__(self):
#         return f"{self.doc_type} - {self.application.reference_no}"


class Document(BaseModel):
    """
    Represents a client’s actual uploaded file for a given requirement.
    Auto-created as placeholders when VisaApplication is created.
    """
    STATUS_CHOICES = [
        ("MISSING", "Missing"),
        ("UPLOADED", "Uploaded"),
        ("PENDING", "Pending Review"),
        ("REVIEWED", "Reviewed"),
        ("REJECTED", "Rejected"),
    ]

    application = models.ForeignKey(
        VisaApplication,
        on_delete=models.CASCADE,
        related_name="documents"
    )
    requirement = models.ForeignKey(
        DocumentRequirement,
        on_delete=models.CASCADE,
        related_name="documents"
    )
    file = models.FileField(upload_to="documents/", blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="MISSING")
    uploaded_at = models.DateTimeField(auto_now=True)
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="verified_documents"
    )
    review_comments = models.TextField(blank=True, null=True)

    # class Meta:
    #     unique_together = ("application", "requirement")  # 1 requirement per app → 1 doc slot
    @property
    def get_status_badge(self):
        """Return (badge_class, label_with_icon) for status."""
        mapping = {
            "MISSING": ("badge-soft-secondary", "⬜ Missing"),
            "UPLOADED": ("badge-soft-info", "📤 Uploaded"),
            "PENDING": ("badge-soft-warning", "⏳ Pending"),
            "VERIFIED": ("badge-soft-success", "✅ Verified"),
            "REJECTED": ("badge-soft-danger", "❌ Rejected"),
        }
        return mapping.get(self.status, ("badge-soft-success", self.status))

    def __str__(self):
        return f"{self.application} - {self.requirement.name} ({self.status})"


