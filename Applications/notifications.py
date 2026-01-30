from django.core.mail import send_mail
from django.conf import settings
import logging
logger = logging.getLogger(__name__)



def send_email(subject, message, recipient):
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [recipient],
        fail_silently=False,
    )



def notify_stage_advanced(application):
    user = application.client.user

    subject = "Visa Application Stage Updated"
    message = f"""
Dear {user.get_full_name},

Your visa application ({application.reference_no}) has progressed.

Current Stage: {application.stage}
Progress: {application.progress}%

Kindly complete upload of remaining required documents for your visa application.
"""

    send_email(subject, message, user.email)


def notify_final_completion(application):
    user = application.client.user

    subject = "🎉 Visa Application Documents Completed"
    message = f"""
Dear {user.get_full_name},

Congratulations!

You have successfully completed ALL required documents for your
{application.visa_type} visa application.

Reference No: {application.reference_no}

✅ Status: Assigned to a Case Officer
📌 Next step: Review & submission

You will be contacted shortly.

— Suave ERP
"""

    send_email(subject, message, user.email)




def notify_next_stage_advanced(application):
    user = application.client.user

    print("📧 notify_stage_advanced CALLED")

    send_mail(
        subject="Visa Application Stage Updated",
        message=(
            f"Dear {user.get_full_name},\n\n"
            f"Your visa application has progressed to the "
            f"{application.stage} stage.\n\n"
            "Please log in to continue."
        ),
        from_email=None,
        recipient_list=[user.email],
        fail_silently=False,
    )


def notify_application_completed(application):
    user = application.client.user

    print("📧 notify_application_completed CALLED")

    send_mail(
        subject="Visa Documents Completed",
        message=(
            f"Dear {user.get_full_name},\n\n"
            "Your student visa document upload is complete.\n"
            "Your application has now been assigned to a case officer."
        ),
        from_email=None,
        recipient_list=[user.email],
        fail_silently=False,
    )
