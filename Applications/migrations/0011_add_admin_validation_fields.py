# Adds the Admin-validation gate for auto-assigned applications:
#   - admin_validated: False while a Case Officer's auto-assignment is
#     awaiting Admin sign-off. Only meaningful while status == "ASSIGNED".
#   - validated_by / validated_at: who validated (or reassigned) it, and
#     when - set by Applications.api_views.ValidateApplicationAssignmentAPIView
#     and ReassignApplicationOfficerAPIView.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Accounts", "0001_initial"),
        ("Applications", "0010_alter_visaapplication_visa_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="visaapplication",
            name="admin_validated",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="visaapplication",
            name="validated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="visaapplication",
            name="validated_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="validated_applications",
                to="Accounts.staffprofile",
            ),
        ),
    ]
