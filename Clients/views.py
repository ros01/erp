# clients/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.middleware.csrf import get_token
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView, ListView
from Applications.models import VisaApplication, StageDefinition
from Documents.models import Document, DocumentRequirement
from django.urls import reverse, reverse_lazy
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from django.views.decorators.csrf import ensure_csrf_cookie
from Applications.constants import STUDENT_STAGE_SEQUENCE, STUDENT_STAGE_SEQUENCE_BY_COUNTRY



# class AddVisaApplicationDecisionsAPIView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def patch(self, request, pk=None, *args, **kwargs):
#         app_id = pk or kwargs.get("pk")
#         application = get_object_or_404(VisaApplication, id=app_id)

#         decision = request.data.get("status")
#         if decision not in ["APPROVED", "REJECTED"]:
#             return Response(
#                 {"error": "Invalid status. Must be APPROVED or REJECTED."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         # ✅ Update status and decision_date
#         from Applications.notifications import notify_visa_decision

#         # after updating status
#         application.status = decision
#         application.decision_date = timezone.now().date()
#         application.save(update_fields=["status", "decision_date"])

#         notify_visa_decision(application)  # ✅ SEND EMAIL
#         serializer = VisaApplicationSerializer(application)
#         return Response(serializer.data, status=status.HTTP_200_OK)


#     def post(self, request, pk):
#         try:
#             application = VisaApplication.objects.get(pk=pk)
#         except VisaApplication.DoesNotExist:
#             return Response({"error": "Application not found"}, status=404)

#         files = request.FILES.getlist("rejection_letters")
#         if not files:
#             return Response({"error": "No files uploaded"}, status=400)

#         for file in files:
#             RejectionLetter.objects.create(
#                 application=application,
#                 file=file
#             )

#         # 🔥 IMPORTANT: re-fetch with related data
#         application = VisaApplication.objects.prefetch_related(
#             "rejection_letters"
#         ).get(pk=pk)

#         return Response(
#             VisaApplicationSerializer(application).data,
#             status=200
#         )


class ClientRegisterPage(View):
    template_name = "clients/register.html"

    def get(self, request):
        csrf_token = get_token(request)  # ✅ fetch CSRF for this session
        return render(request, self.template_name, {"csrf_token": csrf_token})


@login_required
def client_dashboard_view(request):
    if request.user.role != "Client":
        return redirect("/")  # role check

    # ✅ All applications belonging to this client
    applications = VisaApplication.objects.filter(client=request.user.client_profile)
    # ✅ Status breakdown
    applications_count = applications.count()
    approved_count = applications.filter(status="APPROVED").count()
    rejected_count = applications.filter(status="REJECTED").count()
    completed_count = approved_count + rejected_count
    pending_count = applications.exclude(
        Q(status="APPROVED") | Q(status="REJECTED")
    ).count()

    context = {
        "applications_count": applications_count,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "completed_count": completed_count,
        "pending_count": pending_count,
    }
    
    return render(request, "clients/clients_dashboard.html", context)


class StartApplication(TemplateView):
    template_name = "clients/display_requirements_merged.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Template URL with placeholder {pk}, replaced by JS after application creation
        context["application_documents_url"] = "/Clients/applications/{pk}/documents/"
        return context

@login_required
def application_documentsold(request, pk):
    app = get_object_or_404(VisaApplication, id=pk, client=request.user.client_profile)
    return render(request, "clients/application_documents1.html", {"application": app})


@login_required
def application_documents(request, pk):
    application = get_object_or_404(
        VisaApplication,
        id=pk,
        client=request.user.client_profile
    )

    stage_sequence = application.get_stage_sequence()
    current_stage = application.stage

    documents = application.documents.filter(
        requirement__stage=current_stage
    ).select_related("requirement")

    
    completed_stages = stage_sequence[:stage_sequence.index(current_stage)]

    return render(request, "clients/visa_requirements_merged.html", {
    # return render(request, "clients/application_stage_documents.html", {
        "application": application,
        "documents": documents,
        "stage_sequence": stage_sequence,
        "current_stage": current_stage,
        "completed_stages": completed_stages,
    })


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


def get_stage_sequencel(country):
    return list(
        StageDefinition.objects
        .filter(country=country)
        .order_by("order")
        .values_list("stage", flat=True)
    )



@login_required
def application_documentsW(request, pk):
    application = get_object_or_404(
        VisaApplication,
        id=pk,
        client=request.user.client_profile
    )

    country = application.country
    stage_sequence = STUDENT_STAGE_SEQUENCE_BY_COUNTRY.get(country, [])

    current_stage = application.stage

    # Only documents for CURRENT stage
    current_documents = (
        application.documents
        .select_related("requirement")
        .filter(requirement__stage=current_stage)
        .order_by("requirement__name")
    )

    return render(
        request,
        "clients/application_stage_documents.html",
        {
            "application": application,
            "stage_sequence": stage_sequence,
            "current_stage": current_stage,
            "documents": current_documents,
        }
    )




@login_required
def application_documentsll(request, pk):
    application = get_object_or_404(
        VisaApplication,
        id=pk,
        client=request.user.client_profile
    )

    current_stage = application.current_stage

    documents = (
        application.documents
        .select_related("requirement")
        .filter(requirement__stage=current_stage)
        .order_by("requirement__name")
    )

    return render(
        request,
        "clients/application_stage_documents.html",
        {
            "application": application,
            "documents": documents,
            "current_stage": current_stage,
        }
    )


@login_required
def application_documentslast(request, pk):
    application = get_object_or_404(
        VisaApplication,
        id=pk,
        client=request.user.client_profile
    )

    stage_sequence = get_stage_sequence(application.country)

    # Fallback safety
    current_stage = application.current_stage or stage_sequence[0]

    # Split documents by stage
    documents_by_stage = {}
    for stage in stage_sequence:
        documents_by_stage[stage] = Document.objects.filter(
            application=application,
            requirement__stage=stage
        ).select_related("requirement")

    context = {
        "application": application,
        "stage_sequence": stage_sequence,
        "current_stage": current_stage,
        "documents_by_stage": documents_by_stage,
    }

    return render(
        request,
        "clients/application_documents.html",
        context
    )


@login_required
def application_documentsold(request, pk):
    app = get_object_or_404(VisaApplication, id=pk, client=request.user.client_profile)
    return render(request, "clients/application_documents1.html", {"application": app})


@login_required
def applications_list(request):
    return render(request, "clients/applications_list.html")


