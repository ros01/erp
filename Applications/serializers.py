# applications/serializers.py
from rest_framework import serializers
from Documents.models import DocumentRequirement, Document
from .models import VisaApplication, PreviousRefusalLetter, StudentApplicationPipeline, RefusalLetter
from django.contrib.auth import get_user_model
from django.utils import timezone
from .services import is_pending_admin_validation
# from Documents.serializers import DocumentRequirementSerializer, DocumentSerializer


User = get_user_model()


# serializers.py
class StudentPipelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentApplicationPipeline
        fields = "__all__"


class DocumentSerializer(serializers.ModelSerializer):
    requirement_name = serializers.CharField(source="requirement.name", read_only=True)
    stage = serializers.CharField(source="requirement.stage")
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    status_badge = serializers.SerializerMethodField()
    application = serializers.PrimaryKeyRelatedField(read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "application",
            "requirement_name",
            "file",
            "status",            # keep raw status
            "stage",   
            "status_display",
            "status_badge",
            "review_comments",
            "uploaded_at",
            "file_url"
        ]
    
    def get_file_url(self, obj):
        return obj.file.url if obj.file else None

        
    def get_status_badge(self, obj):
        mapping = {
            "MISSING": "badge-soft-danger",
            "UPLOADED": "badge-soft-info",
            "REVIEWED": "badge-soft-success",
            "PENDING": "badge-soft-warning",
            "REJECTED": "badge-soft-danger",
        }
        return mapping.get(obj.status, "badge-soft-secondary")


# class DocumentSerializer(serializers.ModelSerializer):
#     requirement_name = serializers.CharField(source="requirement.name", read_only=True)
#     file_url = serializers.SerializerMethodField()

#     class Meta:
#         model = Document
#         fields = ["id", "requirement_name", "status", "file_url"]

#     def get_file_url(self, obj):
#         return obj.file.url if obj.file else None


class PreviousRefusalLetterSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = PreviousRefusalLetter
        fields = ["id", "file_url", "uploaded_at", "file"]

    def get_file_url(self, obj):
        return obj.file.url if obj.file else None


class VisaApplicationReapplySerializer(serializers.ModelSerializer):
    documents = DocumentSerializer(many=True, read_only=True)
    refusal_letters = PreviousRefusalLetterSerializer(many=True, read_only=True)

    class Meta:
        model = VisaApplication
        fields = [
            "id", "reference_no", "country", "visa_type", "status",
            "documents", "refusal_letters"
        ]

class RefusalLetterSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()

    class Meta:
        model = RefusalLetter
        fields = ("id", "file", "uploaded_at")

    def get_file(self, obj):
        if obj.file and hasattr(obj.file, "url"):
            return obj.file.url
        return None


class ReapplyApplicationSerializer(serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField()
    decision_date = serializers.SerializerMethodField()
    submission_date = serializers.SerializerMethodField()
    refusal_letter = RefusalLetterSerializer(many=True, read_only=True)
    visa_type_display = serializers.CharField(source="get_visa_type_display", read_only=True)
    country_display = serializers.CharField(source="get_country_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    status_badge = serializers.SerializerMethodField()
    assigned_officer_name = serializers.CharField(read_only=True)
    created_by_officer_name = serializers.CharField(read_only=True)
    assigned_officer_name = serializers.CharField(
        source="assigned_officer.user.get_full_name", read_only=True
    )
    created_by_officer_name = serializers.CharField(
        source="created_by_officer.user.get_full_name", read_only=True
    )
    client_name = serializers.CharField(
        source="client.user.get_full_name", read_only=True
    )
    client_email = serializers.CharField(
        source="client.user.email", read_only=True
    )
    passport_number = serializers.CharField(
        source="client.passport_number", read_only=True
    )
    documents = DocumentSerializer(many=True, read_only=True)
    refusal_letters = PreviousRefusalLetterSerializer(many=True, read_only=True)

    class Meta:
        model = VisaApplication
        fields = [
            "id", "client_name", "client_email",
            "reference_no", "passport_number",
            "visa_type", "visa_type_display",
            "country", "country_display",
            "status", "status_display", "status_badge",
            "assigned_officer",
            "created_by_officer",
            "assigned_officer_name",
            "created_by_officer_name",
            "created_at",
            "visa_application_url",
            "submission_date",
            "decision_date",
            "documents",
            "refusal_letter",
            "refusal_letters",
        ]

    def get_created_at(self, obj):
        if obj.created_at:
            return obj.created_at.strftime("%d/%m/%Y, %H:%M:%S")
        return None

    def get_decision_date(self, obj):
        if obj.decision_date:
            return obj.decision_date.strftime("%d/%m/%Y, %H:%M:%S")
        return None

    def get_submission_date(self, obj):
        if obj.submission_date:
            return obj.submission_date.strftime("%d/%m/%Y, %H:%M:%S")
        return None

    def get_status_badge(self, obj):
        mapping = {
            "REFUSED": "badge-soft-danger",
            "APPROVED": "badge-soft-success",
            "SUBMITTED": "badge-soft-warning",
            "ADMIN REVIEW": "badge-soft-info",
            "REVIEWED": "badge-soft-warning",
            "ASSIGNED": "badge-soft-primary",
            "INITIATED": "badge-soft-primary",
            "QUEUED": "badge-soft-secondary",
        }
        return mapping.get(obj.status, "badge-soft-secondary")

# class PreviousRefusalLetterSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = PreviousRefusalLetter
#         fields = ["id", "file", "uploaded_at", "uploaded_by"]




class ReapplyDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "name", "file", "status"]


class DocumentRequirementSerializer(serializers.ModelSerializer):
    form_file_url = serializers.SerializerMethodField()

    stage_display = serializers.CharField(
        source="get_stage_display",
        read_only=True
    )

    class Meta:
        model = DocumentRequirement
        fields = [
            "id",
            "country",
            "visa_type",
            "stage",           # 🔥 REQUIRED
            "stage_display",   # 🔥 REQUIRED
            "name",
            "description",
            "is_mandatory",
            "form_file_url",
        ]


    def get_form_file_url(self, obj):
        request = self.context.get("request")
        if obj.form_file and hasattr(obj.form_file, "url"):
            if request:
                return request.build_absolute_uri(obj.form_file.url)
            return obj.form_file.url
        return None


        
# class DocumentRequirementSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = DocumentRequirement
#         fields = [
#             "id", "country", "visa_type",
#             "name", "description", "category", "is_mandatory"
#         ]


class DocumentSerializer000(serializers.ModelSerializer):
    requirement_name = serializers.CharField(source="requirement.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    status_badge = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id", "requirement_name", "file", "status", "status_display",
            "status_badge", "review_comments", "uploaded_at"
        ]

    def get_status_badge(self, obj):
        return obj.get_status_badge()







class DocumentSerializer00(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    status_badge = serializers.SerializerMethodField()
    requirement_name = serializers.CharField(source="requirement.name", read_only=True)

    class Meta:
        model = Document
        fields = [
            "id", "requirement_name", "status", "status_display",
            "status_badge", "file", "review_comments", "uploaded_at"
        ]

    def get_status_badge(self, obj):
        mapping = {
            "MISSING": "badge-soft-warning",
            "UPLOADED": "badge-soft-info",
            "REVIEWED": "badge-soft-success",
            "REJECTED": "badge-soft-danger",
            # "PENDING": "badge-soft-warning",
        }
        return mapping.get(obj.status, "badge-soft-secondary")



class VisaApplicationDetailSerializer(serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField()
    decision_date = serializers.SerializerMethodField()
    submission_date = serializers.SerializerMethodField()
    client_notified_at_display = serializers.SerializerMethodField()
    refusal_letter = RefusalLetterSerializer(many=True, read_only=True)
    country_display = serializers.CharField(source="get_country_display", read_only=True)
    visa_type_display = serializers.CharField(source="get_visa_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    status_badge = serializers.SerializerMethodField()
    assigned_officer_name = serializers.CharField(
        source="assigned_officer.user.get_full_name", read_only=True
    )
    created_by_officer_name = serializers.CharField(
        source="created_by_officer.user.get_full_name", read_only=True
    )
    client_name = serializers.CharField(
        source="client.user.get_full_name", read_only=True
    )
    client_email = serializers.CharField(
        source="client.user.email", read_only=True
    )
    passport_number = serializers.CharField(
        source="client.passport_number", read_only=True
    )
    documents = DocumentSerializer(many=True, read_only=True)
    # refusal_letters = PreviousRefusalLetterSerializer(many=True, read_only=True)  # ✅ include here

    class Meta:
        model = VisaApplication
        fields = [
            "id", "client_name", "client_email", "reference_no", "country", "country_display", "passport_number",
            "visa_type", "visa_type_display", "status", "status_display", "assigned_officer", "created_by_officer",
            "status_badge", "assigned_officer_name", "created_by_officer_name", "created_at", "visa_application_url",
            "submission_date", "decision_date", "client_notified_at_display", "documents",  "refusal_letter"
        ]

    def get_created_at(self, obj):
        if obj.created_at:
            return obj.created_at.strftime("%d/%m/%Y, %H:%M:%S")
        return None

    def get_decision_date(self, obj):
        if obj.decision_date:
            return obj.decision_date.strftime("%d/%m/%Y, %H:%M:%S")
        return None

    def get_submission_date(self, obj):
        if obj.submission_date:
            return obj.submission_date.strftime("%d/%m/%Y, %H:%M:%S")
        return None

    def get_client_notified_at_display(self, obj):
        if obj.client_notified_at:
            return obj.client_notified_at.strftime("%d/%m/%Y, %H:%M:%S")
        return None

    def get_status_badge(self, obj):
        mapping = {
            "APPROVED": "badge-soft-success",
            "REFUSED": "badge-soft-danger",
            "SUBMITTED": "badge-soft-warning",
            "REVIEWED": "badge-soft-warning",
            "ADMIN REVIEW": "badge-soft-info",
            "ASSIGNED": "badge-soft-primary",
            "INITIATED": "badge-soft-primary",
            "QUEUED": "badge-soft-secondary",
        }
        return mapping.get(obj.status, "badge-soft-secondary")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # 🔒 Client-visibility gate: a Client can't see a recorded
        # APPROVED/REFUSED decision until Admin clicks "Notify Client"
        # (see VisaApplication.client_notified). Cap what they see at
        # "SUBMITTED" ("Awaiting Embassy Decision") until then - other
        # roles (Admin, Case Officer, Finance, Support) always see the
        # real status through this same endpoint.
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if (
            getattr(user, "role", None) == "Client"
            and instance.status in ("APPROVED", "REFUSED")
            and not instance.client_notified
        ):
            data["status"] = "SUBMITTED"
            data["status_display"] = dict(VisaApplication.STATUS_CHOICES).get(
                "SUBMITTED", "Awaiting Embassy Decision"
            )
            data["status_badge"] = "badge-soft-warning"
            data["decision_date"] = None
            data["client_notified_at_display"] = None
            data["refusal_letter"] = []
        return data

# class VisaApplicationUrlUpdateSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = VisaApplication
#         fields = ["visa_application_url"]


class VisaApplicationUrlUpdateSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    status_badge = serializers.SerializerMethodField()

    class Meta:
        model = VisaApplication
        fields = [
            "id",  # 🔑 needed for frontend lookup
            "visa_application_url",
            "status",
            "status_display",
            "status_badge",
        ]

    def get_status_badge(self, obj):
        mapping = {
            "REFUSED": "badge-soft-danger",
            "APPROVED": "badge-soft-success",
            "SUBMITTED": "badge-soft-warning",
            "ADMIN REVIEW": "badge-soft-info",
            "REVIEWED": "badge-soft-warning",
            "ASSIGNED": "badge-soft-primary",
            "INITIATED": "badge-soft-primary",
            "QUEUED": "badge-soft-secondary",
        }
        return mapping.get(obj.status, "badge-soft-secondary")

    def update(self, instance, validated_data):
        instance.visa_application_url = validated_data.get(
            "visa_application_url", instance.visa_application_url
        )
        # ✅ force status change
        instance.status = "ADMIN REVIEW"
        instance.admin_review_sent_at = timezone.now()
        instance.save(update_fields=["visa_application_url", "status", "admin_review_sent_at"])
        return instance

class VisaApplicationUrlUpdateSerializer000(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    status_badge = serializers.SerializerMethodField()

    class Meta:
        model = VisaApplication
        fields = ["visa_application_url", "status", "status_display",
            "status_badge"]


    def get_status_badge(self, obj):
        mapping = {
            "APPROVED": "badge-soft-success",
            "REFUSED": "badge-soft-danger",
            "ADMIN REVIEW": "badge-soft-info",
            "REVIEWED": "badge-soft-warning",
            "ASSIGNED": "badge-soft-primary",
            "QUEUED": "badge-soft-secondary",
        }
        return mapping.get(obj.status, "badge-soft-secondary")

    def update(self, instance, validated_data):
        instance.visa_application_url = validated_data.get("visa_application_url", instance.visa_application_url)
        # ✅ force status change
        instance.status = "ADMIN REVIEW"
        instance.admin_review_sent_at = timezone.now()
        instance.save(update_fields=["visa_application_url", "status", "admin_review_sent_at"])
        return instance


class VisaApplicationsSerializer(serializers.ModelSerializer):
    country_display = serializers.CharField(source="get_country_display", read_only=True)
    visa_type_display = serializers.CharField(source="get_visa_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    status_badge = serializers.SerializerMethodField()
    assigned_officer_name = serializers.CharField(
        source="assigned_officer.user.get_full_name", read_only=True
    )
    client_name = serializers.CharField(
        source="client.user.get_full_name", read_only=True
    )
    client_email = serializers.CharField(
        source="client.user.email", read_only=True
    )
    documents = DocumentSerializer(many=True, read_only=True)

    class Meta:
        model = VisaApplication
        fields = [
            "id", "client_name", "client_email", "reference_no", "country", "country_display",
            "visa_type", "visa_type_display", "status", "status_display",
            "status_badge", "assigned_officer_name", "created_at",
            "submission_date", "decision_date", "documents"
        ]

    def get_status_badge(self, obj):
        mapping = {
            "REFUSED": "badge-soft-danger",
            "APPROVED": "badge-soft-success",
            "SUBMITTED": "badge-soft-warning",
            "ADMIN REVIEW": "badge-soft-info",
            "REVIEWED": "badge-soft-warning",
            "ASSIGNED": "badge-soft-primary",
            "QUEUED": "badge-soft-secondary",
        }
        return mapping.get(obj.status, "badge-soft-secondary")

    # def to_representation(self, instance):
    #     """Hide `documents` in list mode."""
    #     rep = super().to_representation(instance)
    #     if self.context.get("list_mode", False):
    #         rep.pop("documents", None)
    #     return rep






class VisaApplicationSerializer(serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField()
    # Raw, numerically-sortable value for the same created_at moment. The
    # `created_at` field above is a human-readable "%d/%m/%Y, %H:%M:%S"
    # string, which is NOT chronologically sortable as plain text (e.g.
    # "05/01/2026" sorts before "15/09/2025" as a string even though it's
    # the later date) - front-end tables sort by this field instead.
    created_at_ts = serializers.SerializerMethodField()
    decision_date = serializers.SerializerMethodField()
    submission_date = serializers.SerializerMethodField()
    refusal_letter = RefusalLetterSerializer(many=True, read_only=True)
    visa_type_display = serializers.CharField(source="get_visa_type_display", read_only=True)
    country_display = serializers.CharField(source="get_country_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    status_badge = serializers.SerializerMethodField()
    assigned_officer_name = serializers.CharField(read_only=True)
    created_by_officer_name = serializers.CharField(read_only=True)
    assigned_officer_name = serializers.CharField(
        source="assigned_officer.user.get_full_name", read_only=True
    )
    created_by_officer_name = serializers.CharField(
        source="created_by_officer.user.get_full_name", read_only=True
    )
    # 🔒 Admin-validation gate (see Applications.services.is_pending_admin_validation)
    validated_by_name = serializers.CharField(
        source="validated_by.user.get_full_name", read_only=True, default=None
    )
    is_locked_for_officer = serializers.SerializerMethodField()
    # 🔒 Client-notification gate (see VisaApplicationSerializer.to_representation
    # below, and Applications.api_views.NotifyClientAPIView)
    client_notified_display = serializers.SerializerMethodField()
    notified_by_name = serializers.CharField(
        source="notified_by.user.get_full_name", read_only=True, default=None
    )
    client_notified_at_display = serializers.SerializerMethodField()
    client_name = serializers.CharField(
        source="client.user.get_full_name", read_only=True
    )
    client_email = serializers.CharField(
        source="client.user.email", read_only=True
    )
    client_phone = serializers.CharField(
        source="client.user.phone", read_only=True
    )
    passport_number = serializers.CharField(
        source="client.passport_number", read_only=True
    )
    documents = DocumentSerializer(many=True, read_only=True)

    class Meta:
        model = VisaApplication
        fields = [
            "id", "client_name", "client_email", "client_phone","passport_number",
            "reference_no",
            "visa_type", "visa_type_display",
            "country", "country_display",
            "status", "status_display", "status_badge",
            "assigned_officer",
            "created_by_officer",
            "assigned_officer_name",
            "created_by_officer_name",
            "admin_validated",
            "validated_by_name",
            "is_locked_for_officer",
            "client_notified_display",
            "notified_by_name",
            "client_notified_at_display",
            "created_at",
            "created_at_ts",
            "visa_application_url",
            "submission_date",
            "decision_date",
            "documents",
            "refusal_letter",
        ]

    def get_created_at(self, obj):
        if obj.created_at:
            return obj.created_at.strftime("%d/%m/%Y, %H:%M:%S")
        return None

    def get_created_at_ts(self, obj):
        return obj.created_at.timestamp() if obj.created_at else None

    def get_is_locked_for_officer(self, obj):
        return is_pending_admin_validation(obj)

    def get_client_notified_display(self, obj):
        return obj.client_notified

    def get_client_notified_at_display(self, obj):
        if obj.client_notified_at:
            return obj.client_notified_at.strftime("%d/%m/%Y, %H:%M:%S")
        return None

    def get_decision_date(self, obj):
        if obj.decision_date:
            return obj.decision_date.strftime("%d/%m/%Y, %H:%M:%S")
        return None

    def get_submission_date(self, obj):
        if obj.submission_date:
            return obj.submission_date.strftime("%d/%m/%Y, %H:%M:%S")
        return None

    def get_status_badge(self, obj):
        mapping = {
            "REFUSED": "badge-soft-danger",
            "APPROVED": "badge-soft-success",
            "SUBMITTED": "badge-soft-warning",
            "ADMIN REVIEW": "badge-soft-info",
            "REVIEWED": "badge-soft-warning",
            "ASSIGNED": "badge-soft-primary",
            "INITIATED": "badge-soft-primary",
            "QUEUED": "badge-soft-secondary",
        }
        return mapping.get(obj.status, "badge-soft-secondary")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # 🔒 Client-visibility gate: a Client can't see a recorded
        # APPROVED/REFUSED decision until Admin clicks "Notify Client"
        # (see VisaApplication.client_notified). Cap what they see at
        # "SUBMITTED" ("Awaiting Embassy Decision") until then - other
        # roles (Admin, Case Officer, Finance, Support) always see the
        # real status through this same endpoint/table.
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if (
            getattr(user, "role", None) == "Client"
            and instance.status in ("APPROVED", "REFUSED")
            and not instance.client_notified
        ):
            data["status"] = "SUBMITTED"
            data["status_display"] = dict(VisaApplication.STATUS_CHOICES).get(
                "SUBMITTED", "Awaiting Embassy Decision"
            )
            data["status_badge"] = "badge-soft-warning"
            data["decision_date"] = None
            data["refusal_letter"] = []
        return data

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["client"] = user
        return super().create(validated_data)




class DocumentSerializer000(serializers.ModelSerializer):
    requirement_name = serializers.CharField(source="requirement.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    status_badge = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",  "requirement", "requirement_name", "file", "status",
            "status_display", "status_badge", "uploaded_at",
            "review_comments"
        ]

    def get_status_badge(self, obj):
        badge_map = {
            "MISSING": "badge-soft-secondary",
            "UPLODED": "badge-soft-info",
            "PENDING": "badge-soft-warning",
            "VERIFIED": "badge-soft-success",
            "REJECTED": "badge-soft-danger",
        }
        return badge_map.get(obj.status, "badge-soft-dark")

class DocumentSerializer00(serializers.ModelSerializer):
    requirement = DocumentRequirementSerializer(read_only=True)

    class Meta:
        model = Document
        fields = ["id", "requirement", "status", "file", "uploaded_at"]


class DocumentSerializer01(serializers.ModelSerializer):
    requirement_name = serializers.CharField(source="requirement.name", read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "requirement_name",
            "file",
            "status",
            "review_comments",
            "uploaded_at",
        ]

class DocumentSerializer02(serializers.ModelSerializer):
    requirement_name = serializers.CharField(source="requirement.name", read_only=True)
    requirement_category = serializers.CharField(source="requirement.category", read_only=True)
    is_mandatory = serializers.BooleanField(source="requirement.is_mandatory", read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "requirement",
            "requirement_name",
            "requirement_category",
            "is_mandatory",
            "status",
            "file",
            "uploaded_at",
        ]

class VisaApplicationSerializer1(serializers.ModelSerializer):
    documents = DocumentSerializer(many=True, read_only=True)

    class Meta:
        model = VisaApplication
        fields = [
            "id",
            "client",
            "country",
            "visa_type",
            "status",
            "created_at",
            "documents",
        ]
        read_only_fields = ["client", "status", "created_at"]


class VisaApplicationSerializer0(serializers.ModelSerializer):
    documents = DocumentSerializer(many=True, read_only=True)

    class Meta:
        model = VisaApplication
        fields = ["id", "client", "country", "visa_type", "status", "created_at", "reference_no", "documents"]
        read_only_fields = ["client", "status", "created_at", "reference_no", "documents"]

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["client"] = user
        return super().create(validated_data)


# class UserSerializer(serializers.ModelSerializer):
#     password = serializers.CharField(write_only=True)

#     class Meta:
#         model = User
#         fields = ["id", "email", "password", "role"]

#     def create(self, validated_data):
#         password = validated_data.pop("password")
#         user = User(**validated_data)
#         user.set_password(password)
#         user.save()
#         return user


