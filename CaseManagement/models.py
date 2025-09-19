import uuid
from django.db import models
from Accounts.models import StaffProfile
from Applications.models import VisaApplication
from django.db import models
from django.conf import settings



class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True

# class Task(BaseModel):
#     application = models.ForeignKey(VisaApplication, on_delete=models.CASCADE, related_name="tasks")
#     assigned_to = models.CharField(max_length=255)
#     description = models.TextField()
#     due_date = models.DateField()
#     completed = models.BooleanField(default=False)

#     def __str__(self):
#         return f"Task for {self.application.reference_no} - {self.assigned_to}"

# from django.db import models
# from applications.models import VisaApplication



# class ReassignmentLog(BaseModel):
#     application = models.ForeignKey("VisaApplication", on_delete=models.CASCADE, related_name="reassignment_logs")
#     from_officer = models.ForeignKey("Accounts.StaffProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="reassignments_from")
#     to_officer = models.ForeignKey("Accounts.StaffProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="reassignments_to")
#     reassigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="performed_reassignments")
#     strategy = models.CharField(max_length=50, choices=[("manual", "Manual"), ("bulk", "Bulk"), ("auto-round-robin", "Auto Round Robin"), ("auto-workload", "Auto Workload")])
#     timestamp = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"Reassignment of {self.application.reference_no} from {self.from_officer} to {self.to_officer} on {self.timestamp}"


class TaskAssignment(BaseModel):
    STATUS_CHOICES = [
        ("Queued", "Queued"),
        ("Assigned", "Assigned"),
        ("Form Filled", "Form Filled"),
        ("Completed", "Completed"),
    ]

    application = models.OneToOneField(VisaApplication, on_delete=models.CASCADE, related_name="task")
    assigned_to = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Queued")
    description = models.TextField()
    due_date = models.DateField(auto_now_add=True)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Task for {self.application.reference_no} - {self.assigned_to} - {self.status}"


class ReassignmentLog(BaseModel):
    application = models.ForeignKey(VisaApplication, on_delete=models.CASCADE, related_name="reassignment_history")
    from_officer = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="reassignments_from")
    to_officer = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="reassignments_to")
    reason = models.TextField(blank=True, null=True)
    reassigned_by = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="reassignments_done")
    strategy = models.CharField(max_length=50, choices=[("manual", "Manual"), ("bulk", "Bulk"), ("auto-round-robin", "Auto Round Robin"), ("auto-workload", "Auto Workload")])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reassignment {self.application.reference_no} at {self.created_at}"
