import uuid
from django.db import models
from Accounts.models import *
from django.conf import settings
import secrets
from django.utils import timezone


def default_reference_no():
    date = timezone.now().strftime("%Y%m%d")
    token = secrets.token_hex(4).upper()  # 8 hex chars
    return f"APP-{date}-{token}"


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True




# class VisaApplication(models.Model):
#     STATUS_CHOICES = [
#         ("Draft", "Draft"),
#         ("Submitted", "Submitted"),
#         ("Queued", "Queued"),
#         ("Under Review", "Under Review"),
#         ("Form Filled", "Form Filled"),
#         ("Admin Review", "Admin Review"),
#         ("Approved", "Approved"),
#         ("Rejected", "Rejected"),
#     ]

#     client = models.ForeignKey(User, on_delete=models.CASCADE, related_name="applications")
#     country = models.CharField(max_length=100)
#     application_type = models.CharField(max_length=100)
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Draft")
#     form_data = models.JSONField(blank=True, null=True)  # visa-specific form details
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"VisaApplication {self.id} - {self.client.username} ({self.status})"

# applications/models.py

class VisaApplication(BaseModel):
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

    STATUS_CHOICES = [
    	# ("DRAFT", "Draft"),
    	# ("DOCUMENTS SUBMITTED", "Documents Submitted"),
        ("QUEUED", "Queued"),
        ("INITIATED", "Initiated by Officer"),
        ("ASSIGNED", "Assigned to Officer"),
        ("REVIEWED", "Reviewed"),
        ("FORM FILLED", "Form Filled"),
        ("ADMIN REVIEW", "Admin Review"),
        ("SUBMITTED", "Awaiting Embassy Decision"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    # client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="visa_applications")
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name="visa_applications")
    country = models.CharField(max_length=20, choices=COUNTRIES)
    visa_type = models.CharField(max_length=50, choices=VISA_TYPES, default="OTHER")
    created_by_officer = models.ForeignKey(
        StaffProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="initiated_applications"
    )

    assigned_officer = models.ForeignKey(
        StaffProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_applications"   # ✅ add this
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="QUEUED")
    form_data = models.JSONField(blank=True, null=True)  # visa-specific form details
    visa_application_url = models.URLField(blank=True, null=True)
    submission_date = models.DateTimeField(blank=True, null=True)
    decision_date = models.DateTimeField(blank=True, null=True)
    reference_no = models.CharField(max_length=50, unique=True)
    rejection_letter = models.FileField(upload_to="rejection_letters/", blank=True, null=True)

    # @property
    # def assigned_officer_name(self):
    #     """Readable name for assigned officer (if any)."""
    #     return self.assigned_officer.user.get_full_name() if self.assigned_officer else None

    # @property
    # def created_by_officer_name(self):
    #     """Readable name for initiating officer (if any)."""
    #     return self.created_by_officer.user.get_full_name() if self.created_by_officer else None


    def __str__(self):
         return f"{self.reference_no} ({self.country}, {self.visa_type})"


         
    # def __str__(self):
        # return f"VisaApplication {self.reference_no} - {self.client}"

    class Meta:
        indexes = [models.Index(fields=["reference_no", "status"])]

    # def __str__(self):
    #     return f"{self.client.username} | {self.get_country_display()} | {self.get_visa_type_display()} | {self.get_status_display()}"

# class PreviousRefusalLetter(BaseModel):
#     application = models.ForeignKey(
#         VisaApplication,
#         related_name="refusal_letters",
#         on_delete=models.CASCADE
#     )
#     file = models.FileField(upload_to="refusals/")
#     uploaded_at = models.DateTimeField(auto_now_add=True)
#     uploaded_by = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         null=True, blank=True,
#         on_delete=models.SET_NULL
#     )

#     def __str__(self):
#         return f"Refusal Letter for {self.application.reference_no} ({self.id})"

class PreviousRefusalLetter(BaseModel):
    application = models.ForeignKey(
        VisaApplication,
        on_delete=models.CASCADE,
        related_name="refusal_letters"
    )
    file = models.FileField(upload_to="refusal_letters/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Refusal Letter for {self.application.reference_no}"

class EmbassySubmission(BaseModel):
    application = models.OneToOneField(VisaApplication, on_delete=models.CASCADE, related_name="submission")
    reviewed_by = models.ForeignKey(
        StaffProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_reviewer"   # ✅ add this
    )
    submitted_by = models.CharField(max_length=255)
    submission_channel = models.CharField(max_length=50)  # API / Manual
    review_date = models.DateTimeField()
    submission_date = models.DateTimeField()

    def __str__(self):
        return f"Submission for {self.application.reference_no}"

class Decision(BaseModel):
    DECISION_CHOICES = [
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
        ("Pending", "Pending"),
    ]

    application = models.OneToOneField(VisaApplication, on_delete=models.CASCADE, related_name="decision")
    decision_status = models.CharField(max_length=50, choices=DECISION_CHOICES)
    decision_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.application.reference_no} - {self.decision_status}"

