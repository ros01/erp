# documents/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics
from .models import DocumentRequirement
from .serializers import CountrySerializer, VisaTypeSerializer, DocumentRequirementSerializer


class CountryChoicesView(APIView):
    """
    Returns the restricted COUNTRY_CHOICES from the model.
    """
    def get(self, request, *args, **kwargs):
        # Grab distinct country choices actually in use
        countries = [
            {"code": code, "name": label}
            for code, label in DocumentRequirement.COUNTRY_CHOICES
        ]
        return Response(countries)


class CountryListAPIView(APIView):
    """
    Returns only countries that have at least one DocumentRequirement.
    """
    def get(self, request, *args, **kwargs):
        # Get unique country codes from requirements
        countries = (
            DocumentRequirement.objects
            .values_list("country", flat=True)
            .distinct()
        )
        # Convert codes to display names
        choices_dict = dict(DocumentRequirement.COUNTRIES)
        data = [{"code": c, "name": choices_dict.get(c, c)} for c in countries]
        return Response(CountrySerializer(data, many=True).data)



# class CountryListAPIView(APIView):
    """
    Returns all supported countries from choices.
    """
    # def get(self, request, *args, **kwargs):
    #     countries = [
    #         {"code": code, "name": name}
    #         for code, name in DocumentRequirement.COUNTRY_CHOICES
    #     ]
    #     return Response(CountrySerializer(countries, many=True).data)



# class VisaTypeListAPIView(APIView):
    """
    Returns visa types available for a given country.
    (For simplicity, we just return all visa types defined.)
    """
    # def get(self, request, *args, **kwargs):
    #     country = request.query_params.get("country")
    #     if not country:
    #         return Response({"error": "country query param is required"}, status=400)

    #     visa_types = [
    #         {"code": code, "name": name}
    #         for code, name in DocumentRequirement.VISA_TYPES
    #     ]
    #     return Response(VisaTypeSerializer(visa_types, many=True).data)

class VisaTypeListAPIView(APIView):
    """
    Returns visa types available for a given country,
    based only on existing DocumentRequirement entries.
    """
    def get(self, request, *args, **kwargs):
        country = request.query_params.get("country")
        if not country:
            return Response({"error": "country query param is required"}, status=400)

        visa_types = (
            DocumentRequirement.objects
            .filter(country=country)
            .values_list("visa_type", flat=True)
            .distinct()
        )

        choices_dict = dict(DocumentRequirement.VISA_TYPES)
        data = [{"code": v, "name": choices_dict.get(v, v)} for v in visa_types]
        return Response(VisaTypeSerializer(data, many=True).data)


class RequirementListAPIView(generics.ListAPIView):
    """
    Preview: Returns all requirements for a given country and visa type.
    Does NOT create any application.
    """
    serializer_class = DocumentRequirementSerializer

    def get_queryset(self):
        country = self.request.query_params.get("country")
        visa_type = self.request.query_params.get("visa_type")
        qs = DocumentRequirement.objects.all()
        if country:
            qs = qs.filter(country=country)
        if visa_type:
            qs = qs.filter(visa_type=visa_type)
        return qs


