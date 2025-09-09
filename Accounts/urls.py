from django.urls import path
from . import views
from .views import *

app_name = "Accounts"

urlpatterns = [
    path("clients/register/", ClientRegistrationView.as_view(), name="client-register"),
    path('login', views.login, name='login'),
    path('logout', views.logout, name='logout'),
    path("dashboard/", client_dashboard_view, name="client_dashboard"),
    path("case_officer_dashboard/", case_officer_dashboard_view, name="case_officer_dashboard"),
]
