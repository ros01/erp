import uuid
from django.db import models

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True

# class ClientProfile(BaseModel):
#     full_name = models.CharField(max_length=255)
#     email = models.EmailField(unique=True)
#     phone = models.CharField(max_length=20, blank=True, null=True)
#     passport_number = models.CharField(max_length=50, unique=True)
#     nationality = models.CharField(max_length=100)
#     date_of_birth = models.DateField()
#     address = models.TextField(blank=True, null=True)

#     def __str__(self):
#         return f"{self.full_name} ({self.passport_number})"

#     class Meta:
#         indexes = [models.Index(fields=["passport_number", "email"])]

# class Notification(BaseModel):
#     client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="notifications")
#     message = models.TextField()
#     sent = models.BooleanField(default=False)
#     sent_at = models.DateTimeField(blank=True, null=True)

#     def __str__(self):
#         return f"Notification to {self.client.full_name} - {self.message[:30]}"
