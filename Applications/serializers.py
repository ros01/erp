# applications/serializers.py
from rest_framework import serializers
from Documents.models import DocumentRequirement, Document
from .models import VisaApplication
from django.contrib.auth import get_user_model


User = get_user_model()






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



class DocumentRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentRequirement
        fields = [
            "id", "country", "visa_type",
            "name", "description", "category", "is_mandatory"
        ]


class DocumentSerializer(serializers.ModelSerializer):
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


class VisaApplicationSerializer(serializers.ModelSerializer):
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
