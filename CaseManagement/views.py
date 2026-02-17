from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect, get_object_or_404
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model, update_session_auth_hash, authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db.models import Count, Q
from Applications.models import VisaApplication, RejectionLetter, PreviousRefusalLetter
from Accounts.models import ClientProfile
from Documents.models import Document
from django.views.generic import TemplateView, ListView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import zipfile, io
from django.http import HttpResponse
from collections import defaultdict
from django.http import FileResponse, Http404
from django.views.decorators.clickjacking import xframe_options_exempt
from pathlib import Path
from io import BytesIO
from django.contrib.auth.mixins import LoginRequiredMixin
import csv
from django.http import HttpResponse
from django.views import View
import os



User = get_user_model()


# views.py

class OfficerDocumentAnalyticsDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "case_officer/documents/analytics_dashboard.html"


class ComplianceAuditExportView(LoginRequiredMixin, View):

    def get(self, request):

        officer = getattr(request.user, "staff_profile", None)
        if not officer:
            raise PermissionDenied("Not authorized.")

        documents = (
            Document.objects
            .select_related(
                "application",
                "application__client__user",
                "requirement"
            )
            .filter(
                Q(application__created_by_officer=officer) |
                Q(application__assigned_officer=officer)
            )
            .order_by("-uploaded_at")
        )

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=compliance_audit.csv"

        writer = csv.writer(response)
        writer.writerow([
            "Reference",
            "Client",
            "Email",
            "Requirement",
            "Stage",
            "Status",
            "Uploaded At",
            "Reviewed By",
            "Verified",
        ])

        for doc in documents:
            writer.writerow([
                doc.application.reference_no,
                doc.application.client.user.get_full_name,
                doc.application.client.user.email,
                doc.requirement.name if doc.requirement else "",
                doc.requirement.stage if doc.requirement else "",
                doc.status,
                doc.uploaded_at,
                doc.verified_by.get_full_name if doc.verified_by else "",
                doc.verified,
            ])

        return response




class CaseOfficerDocumentSearchView(LoginRequiredMixin, TemplateView):
    template_name = "case_officer/documents/officer_document_search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        officer = getattr(self.request.user, "staff_profile", None)

        if not officer:
            raise PermissionDenied("Not authorized.")

        query = self.request.GET.get("q", "")
        status = self.request.GET.get("status", "")
        stage = self.request.GET.get("stage", "")

        documents = (
            Document.objects
            .select_related(
                "application",
                "application__client__user",
                "requirement"
            )
            .filter(
                Q(application__created_by_officer=officer) |
                Q(application__assigned_officer=officer)
            )
        )

        if query:
            documents = documents.filter(
                Q(application__reference_no__icontains=query) |
                Q(application__client__user__first_name__icontains=query) |
                Q(application__client__user__last_name__icontains=query) |
                Q(requirement__name__icontains=query)
            )

        if status:
            documents = documents.filter(status=status)

        if stage:
            documents = documents.filter(requirement__stage=stage)

        context["documents"] = documents.order_by("-uploaded_at")
        context["query"] = query

        return context


@login_required
def download_documents_by_stage(request, pk, stage):

    staff_profile = getattr(request.user, "staff_profile", None)

    if not staff_profile:
        return HttpResponse(status=403)

    application = get_object_or_404(
        VisaApplication.objects.filter(
            pk=pk
        ).filter(
            Q(assigned_officer=staff_profile) |
            Q(created_by_officer=staff_profile)
        )
    )

    docs = (
        application.documents
        .select_related("requirement")
        .filter(requirement__stage=stage)
    )

    if not docs.exists():
        return HttpResponse("No documents found", status=404)

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as zipf:
        for doc in docs:
            if doc.file:
                zipf.write(
                    doc.file.path,
                    arcname=f"{stage}/{doc.requirement.name}_{doc.id}{doc.file.path[-4:]}"
                )

    buffer.seek(0)
    response = HttpResponse(buffer, content_type="application/zip")
    response["Content-Disposition"] = (
        f'attachment; filename="{application.reference_no}_{stage}_documents.zip"'
    )
    return response


@login_required
def download_rejection_letters(request, pk):
    # Get officer profile
    staff_profile = getattr(request.user, "staff_profile", None)

    if not staff_profile:
        return HttpResponse(status=403)

    application = get_object_or_404(
        VisaApplication.objects.filter(
            pk=pk
        ).filter(
            Q(assigned_officer=staff_profile) |
            Q(created_by_officer=staff_profile)
        )
    )

    letters = application.rejection_letters.all()

    if not letters.exists():
        return HttpResponse("No rejection letters found", status=404)

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as zipf:
        for i, letter in enumerate(letters, start=1):
            if letter.file:
                zipf.write(
                    letter.file.path,
                    arcname=f"Rejection_Letter_{i}{letter.file.path[-4:]}"
                )

    buffer.seek(0)
    response = HttpResponse(buffer, content_type="application/zip")
    response["Content-Disposition"] = (
        f'attachment; filename="{application.reference_no}_rejection_letters.zip"'
    )
    return response

@xframe_options_exempt
@login_required
def preview_media(request, path):
    file_path = Path(settings.MEDIA_ROOT) / path
    if not file_path.exists():
        raise Http404()

    return FileResponse(open(file_path, "rb"))


@login_required
def download_application_documents_zip(request, pk):

    # Get officer profile
    staff_profile = getattr(request.user, "staff_profile", None)

    if not staff_profile:
        return HttpResponse(status=403)

    # Restrict application access
    # application = get_object_or_404(
    #     VisaApplication,
    #     pk=pk,
    #     assigned_officer=staff_profile  # 🔐 ONLY their applications
    # )

    application = get_object_or_404(
        VisaApplication.objects.filter(
            pk=pk
        ).filter(
            Q(assigned_officer=staff_profile) |
            Q(created_by_officer=staff_profile)
        )
    )


    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:

        # 📂 DOCUMENTS
        for doc in application.documents.select_related("requirement"):
            if not doc.file:
                continue

            if not os.path.exists(doc.file.path):
                continue

            filename = os.path.basename(doc.file.name)
            stage = doc.requirement.stage if doc.requirement else "OTHER"

            zip_file.write(
                doc.file.path,
                arcname=f"documents/{stage}/{filename}"
            )

        # 📂 REJECTION LETTERS
        for letter in application.rejection_letters.all():
            if not letter.file:
                continue

            if not os.path.exists(letter.file.path):
                continue

            filename = os.path.basename(letter.file.name)

            zip_file.write(
                letter.file.path,
                arcname=f"rejection_letters/{filename}"
            )

    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/zip")
    response["Content-Disposition"] = (
        f'attachment; filename="{application.reference_no}_documents.zip"'
    )

    return response


@login_required
def download_application_documents_zipold(request, pk):
    application = get_object_or_404(
        VisaApplication,
        pk=pk,
        client__user=request.user
    )

    buffer = io.BytesIO()
    zip_file = zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED)

    for doc in application.documents.all():
        if doc.file:
            zip_file.writestr(
                f"documents/{doc.requirement.name}_{doc.id}.pdf",
                doc.file.read()
            )

    for letter in application.rejection_letters.all():
        zip_file.writestr(
            f"rejection_letters/letter_{letter.id}.pdf",
            letter.file.read()
        )

    zip_file.close()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/zip")
    response["Content-Disposition"] = (
        f'attachment; filename="{application.reference_no}_documents.zip"'
    )
    return response


# class CaseOfficerHomeView(LoginRequiredMixin, TemplateView):
#     template_name = "case_officer/documents/my_documents_home.html"

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)

#         client = self.request.user.client_profile

#         context["applications"] = (
#             VisaApplication.objects
#             .filter(client=client)
#             .order_by("-created_at")
#         )
#         return context



class CaseOfficerDocumentsHomeView(LoginRequiredMixin, TemplateView):
    template_name = "case_officer/documents/caseofficer_documents_home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        officer = getattr(self.request.user, "staff_profile", None)

        if officer is None:
            context["applications"] = VisaApplication.objects.none()
            return context

        context["applications"] = (
            VisaApplication.objects
            .filter(
                Q(created_by_officer=officer) |
                Q(assigned_officer=officer)
            )
            .select_related("client", "client__user")
            .order_by("-created_at")
        )

        return context



class CaseOfficerApplicationDocumentsView(LoginRequiredMixin, TemplateView):
    template_name = "case_officer/documents/application_documents.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        officer = getattr(self.request.user, "staff_profile", None)

        if officer is None:
            raise PermissionDenied("You are not authorized to view this page.")

        application = get_object_or_404(
            VisaApplication,
            Q(created_by_officer=officer) | Q(assigned_officer=officer),
            pk=self.kwargs["pk"]
        )

        # 🔹 Fetch documents with requirements
        documents = (
            application.documents
            .select_related("requirement")
            .order_by("uploaded_at")
        )

        # 🔹 Group documents by requirement.stage
        grouped_documents = defaultdict(list)
        for doc in documents:
            stage = doc.requirement.stage if doc.requirement else "OTHER"
            grouped_documents[stage].append(doc)

        # 🔹 Rejection letters
        context["rejection_letters"] = (
            RejectionLetter.objects
            .filter(application=application)
            .order_by("-uploaded_at")
        )

        context["application"] = application
        context["grouped_documents"] = dict(grouped_documents)

        return context


class CaseOfficerApplicationDocumentsViewOld(LoginRequiredMixin, TemplateView):
    template_name = "case_officer/documents/application_documents.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        application = get_object_or_404(
            VisaApplication,
            pk=self.kwargs["pk"],
            client__user=self.request.user
        )

        # Fetch documents with their requirements
        documents = (
            application.documents
            .select_related("requirement")
            .order_by("uploaded_at")
        )

        # ✅ Group documents by requirement.stage
        grouped_documents = defaultdict(list)
        for doc in documents:
            stage = doc.requirement.stage if doc.requirement else "OTHER"
            grouped_documents[stage].append(doc)


        context["rejection_letters"] = (
            RejectionLetter.objects
            .filter(application=application)
            .order_by("-uploaded_at")
        )

        context["application"] = application
        context["grouped_documents"] = dict(grouped_documents)

        return context




@login_required
def case_officer_dashboard_view(request):
    if request.user.role != "Case Officer":
        return redirect("/")  # restrict non-case officers
    officer = request.user.staff_profile  
    workload = getattr(officer, "workload", 0)

    # ✅ Applications initiated directly by this officer
    initiated_count = VisaApplication.objects.filter(
        created_by_officer=officer
    ).count()

    # ✅ Applications assigned (either initiated or auto-assigned)
    assigned_count = VisaApplication.objects.filter(
        assigned_officer=officer
    ).count()

    # ✅ Breakdown of statuses for officer’s assigned applications
    status_breakdown = (
        VisaApplication.objects.filter(assigned_officer=officer)
        .values("status")
        .annotate(total=Count("id"))
    )

    # ✅ Officer’s applications list
    applications = VisaApplication.objects.filter(
        Q(created_by_officer=officer) | Q(assigned_officer=officer)
    ).select_related("assigned_officer", "created_by_officer")
    admin_review_count = applications.filter(status="ADMIN REVIEW").count()
    awaiting_decision_count = applications.filter(status="SUBMITTED").count()
    # ✅ Applications that are complete (approved or rejected)
    complete_count = applications.filter(
        Q(status="APPROVED") | Q(status="REJECTED")
    ).count()

    context = {
        "officer": officer,
        "workload": workload,
        "initiated_count": initiated_count,
        "assigned_count": assigned_count,
        "status_breakdown": status_breakdown,
        "applications": applications,
        "admin_review_count": admin_review_count,
        "awaiting_decision_count": awaiting_decision_count,
        "complete_count": complete_count,

    }
    return render(request, "case_officer/case_officer_dashboard1.html", context)



@login_required
def case_officer_dashboard_view000(request):
    if request.user.role != "Case Officer":
        return redirect("/")  # restrict non-case officers

    officer = request.user.staff_profile
    workload = getattr(officer, "workload", 0)

    # 🔹 Base queryset (only this officer's applications)
    applications = officer.assigned_applications.select_related("client__user").order_by("-created_at")

    # 🔹 Metrics
    assigned_count = applications.filter(status="ASSIGNED").count()
    initiated_count = applications.filter(status="INITIATED").count()
    admin_review_count = applications.filter(status="ADMIN REVIEW").count()
    awaiting_decision_count = applications.filter(status="SUBMITTED").count()
    complete_count = applications.filter().count()


    return render(
        request,
        "case_officer/case_officer_dashboard1.html",
        {
            "applications": applications,
            "workload": workload,
            "assigned_count": assigned_count,
            "initiated_count": initiated_count,
            "admin_review_count": admin_review_count,
            "awaiting_decision_count": awaiting_decision_count,
            "complete_count": complete_count,
        },
    )


@login_required
def case_officer_dashboard_view1(request):
    if request.user.role != "Case Officer":
        return redirect("/")  # restrict

    officer = request.user.staff_profile
    workload = getattr(request.user.staff_profile, "workload", 0)
    applications = officer.assigned_applications.select_related("client__user").order_by("-created_at")

    return render(
        request,
        "case_officer/case_officer_dashboard1.html",
        {"applications": applications, "workload": workload},
    )

class StartApplication(TemplateView):
    template_name = "case_officer/display_requirements.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Template URL with placeholder {pk}, replaced by JS after application creation
        context["application_documents_url"] = "/CaseManagement/applications/{pk}/documents/"
        return context


@login_required
def applications_list(request):
    return render(request, "case_officer/applications_list.html")


@login_required
def application_documentsold(request, pk):
    app = get_object_or_404(VisaApplication, id=pk)
    client_profile = app.client  # access the related client
    return render(
        request,
        "case_officer/application_documents.html",
        {"application": app, "client_profile": client_profile},
    )



@login_required
def application_documents(request, pk):
    application = get_object_or_404(
        VisaApplication,
        id=pk  
    )
    client = application.client
    stage_sequence = application.get_stage_sequence()
    current_stage = application.stage

    documents = application.documents.filter(
        requirement__stage=current_stage
    ).select_related("requirement")

    
    completed_stages = stage_sequence[:stage_sequence.index(current_stage)]

    return render(request, "case_officer/visa_requirements_merged.html", {
        "application": application,
        "documents": documents,
        "stage_sequence": stage_sequence,
        "current_stage": current_stage,
        "completed_stages": completed_stages,
    })



@login_required
def application_details(request, pk):
    app = get_object_or_404(VisaApplication, pk=pk)
    return render(
        request,
        "case_officer/application_details.html",
        {"application_id": str(app.id)}  # pass only ID, frontend fetches details via API
    )



# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def upload_refusals(request, pk):
#     application = get_object_or_404(VisaApplication, id=pk)

#     files = request.FILES.getlist("refusal_files")
#     uploaded = 0

#     for f in files:
#         # Save to application's refusal_letter (or create multiple model entries if needed)
#         Document.objects.create(
#             application=application,
#             requirement=None,  # or special "Refusal" requirement
#             file=f,
#             status="UPLOADED"
#         )
#         uploaded += 1

#     return Response({"success": True, "files_uploaded": uploaded})




@login_required
def upload_refusal_letters(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    application = get_object_or_404(VisaApplication, id=pk)
    files = request.FILES.getlist("refusal_files")
    uploaded = []

    for f in files:
        obj = PreviousRefusalLetter.objects.create(
            application=application,
            file=f,
            uploaded_by=request.user
        )
        uploaded.append({
            "id": obj.id,
            "file": obj.file.url,
            "uploaded_at": obj.uploaded_at.strftime("%Y-%m-%d %H:%M:%S"),
        })

    return JsonResponse({"success": True, "refusal_letters": uploaded})


    
@login_required
def form_filled_submission(request, pk):
    app = get_object_or_404(VisaApplication, pk=pk)

    try:
        form_filled = app.form_filled
    except FormFilled.DoesNotExist:
        form_filled = None

    if request.method == "POST":
        form = FormFilledForm(request.POST, request.FILES, instance=form_filled)  # ✅ include request.FILES
        if form.is_valid():
            form_instance = form.save(commit=False)
            form_instance.application = app
            form_instance.save()  # triggers status change to ADMIN REVIEW
            return redirect("CaseManagement:application-details", pk=app.pk)
    else:
        form = FormFilledForm(instance=form_filled)

    return render(request, "case_officer/form_filled_submission.html", {
        "form": form,
        "application": app,
    })



@login_required
def admin_review_submission(request):
    return render(request, "case_officer/admin_review_submission.html")

@login_required
def finalize_application(request):
    return render(request, "case_officer/finalize_applications.html")

@login_required
def finalized_applications_list(request):
    return render(request, "case_officer/finalized_applications.html")


@login_required
def reviewed_applications_page(request):
    return render(request, "case_officer/form_processing.html")



# @login_required
# def application_detail_page(request, pk):
#     return render(request, "case_officer/application_details.html", {"application_id": pk})



# @login_required
# def case_officer_dashboard_view(request):
#     if request.user.role != "Case Officer":
#         return redirect("/")  # role check

#     workload = getattr(request.user.staff_profile, "workload", 0)

#     return render(
#         request,
#         "case_officer/case_officer_dashboard1.html",
#         {"workload": workload},
#     )



# @login_required
# def case_officer_dashboard_view(request):
#     if request.user.role != "Case Officer":
#         return redirect("/")  # role check

#     # applications = VisaApplication.objects.filter(client=request.user)
#     # apps_data = []
#     # for app in applications:
#     #     docs = Document.objects.filter(application=app).select_related("requirement")
#     #     apps_data.append({
#     #         "app": app,
#     #         "docs": docs
#     #     })
#     return render(request, "case_officer/case_officer_dashboard1.html")