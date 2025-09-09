# documents/urls.py
from django.urls import path
from .views import CountryListAPIView, VisaTypeListAPIView, RequirementListAPIView, CountryChoicesView

urlpatterns = [
    path("countries/", CountryListAPIView.as_view(), name="countries"),
    path("countries/", CountryChoicesView.as_view(), name="country-choices"),
    path("visa-types/", VisaTypeListAPIView.as_view(), name="visa-types"),
    path("requirements/", RequirementListAPIView.as_view(), name="requirements"),
]
