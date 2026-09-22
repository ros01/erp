"""
Add reviewed_at / admin_review_sent_at timestamps to VisaApplication.

These back the Case Officer dashboard's "Activity" timeline, which needs
a real event date for the REVIEWED and ADMIN REVIEW status transitions.
updated_at (auto_now) can't be used for this: both transitions save via
.save(update_fields=[...]) without "updated_at" in that list, so it is
never refreshed by them - see Applications.api_views.DocumentReviewAPIView
and Applications.serializers.VisaApplicationUrlUpdateSerializer(000).
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Applications", "0014_rename_rejected_to_refused"),
    ]

    operations = [
        migrations.AddField(
            model_name="visaapplication",
            name="reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="visaapplication",
            name="admin_review_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
