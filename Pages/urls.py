from django.urls import path
from . import views
from .views import (
    HomepageTemplateView,
    StartUKVisaApplication,
    StartApplication,
    



)

app_name = 'Pages'

urlpatterns = [
    #path('', views.index, name='index'),
    path('', HomepageTemplateView.as_view(), name='index'),
    path('get_object_or_404', views.get_object_or_404, name='404'),
    path('start/', StartApplication.as_view(), name='start'),
    path('start_uk_visa_application/', StartUKVisaApplication.as_view(), name='start_uk_visa_application'),
    
    
    ]