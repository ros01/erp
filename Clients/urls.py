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
    # API endpoint for registration
    path("api/clients/register/", ClientRegistrationView.as_view(), name="client-register-api"),
    path("client_dashboard/", client_dashboard_view, name="client_dashboard"),
]




