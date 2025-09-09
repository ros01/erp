from django.urls import path
from . import api_views
from Accounts.views import ClientRegistrationView

urlpatterns = [
    path("clients/register/", ClientRegistrationView.as_view(), name="client-register"),
    path("country/", api_views.CountryChoicesView.as_view(), name="country-choices"),
    path("countries/", api_views.CountryListAPIView.as_view(), name="country-list"),
    path("visa-types/", api_views.VisaTypeListAPIView.as_view(), name="visa-type-list"),
    path("requirements/", api_views.RequirementListAPIView.as_view(), name="requirement-list"),
    path("applications/new/", api_views.ApplicationCreateAPIView.as_view(), name="application-create"),
]
