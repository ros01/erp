from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from Documents.models import DocumentRequirement, Document
from .models import VisaApplication
from Documents.serializers import DocumentRequirementSerializer
from .serializers import (
    VisaApplicationSerializer,
)
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from Accounts.choices import *

User = get_user_model()

class CountryChoicesView(APIView):
    """
    Returns the restricted COUNTRY_CHOICES from the model.
    """
    def get(self, request, *args, **kwargs):
        # Grab distinct country choices actually in use
        countries = [
            {"code": code, "name": label}
            for code, label in NATIONALITY
        ]
        return Response(countries)

class CountryListAPIView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        countries = (
            DocumentRequirement.objects
            .values_list("country", flat=True)
            .distinct()
        )
        data = [{"code": c, "name": c} for c in countries]
        return Response(data)


class VisaTypeListAPIView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        country = request.query_params.get("country")
        qs = DocumentRequirement.objects.all()
        if country:
            qs = qs.filter(country=country)
        visa_types = qs.values_list("visa_type", flat=True).distinct()
        data = [{"code": v, "name": v} for v in visa_types]
        return Response(data)


class RequirementListAPIView(generics.ListAPIView):
    permission_classes = [AllowAny]
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




class ApplicationCreateAPIView(generics.GenericAPIView):
    """
    Confirm Application:
    Creates VisaApplication + auto-generates Document placeholders
    """
    serializer_class = VisaApplicationSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        country = request.data.get("country")
        visa_type = request.data.get("visa_type")

        if not country or not visa_type:
            return Response(
                {"detail": "country and visa_type are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Prevent duplicates: one active application per client per country+visa_type
        existing = VisaApplication.objects.filter(
            client=request.user,
            country=country,
            visa_type=visa_type,
        ).first()
        if existing:
            return Response(
                self.get_serializer(existing).data,
                status=status.HTTP_200_OK,
            )

        # Create application
        application = VisaApplication.objects.create(
            client=request.user,
            country=country,
            visa_type=visa_type,
            status="PENDING",
        )

        # Auto-create documents from requirements
        requirements = DocumentRequirement.objects.filter(country=country, visa_type=visa_type)
        Document.objects.bulk_create([
            Document(application=application, requirement=req, status="MISSING")
            for req in requirements
        ])

        return Response(
            self.get_serializer(application).data,
            status=status.HTTP_201_CREATED,
        )



class ApplicationCreateAPIViewOld(generics.GenericAPIView):
    """
    Confirm Application:
    Creates VisaApplication + auto-generates Document placeholders
    """
    serializer_class = VisaApplicationSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        country = request.data.get("country")
        visa_type = request.data.get("visa_type")

        if not country or not visa_type:
            return Response(
                {"detail": "country and visa_type are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create the application for the logged-in client
        application = VisaApplication.objects.create(
            client=request.user,
            country=country,
            visa_type=visa_type,
            status="PENDING",
        )

        # Auto-create Document placeholders
        requirements = DocumentRequirement.objects.filter(country=country, visa_type=visa_type)
        Document.objects.bulk_create([
            Document(application=application, requirement=req, status="MISSING")
            for req in requirements
        ])

        return Response(
            self.get_serializer(application).data,
            status=status.HTTP_201_CREATED,
        )

