from django.urls import path
from . import api_views
from .api_views import *
from Accounts.views import ClientRegistrationView


app_name = "Applications"


urlpatterns = [
    # path("requirements/", api_views.get_requirements, name="requirements"),
    path("user/", CurrentUserView.as_view(), name="current_user"),
    # path("pdf-form-fill/", pdf_form_fill, name="pdf-form-fill"),
    path("pdf-form-fill/", AutoFilledPDFView.as_view(), name="pdf-form-fill"),
    path("pdf-form/", api_views.pdf_form, name="pdf-form"),
    path("clients/register/", ClientRegistrationView.as_view(), name="client-register"),
    path("country/", api_views.CountryChoicesView.as_view(), name="country-choices"),
    path("countries/", api_views.CountryListAPIView.as_view(), name="country-list"),
    path("visa-types/", api_views.VisaTypeListAPIView.as_view(), name="visa-type-list"),
    path("requirements/", api_views.RequirementListAPIView.as_view(), name="requirement-list"),
    path("applications/new/", api_views.ApplicationCreateAPIView.as_view(), name="application-create"),
    path("clients/search/", api_views.ClientSearchAPIView.as_view(), name="client-search"),
    path("clients/new/", api_views.ClientCreateAPIView.as_view(), name="client-create"),
    path("applications/new_case/", api_views.ApplicationCreateAPICaseView.as_view(), name="application-case-create"),
    path("documents/<uuid:pk>/upload/", DocumentUploadAPIView.as_view(), name="document-upload"),
    path("applications/", VisaApplicationListAPIView.as_view(), name="application-list"),
    path("applications/review/", VisaApplicationListReviewAPIView.as_view(), name="application-list-review"),
    path("applications/<uuid:id>/", VisaApplicationDetailAPIView.as_view(), name="applications-detail"),
    path("documents/<uuid:id>/review/", DocumentReviewAPIView.as_view(), name="document-review"),
    path("applications/reviewed/", ReviewedVisaApplicationListAPIView.as_view(), name="reviewed-application-list"),
    path("applications/admin_view/", AdminVisaApplicationListAPIView.as_view(), name="admin-application-list"),
    path("applications/submitted_list_view/", SubmittedVisaApplicationListAPIView.as_view(), name="submitted-application-list"),
    path("applications/finalized_applications_list/", FinalizedVisaApplicationsListAPIView.as_view(), name="finalized-applications-list"),
    path("applications/<uuid:id>/add-url/", VisaApplicationUrlUpdateAPIView.as_view(), name="application-add-url"),
    path("applications/<uuid:pk>/finalize/", FinalizeVisaApplicationAPIView.as_view(), name="application-finalize"),
    path("applications/<uuid:pk>/add_decision/", AddVisaApplicationDecisionAPIView.as_view(), name="add-visa-decison"),
    path("applications/<uuid:pk>/upload_rejection_letter/", UploadRejectionLetterAPIView.as_view(), name="upload-rejection-letter"),
    path("applications/<uuid:pk>/reapply/", ApplicationReapplyView.as_view(), name="application-reapply"),
    path("applications/<uuid:pk>/upload-refusals/", upload_refusals, name="upload_refusals"),

    # path("form-processing/<uuid:pk>/", FormProcessingDetailUpdateAPIView.as_view(), name="form-processing-detail"),
    # path("applications/", VisaApplicationsListAPIView.as_view(), name="application-list"),
    # path("applications/<uuid:id>/", VisaApplicationsListAPIView.as_view(), name="application-detail"),
]


