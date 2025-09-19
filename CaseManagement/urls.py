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


app_name = "CaseManagement"

urlpatterns = [
    path("case_officer_dashboard/", case_officer_dashboard_view, name="case_officer_dashboard"),
    path("applications/", applications_list, name="applications-list"),
    path("applications/<uuid:pk>/", application_details, name="application-details"),
    path("applications/form-processing/", form_processing_submission, name="form-processing"),
    # path("applications/<uuid:pk>/form-filled/", form_filled_submission, name="form-filled"),
    path("applications/form-filled-submissions/", reviewed_applications_page, name="form-filled-submissions"),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

