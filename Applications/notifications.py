from django.core.mail import send_mail
from django.conf import settings
import logging
logger = logging.getLogger(__name__)



def send_email(subject, message, recipient):
    # 🔕 TEMPORARY: email notifications are switched off system-wide via
    # settings.EMAIL_NOTIFICATIONS_ENABLED while the sendgrid.net account
    # is inactive (was causing lags on every action that sends a client
    # notification). Every notify_* function below funnels through this
    # one wrapper, so this is the single place that needs flipping back
    # (set EMAIL_NOTIFICATIONS_ENABLED = True in erp/settings.py) once a
    # working email service is in place.
    if not getattr(settings, "EMAIL_NOTIFICATIONS_ENABLED", True):
        logger.info(
            f"Email notifications disabled - skipped '{subject}' to {recipient}"
        )
        return

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

    # ✅ Routed through send_email() so this also honors
    # settings.EMAIL_NOTIFICATIONS_ENABLED, same as every other notify_*.
    send_email(
        "Visa Application Stage Updated",
        (
            f"Dear {user.get_full_name},\n\n"
            f"Your visa application has progressed to the "
            f"{application.stage} stage.\n\n"
            "Please log in to continue."
        ),
        user.email,
    )


def notify_application_completed(application):
    user = application.client.user

    print("📧 notify_application_completed CALLED")

    # ✅ Routed through send_email() so this also honors
    # settings.EMAIL_NOTIFICATIONS_ENABLED, same as every other notify_*.
    send_email(
        "Visa Documents Completed",
        (
            f"Dear {user.get_full_name},\n\n"
            "Your student visa document upload is complete.\n"
            "Your application has now been assigned to a case officer."
        ),
        user.email,
    )


def notify_visa_decision(application):
    user = application.client.user
    decision = application.status

    if decision == "APPROVED":
        subject = "🎉 Visa Application Approved"
        message = f"""
Dear {user.get_full_name},

Congratulations!

Your visa application has been APPROVED.

Reference No: {application.reference_no}
Country: {application.get_country_display()}
Visa Type: {application.get_visa_type_display()}

We will guide you through the next steps.

— Suave ERP
"""
    else:  # REJECTED
        subject = "Visa Application Decision Update"
        message = f"""
Dear {user.get_full_name},

We regret to inform you that your visa application has been REJECTED.

Reference No: {application.reference_no}
Country: {application.get_country_display()}
Visa Type: {application.get_visa_type_display()}

Please review the refusal letter(s) uploaded by the officer.

— Suave ERP
"""

    send_email(subject, message, user.email)
