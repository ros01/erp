from django.urls import path
from . import views
from .views import *
from django.conf import settings
from django.conf.urls.static import static

# urlpatterns = [
#     # API
#     path("api/applications/", VisaApplicationListAPIView.as_view(), name="application-list"),

#     # Pages
    
# ]


app_name = "Admin"

urlpatterns = [
    path("admin_dashboard/", admin_dashboard_view, name="admin_dashboard"),
    path("admin_review_list/", admin_review_list, name="admin_review_list"),
    path("submitted_applications_list/", submitted_applications_list, name="submitted_applications_list"),
    path("finalized_applications_list/", finalized_applications_list, name="finalized_applications_list"),
    path("documents/", AdminDocumentsHomeView.as_view(), name="admin-documents-home"),
    path("documents/officer/<int:officer_id>/", CaseOfficerApplicationsView.as_view(), name="case-officer-applications"),
    path("documents/application/<uuid:pk>/", CaseOfficerApplicationDocumentsView.as_view(), name="application-documents"),
    path("documents/application/<uuid:pk>/download/", download_application_documents_zip, name="application-documents-zip"),
    path("documents/preview/<path:path>/", preview_media, name="document-preview",),
    path("documents/application/<uuid:pk>/download/<str:stage>/", download_documents_by_stage, name="application-documents-stage-zip",),
    path("documents/application/<uuid:pk>/rejections/download/", download_rejection_letters, name="application-rejection-letters-zip",),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)