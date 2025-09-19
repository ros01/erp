# applications/urls.py
from django.urls import path
from .views import (
    VisaApplicationListView, VisaApplicationCreateView, VisaApplicationDetailView,
    DocumentListCreateView, DocumentDetailView,
    AutoAssignOfficerView, ReassignOfficerView, BulkReassignOfficerView, BulkAutoReassignView
)


urlpatterns = [
    path("applications/", VisaApplicationListView.as_view(), name="application-list"),
    path("applications/new/", VisaApplicationCreateView.as_view(), name="application-create"),
    path("applications/<int:pk>/", VisaApplicationDetailView.as_view(), name="application-detail"),
    path("applications/<int:pk>/assign/", AutoAssignOfficerView.as_view(), name="application-assign"),
    path("applications/<int:pk>/reassign/", ReassignOfficerView.as_view(), name="application-reassign"),
    path("applications/bulk-reassign/", BulkReassignOfficerView.as_view(), name="application-bulk-reassign"),
    path("applications/bulk-auto-reassign/", BulkAutoReassignView.as_view(), name="application-bulk-auto-reassign"),
    path("documents/", DocumentListCreateView.as_view(), name="document-list"),
    path("documents/<int:pk>/", DocumentDetailView.as_view(), name="document-detail"),
]
