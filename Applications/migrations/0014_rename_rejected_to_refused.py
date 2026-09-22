"""
Rename the "REJECTED"/"Rejected" visa-application decision status to
"REFUSED"/"Refused", to match UK Home Office terminology (consistent
with the "refusal letter" rename applied in 0013_refusalletter_and_more.py).

Scope note (per explicit product decision): this migration intentionally
touches ONLY the VisaApplication.status choice/value and the legacy,
unused Decision.decision_status choice/value. The following "REJECTED"
status values are separate, legitimate concepts on unrelated models and
are deliberately LEFT UNTOUCHED by this migration:
  - Document.status ("REJECTED" as a document-review outcome)
  - AdmissionApplication.status ("REJECTED" as an admission-pipeline outcome)
  - CASApplication.status ("REJECTED" as a CAS-pipeline outcome)

This migration both updates the field choices metadata (AlterField) and
converts any existing rows still storing the old value (RunPython data
migration), and is written to be reversible.
"""

from django.db import migrations, models


def rejected_to_refused(apps, schema_editor):
    VisaApplication = apps.get_model("Applications", "VisaApplication")
    VisaApplication.objects.filter(status="REJECTED").update(status="REFUSED")

    Decision = apps.get_model("Applications", "Decision")
    Decision.objects.filter(decision_status="Rejected").update(decision_status="Refused")


def refused_to_rejected(apps, schema_editor):
    VisaApplication = apps.get_model("Applications", "VisaApplication")
    VisaApplication.objects.filter(status="REFUSED").update(status="REJECTED")

    Decision = apps.get_model("Applications", "Decision")
    Decision.objects.filter(decision_status="Refused").update(decision_status="Rejected")


class Migration(migrations.Migration):

    dependencies = [
        ("Applications", "0013_refusalletter_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="visaapplication",
            name="status",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("QUEUED", "Queued"),
                    ("INITIATED", "Initiated by Officer"),
                    ("ASSIGNED", "Assigned to Officer"),
                    ("REVIEWED", "Reviewed"),
                    ("FORM FILLED", "Form Filled"),
                    ("ADMIN REVIEW", "Admin Review"),
                    ("SUBMITTED", "Awaiting Embassy Decision"),
                    ("APPROVED", "Approved"),
                    ("REFUSED", "Refused"),
                ],
                default="QUEUED",
            ),
        ),
        migrations.AlterField(
            model_name="decision",
            name="decision_status",
            field=models.CharField(
                max_length=50,
                choices=[
                    ("Approved", "Approved"),
                    ("Refused", "Refused"),
                    ("Pending", "Pending"),
                ],
            ),
        ),
        migrations.RunPython(rejected_to_refused, refused_to_rejected),
    ]
