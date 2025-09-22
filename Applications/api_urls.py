from django.urls import path
from . import api_views
from .api_views import *
from Accounts.views import ClientRegistrationView


app_name = "Applications"

urlpatterns = [
    path("clients/register/", ClientRegistrationView.as_view(), name="client-register"),
    path("country/", api_views.CountryChoicesView.as_view(), name="country-choices"),
    path("countries/", api_views.CountryListAPIView.as_view(), name="country-list"),
    path("visa-types/", api_views.VisaTypeListAPIView.as_view(), name="visa-type-list"),
    path("requirements/", api_views.RequirementListAPIView.as_view(), name="requirement-list"),
    path("applications/new/", api_views.ApplicationCreateAPIView.as_view(), name="application-create"),
    path("documents/<uuid:pk>/upload/", DocumentUploadAPIView.as_view(), name="document-upload"),
    path("applications/", VisaApplicationListAPIView.as_view(), name="application-list"),
    path("applications/<uuid:id>/", VisaApplicationDetailAPIView.as_view(), name="applications-detail"),
    path("documents/<uuid:id>/review/", DocumentReviewAPIView.as_view(), name="document-review"),
    path("applications/reviewed/", ReviewedVisaApplicationListAPIView.as_view(), name="reviewed-application-list"),
    path("applications/admin_view/", AdminVisaApplicationListAPIView.as_view(), name="admin-application-list"),
    path("applications/submitted_list_view/", SubmittedVisaApplicationListAPIView.as_view(), name="submitted-application-list"),
    path("applications/<uuid:id>/add-url/", VisaApplicationUrlUpdateAPIView.as_view(), name="application-add-url"),
    path("applications/<uuid:pk>/finalize/", FinalizeVisaApplicationAPIView.as_view(), name="application-finalize"),
    # path("form-processing/<uuid:pk>/", FormProcessingDetailUpdateAPIView.as_view(), name="form-processing-detail"),
    # path("applications/", VisaApplicationsListAPIView.as_view(), name="application-list"),
    # path("applications/<uuid:id>/", VisaApplicationsListAPIView.as_view(), name="application-detail"),
]



