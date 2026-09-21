# Renames the decision-time "rejection letter" concept to "refusal letter"
# throughout the codebase. This is a true rename (RenameModel + AlterField),
# not a drop/recreate, so existing RejectionLetter rows and their uploaded
# files are preserved under the new RefusalLetter model.
#
# Also removes VisaApplication.rejection_letter - a dead single-file field
# that was never wired into any live view (superseded by the
# RejectionLetter/RefusalLetter related model, which supports multiple
# letters per application).
#
# The "REJECTED" status/decision value on VisaApplication is a separate,
# legitimate concept and is intentionally left untouched by this migration.
#
# Not to be confused with the pre-existing, unrelated PreviousRefusalLetter
# model (a client's history of past refusals from other visa applications),
# whose related_name="refusal_letters" already occupied the plural form -
# hence RefusalLetter uses the singular related_name="refusal_letter".

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('Applications', '0012_add_client_notified_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='visaapplication',
            name='rejection_letter',
        ),
        migrations.RenameModel(
            old_name='RejectionLetter',
            new_name='RefusalLetter',
        ),
        migrations.AlterField(
            model_name='refusalletter',
            name='application',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='refusal_letter', to='Applications.visaapplication'),
        ),
        migrations.AlterField(
            model_name='refusalletter',
            name='file',
            field=models.FileField(upload_to='refusal_letter/'),
        ),
    ]
