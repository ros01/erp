"""
URL configuration for erp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# from django.contrib import admin
# from django.urls import path

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView


urlpatterns = [
    path('', include ('Pages.urls')),
    path('admin/', admin.site.urls),
    # path("api/", include("Documents.urls")),
    path("api/", include("Applications.api_urls")),
    path('Accounts/', include('Accounts.urls')),
    path('Clients/', include('Clients.urls')),
    path('CaseManagement/', include('CaseManagement.urls')),
    path('Admin/', include('Admin.urls')),
    # path("api_app/", include("CaseManagement.api_urls")),
    # path("api/", include("Documents.api_urls")),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
