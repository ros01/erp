import uuid
from django.db import models
from Applications.models import VisaApplication

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True

class Payment(BaseModel):
    application = models.ForeignKey(VisaApplication, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    payment_method = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"{self.transaction_id} - {self.amount}"
