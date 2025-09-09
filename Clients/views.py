# clients/views.py
from django.shortcuts import render
from django.views import View
from django.middleware.csrf import get_token
from django.contrib.auth.decorators import login_required

class ClientRegisterPage(View):
    template_name = "clients/register.html"

    def get(self, request):
        csrf_token = get_token(request)  # ✅ fetch CSRF for this session
        return render(request, self.template_name, {"csrf_token": csrf_token})


@login_required
def client_dashboard_view(request):
    if request.user.role != "Client":
        return redirect("/")  # role check

    # applications = VisaApplication.objects.filter(client=request.user)
    # apps_data = []
    # for app in applications:
    #     docs = Document.objects.filter(application=app).select_related("requirement")
    #     apps_data.append({
    #         "app": app,
    #         "docs": docs
    #     })
    return render(request, "clients/clients_dashboard.html")
