from django.urls import path
from . import views
from .views import *
from django.conf import settings
from django.conf.urls.static import static

app_name = "CaseManagement"

urlpatterns = [
    path("case_officer_dashboard/", case_officer_dashboard_view, name="case_officer_dashboard"),
    path('start/', StartApplication.as_view(), name='start-application'),
    path("applications/", applications_list, name="applications-list"),
    path("applications/<uuid:pk>/", application_details, name="application-details"),
    path("applications/<uuid:pk>/documents/", application_documents, name="application_documents"),
    path("applications/admin-review-submission-list/", admin_review_submission, name="admin-review-submission-list"),
    path("applications/applications-finalization-list/", finalize_application, name="applications-finalization-list"),
    path("applications/finalized-applications-list/", finalized_applications_list, name="finalized-applications-list"),

    # path("applications/<uuid:pk>/form-filled/", form_filled_submission, name="form-filled"),
    path("applications/form-filled-submissions/", reviewed_applications_page, name="form-filled-submissions"),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

