from django.shortcuts import render
from django.db.models import Q
from django.views.generic import TemplateView, ListView



class HomepageTemplateView(TemplateView):
    template_name = "Pages/index.html"


def get_object_or_404(request):
    return render(request, 'pages/404.html')


class StartApplication(TemplateView):
    template_name = "Pages/display_requirements.html"

class StartUKVisaApplication(TemplateView):
    template_name = "Pages/start_uk_application.html"