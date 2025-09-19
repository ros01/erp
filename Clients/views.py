# clients/views.py
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.middleware.csrf import get_token
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView, ListView
from Applications.models import VisaApplication
from django.urls import reverse, reverse_lazy

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


class StartApplication(TemplateView):
    template_name = "clients/display_requirements.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Template URL with placeholder {pk}, replaced by JS after application creation
        context["application_documents_url"] = "/Clients/applications/{pk}/documents/"
        return context


# class StartApplication(TemplateView):
#     template_name = "clients/display_requirements.html"

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         # Base URL with placeholder pk=0 (will be replaced in JS)
#         context["application_documents_url"] = reverse("Clients:application_documents", kwargs={"pk": 0})
#         return context

# @login_required
# def application_documents(request, pk):
#     user = request.user

#     if user.role == "Client":
#         # Clients: can only see their own applications
#         app = get_object_or_404(VisaApplication, id=pk, client=user.client_profile)

#     elif user.role == "Case Officer":
#         # Case Officers: can only see applications assigned to them
#         app = get_object_or_404(VisaApplication, id=pk, assigned_officer=user.staff_profile)

#     elif user.role in ["Admin", "Finance", "Support"]:
#         # Other staff (optional): allow them to see all
#         app = get_object_or_404(VisaApplication, id=pk)

#     else:
#         return redirect("/")  # fallback, unauthorized

#     return render(request, "clients/application_documents1.html", {"application": app})


@login_required
def application_documents(request, pk):
    app = get_object_or_404(VisaApplication, id=pk, client=request.user.client_profile)
    return render(request, "clients/application_documents1.html", {"application": app})


