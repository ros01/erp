# applications/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import VisaApplication
from documents.models import DocumentRequirement, Document

@receiver(post_save, sender=VisaApplication)
def create_document_checklist(sender, instance, created, **kwargs):
    if created:
        requirements = DocumentRequirement.objects.filter(
            country=instance.country,
            visa_type=instance.visa_type
        )
        docs = [
            Document(application=instance, requirement=req)
            for req in requirements
        ]
        Document.objects.bulk_create(docs)
