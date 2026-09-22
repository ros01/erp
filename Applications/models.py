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

class StageDefinition(models.Model):
    STAGES = [
        ("ADMISSION", "Admission"),
        ("CAS", "CAS"),
        ("VISA", "Visa"),
    ]

    country = models.CharField(max_length=20)
    stage = models.CharField(max_length=20, choices=STAGES)
    order = models.PositiveIntegerField()

    class Meta:
        unique_together = ("country", "stage")
        ordering = ["order"]

    def __str__(self):
        return f"{self.country} → {self.stage} ({self.order})"



class VisaApplication(BaseModel):
    
    VISA_TYPES = [
        ("TOURIST - EMPLOYED", "Tourist Visa - Employed"),
        ("TOURIST - SELF EMPLOYED", "Tourist Visa - Self Employed"),
        ("STUDENT", "Student Visa"),
        ("CHILD STUDENT", "Child Student Visa"),
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
        ("REFUSED", "Refused"),
    ]

    # client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="visa_applications")
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name="visa_applications")
    country = models.CharField(max_length=20, choices=COUNTRIES)
    visa_type = models.CharField(max_length=50, choices=VISA_TYPES, default="OTHER")
    # current_stage = models.CharField(
    #     max_length=20,
    #     default="ADMISSION"
    # )

    stage = models.CharField(
        max_length=20,
        choices=[
            ("ADMISSION", "Admission"),
            ("CAS", "CAS"),
            ("VISA", "Visa"),
        ],
        default="ADMISSION",
    )



    progress = models.PositiveIntegerField(default=0)  # 0–100

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

    # 🔒 Admin gatekeeping: while status == "ASSIGNED", the assigned Case
    # Officer cannot review documents or continue processing this
    # application until Admin either validates the auto-assignment or
    # reassigns it to a different officer. Both actions set this True.
    # Applications a Case Officer creates themselves (status "INITIATED")
    # are exempt - see Applications.signals.
    admin_validated = models.BooleanField(default=False)
    validated_by = models.ForeignKey(
        StaffProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validated_applications",
    )
    validated_at = models.DateTimeField(null=True, blank=True)

    # 🔒 Client-visibility gate: once a decision (status APPROVED/REFUSED)
    # is recorded, the client can't see it until Admin explicitly clicks
    # "Notify Client". Until then, client-facing serializers cap the
    # visible status at "SUBMITTED" ("Awaiting Embassy Decision") - see
    # VisaApplicationSerializer.to_representation and
    # VisaApplicationDetailSerializer.to_representation in
    # Applications.serializers.
    client_notified = models.BooleanField(default=False)
    notified_by = models.ForeignKey(
        StaffProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notified_applications",
    )
    client_notified_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="QUEUED")
    form_data = models.JSONField(blank=True, null=True)  # visa-specific form details
    visa_application_url = models.URLField(blank=True, null=True)
    submission_date = models.DateTimeField(blank=True, null=True)
    decision_date = models.DateTimeField(blank=True, null=True)
    reference_no = models.CharField(max_length=50, unique=True)

    # 📋 Case Officer dashboard "Activity" timeline timestamps - set the
    # first (and each subsequent) time the application's status reaches
    # these particular values, so the dashboard can report a real event
    # date instead of relying on updated_at (which isn't refreshed by the
    # status-only .save(update_fields=[...]) calls that make these
    # transitions). See Applications.api_views.DocumentReviewAPIView and
    # Applications.serializers.VisaApplicationUrlUpdateSerializer(000).
    reviewed_at = models.DateTimeField(blank=True, null=True)
    admin_review_sent_at = models.DateTimeField(blank=True, null=True)

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


    def get_stage_sequence(self):
        """
        Returns ordered list of stage codes for this application's country.
        """
        return list(
            StageDefinition.objects
            .filter(country=self.country)
            .order_by("order")
            .values_list("stage", flat=True)
        )


    def get_next_stage(self):
        stages = self.get_stage_sequence()

        if self.stage not in stages:
            return None

        idx = stages.index(self.stage)
        if idx + 1 < len(stages):
            return stages[idx + 1]

        return None

    def advance_stage(self):
        stages = self.get_stage_sequence()

        if self.stage not in stages:
            return False

        current_index = stages.index(self.stage)
        next_stage = self.get_next_stage()

        if not next_stage:
            # final stage completed
            self.progress = 100
            self.save(update_fields=["progress"])
            return False

        # progress = completed stages / total stages
        completed_stages = current_index + 1
        self.progress = int((completed_stages / len(stages)) * 100)

        self.stage = next_stage
        self.save(update_fields=["stage", "progress"])
        return True



    # def advance_stage(self):
    #     next_stage = self.get_next_stage()
    #     if not next_stage:
    #         return False

    #     stages = self.get_stage_sequence()
    #     self.stage = next_stage
    #     # self.progress = int(((stages.index(next_stage) + 1) / len(stages)) * 100)

    #     completed_stages = stages.index(self.stage)  # stages BEFORE current
    #     self.progress = int((completed_stages / len(stages)) * 100)


    #     self.save(update_fields=["stage", "progress"])
    #     return True





    def is_stage_completed(application, stage):
        docs = Document.objects.filter(
            application=application,
            requirement__stage=stage,
            requirement__is_mandatory=True
        )
        return docs.exists() and all(d.status == "REVIEWED" for d in docs)



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

class RefusalLetter(models.Model):
    application = models.ForeignKey(
        VisaApplication,
        on_delete=models.CASCADE,
        related_name="refusal_letter"
    )
    file = models.FileField(upload_to="refusal_letter/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Refusal Letter - {self.application.reference_no}"


class StudentApplicationPipeline(BaseModel):
    STAGES = [
        ("ADMISSION", "Admission Application"),
        ("CAS", "CAS Processing"),
        ("VISA", "Student Visa Application"),
        ("COMPLETED", "Completed"),
    ]

    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE)
    country = models.CharField(max_length=20, choices=VisaApplication.COUNTRIES)
    current_stage = models.CharField(max_length=20, choices=STAGES, default="ADMISSION")

    admission_application = models.OneToOneField(
        "AdmissionApplication", null=True, blank=True, on_delete=models.SET_NULL
    )
    cas_application = models.OneToOneField(
        "CASApplication", null=True, blank=True, on_delete=models.SET_NULL
    )
    visa_application = models.OneToOneField(
        VisaApplication, null=True, blank=True, on_delete=models.SET_NULL
    )

    def __str__(self):
        return f"{self.client} – {self.country} – {self.current_stage}"


class AdmissionApplication(BaseModel):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted"),
        ("OFFER_RECEIVED", "Offer Received"),
        ("REJECTED", "Rejected"),
    ]

    pipeline = models.OneToOneField(StudentApplicationPipeline, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="DRAFT")
    offer_letter = models.FileField(upload_to="offer_letters/", blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)


class CASApplication(BaseModel):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted"),
        ("CAS_ISSUED", "CAS Issued"),
        ("REJECTED", "Rejected"),
    ]

    pipeline = models.OneToOneField(StudentApplicationPipeline, on_delete=models.CASCADE)
    cas_number = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="DRAFT")
    cas_letter = models.FileField(upload_to="cas_letters/", blank=True, null=True)



# StageDefinition.objects.bulk_create([
#     StageDefinition(country="UK", stage="ADMISSION", order=1),
#     StageDefinition(country="UK", stage="CAS", order=2),
#     StageDefinition(country="UK", stage="VISA", order=3),

#     StageDefinition(country="CANADA", stage="ADMISSION", order=1),
#     StageDefinition(country="CANADA", stage="VISA", order=2),

#     StageDefinition(country="USA", stage="ADMISSION", order=1),
#     StageDefinition(country="USA", stage="VISA", order=2),
# ])


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
        ("Refused", "Refused"),
        ("Pending", "Pending"),
    ]

    application = models.OneToOneField(VisaApplication, on_delete=models.CASCADE, related_name="decision")
    decision_status = models.CharField(max_length=50, choices=DECISION_CHOICES)
    decision_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.application.reference_no} - {self.decision_status}"

