# applications/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import VisaApplication
from Documents.models import DocumentRequirement, Document
from django.db.models import Count, Q
from Accounts.models import StaffProfile
from CaseManagement.models import TaskAssignment
from django.conf import settings
from django.utils import timezone
from django.db.models import Count


# from django.utils.log import getLogger
import logging

logger = logging.getLogger(__name__)



# logger = getLogger(__name__)

DEFAULT_QUEUE_USERNAME = "default.queue"


@receiver(post_save, sender=Document)
def check_and_assign_officer(sender, instance, created, **kwargs):
    """
    When a Document is uploaded/updated:
    If the parent VisaApplication now has ALL mandatory documents uploaded,
    auto-assign a Case Officer (if not already assigned).
    """
    application = instance.application

    # Already assigned → skip
    if application.assigned_officer or application.status != "QUEUED":
        return

    # ✅ Get all mandatory requirements for this visa type + country
    mandatory_requirements = DocumentRequirement.objects.filter(
        country=application.country,
        visa_type=application.visa_type,
        is_mandatory=True,
    )

    # ✅ Ensure each mandatory requirement has a non-MISSING Document
    for req in mandatory_requirements:
        doc = application.documents.filter(requirement=req).first()
        if not doc or doc.status == "MISSING":
            return  # still incomplete → abort

    # ✅ All requirements satisfied → assign officer
    officers = (
        StaffProfile.objects.filter(user__role="Case Officer", is_available=True)
        .annotate(num_apps=Count("tasks"))
        .order_by("workload", "id")
    )

    if officers.exists():
        officer = officers.first()
        application.assigned_officer = officer
        application.status = "ASSIGNED"
        application.save(update_fields=["assigned_officer", "status"])

        officer.workload = officer.workload + 1
        officer.save(update_fields=["workload"])

        TaskAssignment.objects.create(
            application=application,
            assigned_to=officer,
            status="Assigned",
            description=f"Auto-assigned task for application {application.reference_no}",
        )


@receiver(post_save, sender=VisaApplication)
def auto_assign_officer(sender, instance, created, **kwargs):
    """
    Auto-assign least busy Case Officer when a Client completes all mandatory docs.
    OR
    If created directly by a Case Officer with status 'INITIATED',
    record creator, update workload, and create TaskAssignment
    (without treating it as auto-assigned).
    """

    # 🔹 Don't run if not newly created or task already exists
    if not created or hasattr(instance, "task"):
        return

    # 🔹 Case 1: Application created directly by a Case Officer
    if instance.status == "INITIATED":
        officer = instance.created_by_officer

        # ✅ Explicitly track initiator
        if not instance.created_by_officer:
            instance.created_by_officer = officer
            instance.save(update_fields=["created_by_officer"])

        # ✅ Update workload
        officer.workload = officer.workload + 1
        officer.save(update_fields=["workload"])

        # ✅ Create TaskAssignment (initiated, not auto-assigned)
        TaskAssignment.objects.create(
            application=instance,
            assigned_to=officer,
            status="Assigned",
            description=f"Task for application {instance.reference_no} (initiated by Case Officer)",
        )
        return

    # 🔹 Case 2: Application created by Client (check mandatory requirements)
    mandatory_requirements = DocumentRequirement.objects.filter(
        country=instance.country,
        visa_type=instance.visa_type,
        is_mandatory=True,
    )

    for req in mandatory_requirements:
        doc = instance.documents.filter(requirement=req).first()
        if not doc or doc.status == "MISSING":
            return  # stop until all mandatory docs uploaded

    # 🔹 Auto-assign least busy officer (only if no creator officer)
    officers = (
        StaffProfile.objects.filter(user__role="Case Officer", is_available=True)
        .annotate(num_apps=Count("assigned_applications"))
        .order_by("workload", "id")
    )

    if officers.exists():
        officer = officers.first()

        # ✅ Mark as auto-assigned
        instance.assigned_officer = officer
        instance.status = "ASSIGNED"
        instance.save(update_fields=["assigned_officer", "status"])

        # ✅ Update workload
        officer.workload = officer.workload + 1
        officer.save(update_fields=["workload"])

        # ✅ Create TaskAssignment (auto-assigned)
        TaskAssignment.objects.create(
            application=instance,
            assigned_to=officer,
            status="Assigned",
            description=f"Auto-assigned task for application {instance.reference_no}",
        )






# @receiver(post_save, sender=VisaApplication)
# def auto_assign_officer(sender, instance, created, **kwargs):
#     """
#     Auto-assign least busy Case Officer when a Client completes all mandatory docs.
#     OR
#     If created directly by a Case Officer with status 'INITIATED',
#     update workload and create TaskAssignment immediately (without reassign).
#     """
#     if not created or hasattr(instance, "task"):
#         return

#     # 🔹 Case 1: Application created directly by a Case Officer with INITIATED status
#     if instance.status == "INITIATED" and instance.assigned_officer:
#         officer = instance.assigned_officer

#         # ✅ Update workload
#         officer.workload = officer.workload + 1
#         officer.save(update_fields=["workload"])

#         # ✅ Create TaskAssignment (do not reassign officer)
#         TaskAssignment.objects.create(
#             application=instance,
#             assigned_to=officer,
#             status="Assigned",
#             description=f"Task for application {instance.reference_no} (initiated by Case Officer)",
#         )
#         return

#     # 🔹 Case 2: Client-created application (must check mandatory requirements)
#     mandatory_requirements = DocumentRequirement.objects.filter(
#         country=instance.country,
#         visa_type=instance.visa_type,
#         is_mandatory=True,
#     )

#     for req in mandatory_requirements:
#         doc = instance.documents.filter(requirement=req).first()
#         if not doc or doc.status == "MISSING":
#             return  # stop until all mandatory docs uploaded

#     officers = (
#         StaffProfile.objects.filter(user__role="Case Officer", is_available=True)
#         .annotate(num_apps=Count("assigned_applications"))
#         .order_by("workload", "id")
#     )

#     if officers.exists():
#         officer = officers.first()
#         instance.assigned_officer = officer
#         instance.status = "ASSIGNED"
#         instance.save(update_fields=["assigned_officer", "status"])

#         officer.workload = officer.workload + 1
#         officer.save(update_fields=["workload"])

#         TaskAssignment.objects.create(
#             application=instance,
#             assigned_to=officer,
#             status="Assigned",
#             description=f"Auto-assigned task for application {instance.reference_no}",
#         )

# @receiver(post_save, sender=VisaApplication)
# def auto_assign_officer(sender, instance, created, **kwargs):
#     """
#     Auto-assign least busy Case Officer when a Client completes all mandatory docs.
#     OR
#     If created directly by a Case Officer with status 'INITIATED',
#     update workload and create TaskAssignment immediately.
#     """
#     if not created or hasattr(instance, "task"):
#         return

#     # 🔹 Case 1: Application created directly by Case Officer with INITIATED status
#     if instance.status == "INITIATED" and instance.assigned_officer:
#         officer = instance.assigned_officer
#         officer.workload += 1
#         officer.save(update_fields=["workload"])

#         TaskAssignment.objects.create(
#             application=instance,
#             assigned_to=officer,
#             status="Assigned",
#             description=f"Task for application {instance.reference_no} (initiated by Case Officer)",
#         )
#         return


#     # 🔹 Case 2: Client-created application (must check mandatory requirements)
#     mandatory_requirements = DocumentRequirement.objects.filter(
#         country=instance.country,
#         visa_type=instance.visa_type,
#         is_mandatory=True,
#     )

#     for req in mandatory_requirements:
#         doc = instance.documents.filter(requirement=req).first()
#         if not doc or doc.status == "MISSING":
#             return  # stop until all docs uploaded

#     officers = (
#         StaffProfile.objects.filter(user__role="Case Officer", is_available=True)
#         .annotate(num_apps=Count("tasks"))
#         .order_by("workload", "id")
#     )

#     if officers.exists():
#         officer = officers.first()
#         instance.assigned_officer = officer
#         instance.status = "ASSIGNED"
#         instance.save(update_fields=["assigned_officer", "status"])

#         officer.workload = officer.workload + 1
#         officer.save(update_fields=["workload"])

#         TaskAssignment.objects.create(
#             application=instance,
#             assigned_to=officer,
#             status="Assigned",
#             description=f"Auto-assigned task for application {instance.reference_no}",
#         )


# @receiver(post_save, sender=VisaApplication)
# def auto_assign_officer(sender, instance, created, **kwargs):
    """
    Auto-assign least busy Case Officer, update workload,
    and create TaskAssignment when a new VisaApplication is created.
    Only runs when ALL mandatory DocumentRequirements for this visa type & country
    are satisfied (i.e. corresponding Document exists and is not MISSING).
    """
    # if not created or hasattr(instance, "task"):
    #     return

    # # ✅ Get all mandatory requirements for this visa type + country
    # mandatory_requirements = DocumentRequirement.objects.filter(
    #     country=instance.country,
    #     visa_type=instance.visa_type,
    #     is_mandatory=True,
    # )

    # # ✅ Check each mandatory requirement has a corresponding uploaded document
    # for req in mandatory_requirements:
    #     doc = instance.documents.filter(requirement=req).first()
    #     if not doc or doc.status == "MISSING":
    #         # Abort auto-assignment until all mandatory docs are uploaded
    #         return

    # # ✅ If we reach here → all requirements are satisfied
    # officers = (
    #     StaffProfile.objects.filter(user__role="Case Officer", is_available=True)
    #     .annotate(num_apps=Count("tasks"))
    #     .order_by("workload", "id")
    # )

    # if officers.exists():
    #     officer = officers.first()
    #     instance.assigned_officer = officer
    #     instance.status = "ASSIGNED"   # ✅ now safe to assign
    #     instance.save(update_fields=["assigned_officer", "status"])

    #     officer.workload = officer.workload + 1
    #     officer.save(update_fields=["workload"])

    #     TaskAssignment.objects.create(
    #         application=instance,
    #         assigned_to=officer,
    #         status="Assigned",
    #         description=f"Auto-assigned task for application {instance.reference_no}",
    #     )




# @receiver(post_save, sender=VisaApplication)
# def auto_assign_officer(sender, instance, created, **kwargs):
#     """
#     Auto-assign least busy Case Officer, update workload,
#     and create TaskAssignment when a new VisaApplication is created.
#     Also update the application status to 'ASSIGNED',
#     but only if all mandatory documents are uploaded.
#     """
#     if not created or hasattr(instance, "task"):
#         return

#     # ✅ Check if all mandatory documents have been uploaded (not MISSING)
#     missing_required_docs = instance.documents.filter(
#         requirement__is_mandatory=True,
#         status="MISSING"
#     ).exists()

#     if missing_required_docs:
#         # Abort auto-assignment until documents are ready
#         return

#     officers = (
#         StaffProfile.objects.filter(user__role="Case Officer", is_available=True)
#         .annotate(num_apps=Count("tasks"))
#         .order_by("workload", "id")
#     )

#     if officers.exists():
#         officer = officers.first()
#         instance.assigned_officer = officer
#         instance.status = "ASSIGNED"   # ✅ update status only when requirements are satisfied
#         instance.save(update_fields=["assigned_officer", "status"])

#         officer.workload = officer.workload + 1
#         officer.save(update_fields=["workload"])

#         TaskAssignment.objects.create(
#             application=instance,
#             assigned_to=officer,
#             status="Assigned",
#             description=f"Auto-assigned task for application {instance.reference_no}",
#         )



# @receiver(post_save, sender=VisaApplication)
# def auto_assign_officer(sender, instance, created, **kwargs):
#     """
#     Auto-assign least busy Case Officer, update workload,
#     and create TaskAssignment when a new VisaApplication is created.
#     Also update the application status to 'ASSIGNED'.
#     """
#     if not created or hasattr(instance, "task"):
#         return

#     officers = (
#         StaffProfile.objects.filter(user__role="Case Officer", is_available=True)
#         .annotate(num_apps=Count("tasks"))
#         .order_by("workload", "id")
#     )

#     if officers.exists():
#         officer = officers.first()
#         instance.assigned_officer = officer
#         instance.status = "ASSIGNED"   # ✅ update status here
#         instance.save(update_fields=["assigned_officer", "status"])

#         officer.workload = officer.workload + 1
#         officer.save(update_fields=["workload"])

#         TaskAssignment.objects.create(
#             application=instance,
#             assigned_to=officer,
#             status="Assigned",
#             description=f"Auto-assigned task for application {instance.reference_no}",
#         )


# @receiver(post_save, sender=VisaApplication)
# def auto_assign_officer(sender, instance, created, **kwargs):
#     """
#     Auto-assign least busy Case Officer, update workload,
#     and create TaskAssignment when a new VisaApplication is created.
#     """
#     if not created or hasattr(instance, "task"):
#         return

#     officers = (
#         StaffProfile.objects.filter(user__role="Case Officer", is_available=True)
#         .annotate(num_apps=Count("tasks"))
#         .order_by("workload", "id")
#     )

#     if officers.exists():
#         officer = officers.first()
#         instance.assigned_officer = officer
#         instance.save(update_fields=["assigned_officer"])

#         officer.workload = officer.workload + 1
#         officer.save(update_fields=["workload"])

#         TaskAssignment.objects.create(
#             application=instance,
#             assigned_to=officer,
#             status="Assigned",
#             description=f"Auto-assigned task for application {instance.reference_no}",
#         )


@receiver(post_delete, sender=VisaApplication)
def decrement_workload_on_app_delete(sender, instance, **kwargs):
    """
    If application is deleted → decrement officer workload
    but keep TaskAssignment record intact (historical log).
    """
    officer = getattr(instance, "assigned_officer", None)
    if officer and officer.workload > 0:
        officer.workload -= 1
        officer.save(update_fields=["workload"])


@receiver(post_save, sender=TaskAssignment)
def handle_task_completion(sender, instance, **kwargs):
    """
    If a TaskAssignment is marked as completed → decrement workload,
    but do not delete TaskAssignment.
    """
    if instance.status == "Completed" and not instance.completed:
        instance.completed = True
        instance.save(update_fields=["completed"])

        officer = instance.assigned_to
        if officer and officer.workload > 0:
            officer.workload -= 1
            officer.save(update_fields=["workload"])



# @receiver(post_save, sender=VisaApplication)
# def auto_assign_officer(sender, instance, created, **kwargs):
#     """
#     Auto-assign least busy Case Officer, update workload, 
#     and log TaskAssignment when a new VisaApplication is created.
#     """
#     if not created or instance.assigned_officer:  
#         # Skip updates or already assigned
#         return

#     # Get available officers with count of applications
#     officers = (
#         StaffProfile.objects.filter(user__role="Case Officer", is_available=True)
#         .annotate(num_apps=Count("assigned_applications"))
#         .order_by("num_apps", "id")
#     )

#     if officers.exists():
#         officer = officers.first()

#         # Assign officer
#         instance.assigned_officer = officer
#         instance.save(update_fields=["assigned_officer"])

#         # Increment workload
#         officer.workload = officer.workload + 1
#         officer.save(update_fields=["workload"])

#         # Create TaskAssignment record
#         TaskAssignment.objects.create(
#             assigned_to=officer,
#             application=instance
#         )





# @receiver(post_save, sender=VisaApplication)
# def auto_assign_officer(sender, instance, created, **kwargs):
#     """
#     Automatically assign the least-busy available Case Officer
#     whenever a new VisaApplication is created.
#     """
#     if not created:  # only assign when first created
#         return

#     # Get available case officers
#     officers = (
#         StaffProfile.objects.filter(user__role="Case Officer", is_available=True)
#         .annotate(num_apps=Count("assigned_applications"))
#         .order_by("num_apps")  # least busy first
#     )

#     if officers.exists():
#         officer = officers.first()
#         instance.assigned_officer = officer
#         instance.save(update_fields=["assigned_officer"])


# @receiver(post_save, sender=VisaApplication)
# def auto_assign_officer(sender, instance, created, **kwargs):
#     """
#     Automatically assign a case officer with the least workload
#     when a new VisaApplication is created.
#     Fallback → assign to 'Default Queue' user if no officers available.
#     """
#     if created and instance.assigned_officer is None:
#         officers = StaffProfile.objects.filter(user__role="Case Officer", is_available=True)
#         officers = officers.annotate(num_apps=Count("assigned_applications")).order_by("num_apps")

#         if officers.exists():
#             # Assign to least busy officer
#             instance.assigned_officer = officers.first()
#             instance.save(update_fields=["assigned_officer"])
#         else:
#             try:
#                 # Assign to fallback "default.queue" staff profile
#                 default_user = StaffProfile.objects.get(user__email=DEFAULT_QUEUE_USERNAME)
#                 instance.assigned_officer = default_user
#                 instance.save(update_fields=["assigned_officer"])
#                 logger.warning(f"Application {instance.reference_no} assigned to Default Queue.")
#             except StaffProfile.DoesNotExist:
#                 # No fallback user, leave unassigned
#                 logger.error(
#                     f"No available officers and no Default Queue user. "
#                     f"Application {instance.reference_no} left unassigned."
#                 )



# Behavior
# If officers exist → assign least busy officer.
# If no officers exist → assign "default.queue".
# If even that fails → leave unassigned & log error.

# @receiver(post_save, sender=VisaApplication)
# def auto_assign_officer(sender, instance, created, **kwargs):
#     """
#     Automatically assign a case officer with the least workload
#     when a new VisaApplication is created.
#     """
#     if created and instance.assigned_officer is None:
#         officers = StaffProfile.objects.filter(role="CaseOfficer", is_active=True) \
#             .annotate(open_cases=Count(
#                 "assigned_applications",
#                 filter=~Q(assigned_applications__status="completed")
#             )) \
#             .order_by("open_cases")

#         if officers.exists():
#             instance.assigned_officer = officers.first()
#             instance.save(update_fields=["assigned_officer"])


# Behavior
# When a new VisaApplication is created:
# The signal runs.
# Finds all active staff with role="CaseOfficer".
# Assigns the one with the fewest open (non-completed) cases.
# Saves the assignment automatically.

# @receiver(post_save, sender=VisaApplication)
# def create_document_checklist(sender, instance, created, **kwargs):
#     if created:
#         requirements = DocumentRequirement.objects.filter(
#             country=instance.country,
#             visa_type=instance.visa_type
#         )
#         docs = [
#             Document(application=instance, requirement=req)
#             for req in requirements
#         ]
#         Document.objects.bulk_create(docs)
