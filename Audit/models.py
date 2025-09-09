import uuid
from django.db import models

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True

# class AuditLog(BaseModel):
#     user = models.CharField(max_length=255)
#     action = models.CharField(max_length=255)
#     model_name = models.CharField(max_length=255)
#     object_id = models.UUIDField()
#     changes = models.TextField()

#     def __str__(self):
#         return f"{self.user} - {self.action} on {self.model_name}"
