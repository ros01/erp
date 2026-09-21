# Data migration:
#   Adds the new UK "Child Student" visa document requirement checklist.
#   This is a brand-new (country, visa_type) combination - no existing
#   DocumentRequirement rows exist for it yet, so this is purely additive
#   (nothing is deleted, nothing cascades to existing Document rows).
#   UK's StageDefinition (ADMISSION -> VISA) already exists from the prior
#   Student-visa seeding, so no StageDefinition changes are needed here.

from django.db import migrations


# ---------------------------------------------------------------------------
# UK "Child Student" - a flat checklist (no admission/visa split in the
# source list), so it is stored under the VISA stage, matching the same
# convention used for Canada "Child Student" (see migration 0012). This
# visa type is not part of Applications.services' STUDENT staged-flow
# group, so it uses the flat all-documents completion flow - which stage
# the rows carry has no functional effect.
# ---------------------------------------------------------------------------
UK_CHILD_STUDENT_DOCUMENTS = [
    ("Birth Certificate", "", "IDENTITY", True),
    ("CAS", "", "ADMISSION", True),
    ("TB Test", "", "OTHER", True),
    ("Guardian or Non-Guardian Support Letter", "", "FAMILY", True),
    ("Guardian Data Page", "", "FAMILY", True),
    ("International Passport", "", "IDENTITY", True),
    ("Previous Travels", "", "OTHER", True),
    ("Parental Consent Letter", "", "FAMILY", True),
    ("Authorization to Use Bank Statement", "", "FINANCIAL", True),
    ("Sponsor Financial Evidence", "", "FINANCIAL", True),
    ("Parents' Data and Visa Pages", "", "FAMILY", True),
    ("Consent Letter", "", "FAMILY", True),
    ("Offer Letter", "", "ADMISSION", True),
    ("Introduction Letter/Sponsorship Letter", "", "FAMILY", True),
    ("Study Permit Form", "", "ADMISSION", True),
    ("Family Information Form", "", "FAMILY", True),
    ("Temporary Residence Form", "", "ADMISSION", True),
    ("Additional Information Form", "", "ADMISSION", True),
]

REQUIREMENTS_BY_COUNTRY = {
    ("UK", "CHILD STUDENT"): {
        "VISA": UK_CHILD_STUDENT_DOCUMENTS,
    },
}


def add_requirements(apps, schema_editor):
    DocumentRequirement = apps.get_model("Documents", "DocumentRequirement")

    for (country, visa_type), stages in REQUIREMENTS_BY_COUNTRY.items():
        # Idempotent/re-runnable: wipe whatever exists for this
        # country/visa_type today (should be nothing, since it's new) and
        # recreate from the canonical list, same convention as migration 0012.
        DocumentRequirement.objects.filter(country=country, visa_type=visa_type).delete()

        for stage, documents in stages.items():
            for name, description, category, is_mandatory in documents:
                DocumentRequirement.objects.create(
                    country=country,
                    visa_type=visa_type,
                    stage=stage,
                    name=name,
                    description=description,
                    category=category,
                    is_mandatory=is_mandatory,
                )


def reverse_add_requirements(apps, schema_editor):
    DocumentRequirement = apps.get_model("Documents", "DocumentRequirement")
    for country, visa_type in REQUIREMENTS_BY_COUNTRY:
        DocumentRequirement.objects.filter(country=country, visa_type=visa_type).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("Documents", "0012_amend_student_and_add_child_student_requirements"),
    ]

    operations = [
        migrations.RunPython(add_requirements, reverse_add_requirements),
    ]
