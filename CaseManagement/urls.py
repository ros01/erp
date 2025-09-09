from django.urls import path
from . import views
from .views import *

app_name = "CaseManagement"

urlpatterns = [
    path("case_officer_dashboard/", case_officer_dashboard_view, name="case_officer_dashboard"),
]