# applications/serializers.py
from rest_framework import serializers
from Documents.models import DocumentRequirement, Document
from .models import VisaApplication
from django.contrib.auth import get_user_model
# from Documents.serializers import DocumentRequirementSerializer, DocumentSerializer


User = get_user_model()


# class FormProcessingSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = FormProcessing
#         fields = [
#             "id", "application", "file", "application_url",
#             "visa_application_username", "visa_application_password"
#         ]
#         read_only_fields = ["id", "application"]



class DocumentRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentRequirement
        fields = [
            "id", "country", "visa_type",
            "name", "description", "category", "is_mandatory"
        ]


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


class DocumentSerializer(serializers.ModelSerializer):
    requirement_name = serializers.CharField(source="requirement.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    status_badge = serializers.SerializerMethodField()
    application = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "application",
            "requirement_name",
            "file",
            "status",            # keep raw status
            "status_display",
            "status_badge",
            "review_comments",
            "uploaded_at",
        ]
    # def get_status_badge(self, obj):
    #     return obj.get_status_badge()

        
    def get_status_badge(self, obj):
        mapping = {
            "MISSING": "badge-soft-danger",
            "UPLOADED": "badge-soft-info",
            "REVIEWED": "badge-soft-success",
            "PENDING": "badge-soft-warning",
            "REJECTED": "badge-soft-danger",
        }
        return mapping.get(obj.status, "badge-soft-secondary")




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
            "status_badge", "assigned_officer_name", "created_at", "visa_application_url",
            "submission_date", "decision_date", "documents"
        ]

    def get_status_badge(self, obj):
        mapping = {
            "APPROVED": "badge-soft-success",
            "REJECTED": "badge-soft-danger",
            "SUBMITTED": "badge-soft-warning",
            "REVIEWED": "badge-soft-warning",
            "ADMIN REVIEW": "badge-soft-info",
            "ASSIGNED": "badge-soft-primary",
            "QUEUED": "badge-soft-secondary",
        }
        return mapping.get(obj.status, "badge-soft-secondary")


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
            "REJECTED": "badge-soft-danger",
            "APPROVED": "badge-soft-success",
            "SUBMITTED": "badge-soft-warning",
            "ADMIN REVIEW": "badge-soft-info",
            "REVIEWED": "badge-soft-warning",
            "ASSIGNED": "badge-soft-primary",
            "QUEUED": "badge-soft-secondary",
        }
        return mapping.get(obj.status, "badge-soft-secondary")

    def update(self, instance, validated_data):
        instance.visa_application_url = validated_data.get(
            "visa_application_url", instance.visa_application_url
        )
        # ✅ force status change
        instance.status = "ADMIN REVIEW"
        instance.save(update_fields=["visa_application_url", "status"])
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
            "REJECTED": "badge-soft-danger",
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
        instance.save(update_fields=["visa_application_url", "status"])
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
            "REJECTED": "badge-soft-danger",
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
    visa_type_display = serializers.CharField(source="get_visa_type_display", read_only=True)
    country_display = serializers.CharField(source="get_country_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    status_badge = serializers.SerializerMethodField()
    assigned_officer_name = serializers.CharField(source="assigned_officer.user.get_full_name", read_only=True)
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
            "id", "client_name", "client_email",
            "reference_no",
            "visa_type", "visa_type_display",
            "country", "country_display",
            "status", "status_display", "status_badge",
            "assigned_officer_name",
            "created_at",
            "visa_application_url",
            "submission_date",
            "decision_date",
            "documents",
        ]

    def get_status_badge(self, obj):
        mapping = {
            "REJECTED": "badge-soft-danger",
            "APPROVED": "badge-soft-success",
            "SUBMITTED": "badge-soft-warning",
            "ADMIN REVIEW": "badge-soft-info",
            "REVIEWED": "badge-soft-warning",
            "ASSIGNED": "badge-soft-primary",
            "QUEUED": "badge-soft-secondary",
        }
        return mapping.get(obj.status, "badge-soft-secondary")

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


