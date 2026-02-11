# clients/urls.py
from django.urls import path
from .views import *
from Accounts.views import ClientRegistrationView
from django.contrib.auth.decorators import login_required

app_name = "Clients"

urlpatterns = [
    # HTML page for registration
    path("register/", ClientRegisterPage.as_view(), name="client-register"),
    path('start/', StartApplication.as_view(), name='start-application'),
    path("applications/", applications_list, name="applications-list"),
    path("applications/<uuid:pk>/documents/", application_documents, name="application_documents"),
    path("documents/", ClientDocumentsHomeView.as_view(), name="documents-home"),
    path("documents/application/<uuid:pk>/",ClientApplicationDocumentsView.as_view(), name="application-documents"),
    path("documents/application/<uuid:pk>/download/", download_application_documents_zip, name="application-documents-zip"),
    path("documents/preview/<path:path>/", preview_media, name="document-preview",),
    path("documents/application/<uuid:pk>/download/<str:stage>/", download_documents_by_stage, name="application-documents-stage-zip",),
    path("documents/application/<uuid:pk>/rejections/download/", download_rejection_letters, name="application-rejection-letters-zip",),



    # API endpoint for registration
    path("api/clients/register/", ClientRegistrationView.as_view(), name="client-register-api"),
    path("client_dashboard/", client_dashboard_view, name="client_dashboard"),
]





