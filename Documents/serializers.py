# documents/serializers.py
from rest_framework import serializers
from .models import DocumentRequirement

class CountrySerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()

class VisaTypeSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()

class DocumentRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentRequirement
        fields = ["id", "name", "description", "category", "is_mandatory"]
