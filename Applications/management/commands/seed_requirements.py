from django.core.management.base import BaseCommand
from Documents.models import DocumentRequirement

class Command(BaseCommand):
    help = "Seed student document requirements"

    def handle(self, *args, **kwargs):
        COUNTRIES = ["UK", "CANADA", "USA"]
        VISA_TYPE = "STUDENT"

        DATA = {
            "ADMISSION": [
                ("International Passport (Bio-data page)", "Passport bio-data page"),
                ("Academic Qualifications", "WAEC / NECO / Degree / Transcript"),
                ("Curriculum Vitae (CV)", "Recent CV or résumé"),
                ("Statement of Purpose (SOP)", "Why you want to study this course"),
                ("Reference Letters", "Two academic or professional references"),
                ("English Language Proof", "IELTS / TOEFL / WAEC English"),
                ("Application Form Evidence", "School application submission"),
                ("Portfolio", "For creative courses only"),
            ],

            # ⚠️ CAS IS UK ONLY
            "CAS": [
                ("Valid International Passport", "Must be valid"),
                ("Unconditional Offer Letter", "Issued by school"),
                ("Tuition Fee Payment Proof", "Receipt or confirmation"),
                ("Proof of Funds", "28 consecutive days bank statement"),
                ("Sponsor Documents", "If sponsored"),
                ("TB Test Certificate", "IOM approved clinic"),
                ("Previous Academic Documents", "Certificates and transcripts"),
                ("CAS Payment Receipt", "If required"),
                ("Interview Readiness", "Credibility interview checklist"),
            ],

            "VISA": [
                ("Valid International Passport", "At least 6 months validity"),
                ("Offer Letter", "Admission letter"),
                ("Tuition Fee Payment Proof", "Paid fees"),
                ("Proof of Funds", "Financial statements"),
                ("Medical / TB Certificate", "If required"),
                ("Visa Application Form", "Completed online"),
                ("Passport Photograph", "Embassy specification"),
                ("Academic Documents", "Certificates and transcripts"),
                ("Police Clearance Certificate", "If required"),
                ("Travel History", "Previous visas"),
                ("Accommodation Proof", "Hostel or tenancy"),
                ("Study Plan", "Career alignment"),
                ("Statement of Purpose", "Academic motivation"),
                ("Reference Letters", "Academic or professional"),
                ("English Language Proof", "IELTS / TOEFL / WAEC"),
                ("Curriculum Vitae", "If applicable"),
            ],
        }

        for country in COUNTRIES:
            for stage, items in DATA.items():

                # 🔥 SKIP CAS FOR NON-UK COUNTRIES
                if stage == "CAS" and country != "UK":
                    continue

                for name, desc in items:
                    DocumentRequirement.objects.get_or_create(
                        country=country,
                        visa_type=VISA_TYPE,
                        stage=stage,
                        name=name,
                        defaults={
                            "description": desc,
                            "is_mandatory": True,
                        }
                    )

        if DocumentRequirement.objects.exists():
            self.stdout.write(
                self.style.WARNING("Requirements already exist — skipping seeding")
            )
            return

        self.stdout.write(self.style.SUCCESS("✅ Student document requirements seeded"))
