from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, StaffProfile

@receiver(post_save, sender=User)
def create_staff_profile(sender, instance, created, **kwargs):
    """
    Automatically create a StaffProfile for non-client users.
    """
    if created and instance.role != "Client":
        StaffProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_staff_profile(sender, instance, **kwargs):
    """
    Ensure StaffProfile is always saved when User is updated.
    """
    if instance.role != "Client":
        StaffProfile.objects.get_or_create(user=instance)
        instance.staff_profile.save()
