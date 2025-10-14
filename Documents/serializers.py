# documents/serializers.py
from rest_framework import serializers
from .models import DocumentRequirement

class CountrySerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()

class VisaTypeSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()

# class DocumentRequirementSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = DocumentRequirement
#         fields = ["id", "name", "description", "category", "is_mandatory"]


# class DocumentRequirementSerializer(serializers.ModelSerializer):
#     form_file_url = serializers.SerializerMethodField()

#     class Meta:
#         model = DocumentRequirement
#         fields = [
#             "id", "country", "visa_type", "name", "description",
#             "category", "is_mandatory", "form_file_url"
#         ]

#     def get_form_file_url(self, obj):
#         request = self.context.get("request")
#         if obj.form_file and hasattr(obj.form_file, "url"):
#             return request.build_absolute_uri(obj.form_file.url)
#         return None


class DocumentRequirementSerializer(serializers.ModelSerializer):
    form_file_url = serializers.SerializerMethodField()

    class Meta:
        model = DocumentRequirement
        fields = [
            "id",
            "country",
            "visa_type",
            "name",
            "description",
            "is_mandatory",
            "form_file_url",  # ✅ include this
        ]

    def get_form_file_url(self, obj):
        request = self.context.get("request")
        if obj.form_file and hasattr(obj.form_file, "url"):
            if request:
                return request.build_absolute_uri(obj.form_file.url)
            return obj.form_file.url
        return None
