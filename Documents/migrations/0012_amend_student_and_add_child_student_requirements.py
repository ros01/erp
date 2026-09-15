# Data migration:
#   1. Collapses the UK CAS stage into VISA in StageDefinition (all three
#      student-visa countries now share the same ADMISSION -> VISA pipeline).
#   2. Replaces the old generic Canada/UK Student document requirements with
#      the client's amended checklists (stale items are deleted outright,
#      per instruction - any Document already uploaded against a deleted
#      requirement is cascade-deleted along with it).
#   3. Adds the new Canada "Child Student" requirement checklist.

from django.db import migrations


# ---------------------------------------------------------------------------
# StageDefinition: UK's CAS stage is collapsed - every student-visa country
# now runs ADMISSION (1) -> VISA (2).
# ---------------------------------------------------------------------------
STAGE_SEQUENCE = {
    "UK": ["ADMISSION", "VISA"],
    "CANADA": ["ADMISSION", "VISA"],
    "USA": ["ADMISSION", "VISA"],
}


# ---------------------------------------------------------------------------
# Document requirements. (name, description, category, is_mandatory)
# ---------------------------------------------------------------------------
ADMISSION_DOCUMENTS = [
    ("International Passport", "Bio-data page showing photo and personal details.", "IDENTITY", True),
    ("Academic Qualifications", "Degree certificates and academic transcripts.", "ADMISSION", True),
    ("Curriculum Vitae (CV)", "Detailed resume.", "ADMISSION", True),
    ("Statement of Purpose (SOP)", "Personal goals and study motivation essay.", "ADMISSION", True),
    ("Reference Letters", "Academic or professional recommendation letters.", "ADMISSION", True),
    ("English Language Proof", "Recognized English test certificate or WAEC (minimum C6–C4) Or IELTS.", "ADMISSION", True),
    ("Supplementary University Information Form", "", "ADMISSION", True),
    ("Required Information PDF Form", "", "ADMISSION", True),
]

CANADA_STUDENT_VISA_DOCUMENTS = [
    ("Valid International Passport", "Current and valid passport.", "IDENTITY", True),
    ("Unconditional Offer Letter", "Official university acceptance letter.", "ADMISSION", True),
    ("PAL Letter", "With official university PAL number.", "ADMISSION", True),
    ("PAL Payment Receipt", "Proof of PAL payment.", "FINANCIAL", True),
    ("Visa Application Form", "Copy of submitted online visa application.", "OTHER", True),
    ("Passport Photograph", "Recent passport photographs meeting embassy requirements.", "IDENTITY", True),
    ("Proof of Funds", "28-day bank statements.", "FINANCIAL", True),
    ("Sponsor Documents", "Sponsor's identification and financial support documents.", "FAMILY", True),
    ("Tuition Fee Payment Proof", "Evidence of tuition fee payment.", "FINANCIAL", True),
    ("TB Test Certificate", "Approved tuberculosis clearance certificate.", "OTHER", True),
    ("Travel History", "Previous visas and entry/exit stamps.", "OTHER", True),
]

# UK's VISA stage now also carries the CAS letter - the CAS stage itself
# has been collapsed away.
UK_STUDENT_VISA_DOCUMENTS = [
    ("Valid International Passport", "Current and valid passport.", "IDENTITY", True),
    ("Unconditional Offer Letter", "Official university acceptance letter.", "ADMISSION", True),
    ("Visa Application Form", "Copy of submitted online visa application.", "OTHER", True),
    ("Proof of Funds", "28-day bank statements.", "FINANCIAL", True),
    ("Sponsor Documents", "Sponsor's identification and financial support documents.", "FAMILY", True),
    ("Tuition Fee Payment Proof", "Evidence of tuition fee payment.", "FINANCIAL", True),
    ("TB Test Certificate", "Approved tuberculosis clearance certificate.", "OTHER", True),
    ("Travel History", "Previous visas and entry/exit stamps.", "OTHER", True),
    ("CAS Letter", "", "ADMISSION", True),
]

# Canada "Child Student" - a flat checklist (no admission/visa split), so it
# is stored under the VISA stage. This visa type isn't in the STUDENT stage
# group in Applications.services, so it uses the flat all-documents
# completion flow rather than the staged one - which stage the rows carry
# has no functional effect, VISA was picked for consistency with the main
# Student checklist's visa-stage documents.
CANADA_CHILD_STUDENT_DOCUMENTS = [
    ("Birth Certificate", "", "IDENTITY", True),
    ("Digital Photo", "", "IDENTITY", True),
    ("Letter of Acceptance", "", "ADMISSION", True),
    ("PAL / Exemption Letter", "", "ADMISSION", True),
    ("Medical Results", "IOM", "OTHER", True),
    ("Guardian or Non-Guardian Support Letter", "", "FAMILY", True),
    ("International Passport", "", "IDENTITY", True),
    ("Previous Travel Details", "", "OTHER", True),
    ("Parental Consent Letter", "", "FAMILY", True),
    ("Authorization to Use Bank Statement", "", "FINANCIAL", True),
    ("Financial Evidence", "", "FINANCIAL", True),
    ("Parents' Data and Visa Pages", "", "FAMILY", True),
    ("Sponsorship Letter, Family Evidence, Employment", "", "FAMILY", True),
    ("Affidavit of Sponsorship", "", "FAMILY", True),
    ("Study Permit Form", "", "ADMISSION", True),
    ("Family Information Form", "", "FAMILY", True),
    ("Temporary Residence Form", "", "ADMISSION", True),
    ("Required Information PDF Form", "", "ADMISSION", True),
]

# (country, visa_type) -> {stage: [documents]}
REQUIREMENTS_BY_COUNTRY = {
    ("CANADA", "STUDENT"): {
        "ADMISSION": ADMISSION_DOCUMENTS,
        "VISA": CANADA_STUDENT_VISA_DOCUMENTS,
    },
    ("UK", "STUDENT"): {
        "ADMISSION": ADMISSION_DOCUMENTS,
        "VISA": UK_STUDENT_VISA_DOCUMENTS,
    },
    ("CANADA", "CHILD STUDENT"): {
        "VISA": CANADA_CHILD_STUDENT_DOCUMENTS,
    },
}


def amend_requirements(apps, schema_editor):
    StageDefinition = apps.get_model("Applications", "StageDefinition")
    DocumentRequirement = apps.get_model("Documents", "DocumentRequirement")

    # --- StageDefinition: collapse UK's CAS stage --------------------------
    for country, stages in STAGE_SEQUENCE.items():
        # Drop any stage no longer in the sequence for this country (e.g.
        # UK's old CAS row).
        StageDefinition.objects.filter(country=country).exclude(stage__in=stages).delete()
        for order, stage in enumerate(stages, start=1):
            StageDefinition.objects.update_or_create(
                country=country, stage=stage, defaults={"order": order}
            )

    # --- DocumentRequirement: amend Canada/UK Student, add Child Student ---
    for (country, visa_type), stages in REQUIREMENTS_BY_COUNTRY.items():
        # "Amend" = replace outright: delete whatever exists for this
        # country/visa_type today (including stale items and, for UK, any
        # leftover CAS-stage rows) and recreate from the canonical list.
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


def reverse_amend_requirements(apps, schema_editor):
    # Best-effort reverse: remove exactly what this migration created. The
    # stale requirements it deleted on the way forward cannot be restored.
    DocumentRequirement = apps.get_model("Documents", "DocumentRequirement")
    for country, visa_type in REQUIREMENTS_BY_COUNTRY:
        DocumentRequirement.objects.filter(country=country, visa_type=visa_type).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("Documents", "0011_alter_documentrequirement_visa_type"),
        ("Applications", "0010_alter_visaapplication_visa_type"),
    ]

    operations = [
        migrations.RunPython(amend_requirements, reverse_amend_requirements),
    ]
