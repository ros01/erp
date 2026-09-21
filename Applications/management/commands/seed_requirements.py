from django.core.management.base import BaseCommand
from Documents.models import DocumentRequirement
from Applications.models import StageDefinition


# ---------------------------------------------------------------------------
# StageDefinition: UK's CAS stage has been collapsed into VISA - every
# student-visa country now runs the same ADMISSION (1) -> VISA (2) pipeline.
# ---------------------------------------------------------------------------
STAGE_SEQUENCE = {
    "UK": ["ADMISSION", "VISA"],
    "CANADA": ["ADMISSION", "VISA"],
    "USA": ["ADMISSION", "VISA"],
}


# ---------------------------------------------------------------------------
# Document requirements: (name, description, category, is_mandatory)
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

# Canada "Child Student": a flat checklist (no admission/visa split in the
# source list), stored under the VISA stage. This visa type is NOT part of
# Applications.services' STUDENT staged-flow group, so it uses the flat
# all-documents completion flow - the stage value has no functional effect
# there; VISA was picked for consistency with the main Student checklist.
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

# UK "Child Student": a flat checklist (no admission/visa split in the
# source list), stored under the VISA stage - same convention as Canada
# "Child Student" above. Not part of the STUDENT staged-flow group, so it
# uses the flat all-documents completion flow.
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

# USA is untouched by this amendment - kept as the original generic
# checklist it already had.
USA_STUDENT_DOCUMENTS = {
    "ADMISSION": [
        ("International Passport (Bio-data page)", "Passport bio-data page", "IDENTITY", True),
        ("Academic Qualifications", "WAEC / NECO / Degree / Transcript", "ADMISSION", True),
        ("Curriculum Vitae (CV)", "Recent CV or résumé", "ADMISSION", True),
        ("Statement of Purpose (SOP)", "Why you want to study this course", "ADMISSION", True),
        ("Reference Letters", "Two academic or professional references", "ADMISSION", True),
        ("English Language Proof", "IELTS / TOEFL / WAEC English", "ADMISSION", True),
        ("Application Form Evidence", "School application submission", "ADMISSION", True),
        ("Portfolio", "For creative courses only", "OTHER", False),
    ],
    "VISA": [
        ("Valid International Passport", "At least 6 months validity", "IDENTITY", True),
        ("Offer Letter", "Admission letter", "ADMISSION", True),
        ("Tuition Fee Payment Proof", "Paid fees", "FINANCIAL", True),
        ("Proof of Funds", "Financial statements", "FINANCIAL", True),
        ("Medical / TB Certificate", "If required", "OTHER", True),
        ("Visa Application Form", "Completed online", "OTHER", True),
        ("Passport Photograph", "Embassy specification", "IDENTITY", True),
        ("Academic Documents", "Certificates and transcripts", "ADMISSION", True),
        ("Police Clearance Certificate", "If required", "OTHER", True),
        ("Travel History", "Previous visas", "OTHER", True),
        ("Accommodation Proof", "Hostel or tenancy", "OTHER", True),
        ("Study Plan", "Career alignment", "ADMISSION", True),
        ("Statement of Purpose", "Academic motivation", "ADMISSION", True),
        ("Reference Letters", "Academic or professional", "ADMISSION", True),
        ("English Language Proof", "IELTS / TOEFL / WAEC", "ADMISSION", True),
        ("Curriculum Vitae", "If applicable", "ADMISSION", False),
    ],
}

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
    ("UK", "CHILD STUDENT"): {
        "VISA": UK_CHILD_STUDENT_DOCUMENTS,
    },
    ("USA", "STUDENT"): USA_STUDENT_DOCUMENTS,
}


class Command(BaseCommand):
    help = (
        "Seed/amend student (and child student) document requirements and "
        "StageDefinition rows. Re-runnable: for each country/visa_type it "
        "wipes whatever requirements exist today and recreates them from "
        "the canonical list here, so it always leaves the DB matching this "
        "file exactly."
    )

    def handle(self, *args, **kwargs):
        # --- StageDefinition -------------------------------------------------
        for country, stages in STAGE_SEQUENCE.items():
            StageDefinition.objects.filter(country=country).exclude(stage__in=stages).delete()
            for order, stage in enumerate(stages, start=1):
                StageDefinition.objects.update_or_create(
                    country=country, stage=stage, defaults={"order": order}
                )
        self.stdout.write(self.style.SUCCESS("✅ StageDefinition seeded (CAS collapsed into VISA)"))

        # --- DocumentRequirement ---------------------------------------------
        for (country, visa_type), stages in REQUIREMENTS_BY_COUNTRY.items():
            deleted_total, deleted_breakdown = DocumentRequirement.objects.filter(
                country=country, visa_type=visa_type
            ).delete()
            deleted = deleted_breakdown.get("Documents.DocumentRequirement", 0)

            created = 0
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
                    created += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ {country} / {visa_type}: replaced {deleted} old requirement row(s) "
                    f"with {created} new one(s)"
                )
            )
