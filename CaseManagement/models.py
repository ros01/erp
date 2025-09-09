import uuid
from django.db import models
from Accounts.models import StaffProfile
from Applications.models import VisaApplication

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
    due_date = models.DateField()
    completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Task for {self.application.reference_no} - {self.assigned_to} - {self.status}"

class ReassignmentHistory(BaseModel):
    application = models.ForeignKey(VisaApplication, on_delete=models.CASCADE, related_name="reassignment_history")
    from_officer = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="reassignments_from")
    to_officer = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="reassignments_to")
    reason = models.TextField(blank=True, null=True)
    reassigned_by = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="reassignments_done")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reassignment {self.application.reference_no} at {self.created_at}"
