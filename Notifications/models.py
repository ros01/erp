from django.db import models
from Accounts.models import User
from Applications.models import VisaApplication

class Notification(models.Model):
    CHANNEL_CHOICES = [
        ("Email", "Email"),
        ("SMS", "SMS"),
        ("System", "System"),
    ]
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Sent", "Sent"),
        ("Failed", "Failed"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    application = models.ForeignKey(VisaApplication, on_delete=models.CASCADE, related_name="notifications", null=True, blank=True)
    message = models.TextField()
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default="System")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification to {self.user.username} ({self.status})"

