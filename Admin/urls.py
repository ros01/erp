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

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)