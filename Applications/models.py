import uuid
from django.db import models
from Accounts.models import User, ClientProfile
from django.conf import settings


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



class VisaApplication(BaseModel):
    VISA_TYPES = [
        ("TOURIST", "Tourist Visa"),
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
        ("SCHENGEN", "Schengen"),
        ("QATAR", "Qatar"),
        ("DUBAI", "Dubai"),
    ]

    STATUS_CHOICES = [
    	("DRAFT", "Draft"),
    	("DOCUMENTS SUBMITTED", "Documents Submitted"),
        ("QUEUED", "Queued"),
        ("ASSIGNED", "Assigned to Officer"),
        ("UNDER REVIEW", "Under Review"),
        ("FORM FILLED", "Form Filled"),
        ("ADMIN REVIEW", "Admin Review"),
        ("SUBMITTED", "Submitted to Embassy"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    # client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="visa_applications")
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name="visa_applications")
    country = models.CharField(max_length=20, choices=COUNTRIES)
    visa_type = models.CharField(max_length=50, choices=VISA_TYPES, default="OTHER")
    assigned_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="assigned_applications"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="QUEUED")
    form_data = models.JSONField(blank=True, null=True)  # visa-specific form details
    submission_date = models.DateField(blank=True, null=True)
    decision_date = models.DateField(blank=True, null=True)
    reference_no = models.CharField(max_length=50, unique=True)

    # def __str__(self):
    #     return f"VisaApplication {self.id} - {self.client.username} ({self.status})"

    def __str__(self):
        return f"VisaApplication {self.reference_no} - {self.client.full_name}"

    class Meta:
        indexes = [models.Index(fields=["reference_no", "status"])]

    # def __str__(self):
    #     return f"{self.client.username} | {self.get_country_display()} | {self.get_visa_type_display()} | {self.get_status_display()}"

# class VisaApplication(BaseModel):
#     STATUS_CHOICES = [
#         ("Pending", "Pending"),
#         ("Submitted", "Submitted"),
#         ("Under Review", "Under Review"),
#         ("Approved", "Approved"),
#         ("Rejected", "Rejected"),
#     ]

#     client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="applications")
#     visa_type = models.CharField(max_length=100)
#     destination_country = models.CharField(max_length=100)
#     status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="Pending")
#     submission_date = models.DateField(blank=True, null=True)
#     decision_date = models.DateField(blank=True, null=True)
#     reference_no = models.CharField(max_length=50, unique=True)

#     def __str__(self):
#         return f"{self.reference_no} - {self.client.full_name}"

#     class Meta:
#         indexes = [models.Index(fields=["reference_no", "status"])]


class EmbassySubmission(BaseModel):
    application = models.OneToOneField(VisaApplication, on_delete=models.CASCADE, related_name="submission")
    submitted_by = models.CharField(max_length=255)
    submission_channel = models.CharField(max_length=50)  # API / Manual
    submission_date = models.DateField()

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

