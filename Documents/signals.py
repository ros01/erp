from django.db.models.signals import post_save
from django.dispatch import receiver
from Applications.models import VisaApplication
from .models import DocumentRequirement, Document


# @receiver(post_save, sender=VisaApplication)
# def create_required_documents(sender, instance, created, **kwargs):
#     """
#     When a new VisaApplication is created, auto-generate required
#     Document slots based on DocumentRequirement for that country & visa_type.
#     """
#     if created:
#         requirements = DocumentRequirement.objects.filter(
#             country=instance.country,
#             visa_type=instance.visa_type
#         )

#         for req in requirements:
#             Document.objects.get_or_create(
#                 application=instance,
#                 requirement=req,
#                 defaults={"status": "Missing"}
#             )
