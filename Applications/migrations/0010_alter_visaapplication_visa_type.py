from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Applications', '0009_rejectionletter'),
    ]

    operations = [
        migrations.AlterField(
            model_name='visaapplication',
            name='visa_type',
            field=models.CharField(choices=[('TOURIST - EMPLOYED', 'Tourist Visa - Employed'), ('TOURIST - SELF EMPLOYED', 'Tourist Visa - Self Employed'), ('STUDENT', 'Student Visa'), ('CHILD STUDENT', 'Child Student Visa'), ('WORK', 'Work Visa'), ('BUSINESS', 'Business Visa'), ('TRANSIT', 'Transit Visa'), ('RESIDENCY', 'Residency / PR'), ('DIPLOMATIC', 'Diplomatic Visa'), ('OTHER', 'Other')], default='OTHER', max_length=50),
        ),
    ]
