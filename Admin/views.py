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
from django.db.models import Q, Count
from Applications.models import VisaApplication, RejectionLetter, PreviousRefusalLetter
from Accounts.models import ClientProfile
from Documents.models import Document
from django.contrib.auth.mixins import LoginRequiredMixin
import csv
from django.http import HttpResponse
from django.views import View
from django.views.generic import TemplateView, ListView
import os
from collections import defaultdict
from Accounts.models import *
from django.views.decorators.clickjacking import xframe_options_exempt
from pathlib import Path
from io import BytesIO
from django.core.exceptions import PermissionDenied
import zipfile, io

User = get_user_model()


@xframe_options_exempt
@login_required
def preview_media(request, path):
    file_path = Path(settings.MEDIA_ROOT) / path
    if not file_path.exists():
        raise Http404()

    return FileResponse(open(file_path, "rb"))




def get_application_for_user(request, pk):
    user = request.user
    staff_profile = getattr(user, "staff_profile", None)

    # 🔹 Admin users can access any application
    if user.is_superuser or user.is_staff or user.staff_profile:
        return get_object_or_404(
            VisaApplication.objects.prefetch_related(
                "documents__requirement",
                "rejection_letters"
            ),
            pk=pk
        )

    raise PermissionDenied("You are not authorized to access this application.")


@login_required
def download_documents_by_stage(request, pk, stage):

    application = get_application_for_user(request, pk)

    docs = (
        application.documents
        .select_related("requirement")
        .filter(requirement__stage=stage)
    )

    if not docs.exists():
        return HttpResponse("No documents found", status=404)

    buffer = BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for doc in docs:
            if not doc.file:
                continue
            if not os.path.exists(doc.file.path):
                continue

            filename = os.path.basename(doc.file.name)

            zipf.write(
                doc.file.path,
                arcname=f"{stage}/{filename}"
            )

    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/zip")
    response["Content-Disposition"] = (
        f'attachment; filename="{application.reference_no}_{stage}_documents.zip"'
    )

    return response



@login_required
def download_rejection_letters(request, pk):

    application = get_application_for_user(request, pk)

    letters = application.rejection_letters.all()

    if not letters.exists():
        return HttpResponse("No rejection letters found", status=404)

    buffer = BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for i, letter in enumerate(letters, start=1):
            if not letter.file:
                continue
            if not os.path.exists(letter.file.path):
                continue

            filename = os.path.basename(letter.file.name)

            zipf.write(
                letter.file.path,
                arcname=f"Rejection_Letter_{i}_{filename}"
            )

    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/zip")
    response["Content-Disposition"] = (
        f'attachment; filename="{application.reference_no}_rejection_letters.zip"'
    )

    return response



@login_required
def download_application_documents_zip(request, pk):

    application = get_application_for_user(request, pk)

    buffer = BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:

        # 📂 DOCUMENTS
        for doc in application.documents.select_related("requirement"):
            if not doc.file:
                continue
            if not os.path.exists(doc.file.path):
                continue

            filename = os.path.basename(doc.file.name)
            stage = (
                doc.requirement.stage
                if doc.requirement and doc.requirement.stage
                else "OTHER"
            )

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


class AdminDocumentsHomeView(LoginRequiredMixin, TemplateView):
    template_name = "admin/documents/all_documents_home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get all applications that have officer involvement
        applications = (
            VisaApplication.objects
            .filter(
                Q(created_by_officer__isnull=False) |
                Q(assigned_officer__isnull=False)
            )
            .select_related(
                "client",
                "client__user",
                "created_by_officer",
                "assigned_officer"
            )
            .prefetch_related("documents")
            .order_by("assigned_officer__user__first_name",
                      "created_by_officer__user__first_name",
                      "-created_at")
        )

        # ===============================
        # 🔥 GROUP BY OFFICER → APPLICATION
        # ===============================

        grouped_data = defaultdict(lambda: {
            "officer": None,
            "applications": []
        })

        for app in applications:

            # Priority: Assigned officer > Created by officer
            officer = app.assigned_officer or app.created_by_officer

            if not officer:
                continue

            officer_id = officer.id

            if not grouped_data[officer_id]["officer"]:
                grouped_data[officer_id]["officer"] = officer

            grouped_data[officer_id]["applications"].append(app)

        context["grouped_applications"] = dict(grouped_data)

        return context



class CaseOfficerApplicationsView(LoginRequiredMixin, TemplateView):
    template_name = "admin/documents/officer_applications.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        officer_id = self.kwargs.get("officer_id")

        officer = get_object_or_404(StaffProfile, pk=officer_id)

        applications = (
            VisaApplication.objects
            .filter(
                Q(created_by_officer=officer) |
                Q(assigned_officer=officer)
            )
            .select_related("client__user")
            .prefetch_related("documents__requirement")
            .order_by("-created_at")
        )

        context["officer"] = officer
        context["applications"] = applications

        return context


class CaseOfficerApplicationDocumentsView(LoginRequiredMixin, TemplateView):
    template_name = "Admin/documents/application_documents.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        application = get_object_or_404(
            VisaApplication.objects.select_related(
                "client__user",
                "created_by_officer",
                "assigned_officer"
            ).prefetch_related(
                "documents__requirement",
                "rejection_letters"
            ),
            pk=self.kwargs["pk"]
        )

        # 🔹 Determine which officer this application belongs to
        officer = application.assigned_officer or application.created_by_officer

        if officer is None:
            raise PermissionDenied("No officer assigned to this application.")

        # 🔹 Group documents by stage
        grouped_documents = defaultdict(list)

        for doc in application.documents.all():
            stage = (
                doc.requirement.stage
                if doc.requirement and doc.requirement.stage
                else "OTHER"
            )
            grouped_documents[stage].append(doc)

        context["application"] = application
        context["grouped_documents"] = dict(grouped_documents)
        context["rejection_letters"] = application.rejection_letters.all()
        context["officer_id"] = officer.id   # ✅ REQUIRED for back button
        context["officer"] = officer

        return context

@login_required
def admin_dashboard_view(request):
    if request.user.role != "Admin":
        return redirect("/")  # role check

    # ✅ All applications initiated by officers
    initiated_count = VisaApplication.objects.filter(
        created_by_officer__isnull=False
    ).count()

    # ✅ All applications assigned to officers
    assigned_count = VisaApplication.objects.filter(
        assigned_officer__isnull=False
    ).count()

    # ✅ Applications for dashboard
    applications = VisaApplication.objects.all()
    applications_count = applications.count()

    # ✅ Status breakdown across all applications
    status_breakdown = (
        applications.values("status")
        .annotate(total=Count("id"))
        .order_by("status")
    )

    admin_review_count = applications.filter(status="ADMIN REVIEW").count()
    awaiting_decision_count = applications.filter(status="SUBMITTED").count()
    complete_count = applications.filter(
        Q(status="APPROVED") | Q(status="REJECTED")
    ).count()

    context = {
        "initiated_count": initiated_count,
        "assigned_count": assigned_count,
        "status_breakdown": status_breakdown,
        "applications": applications,
        "applications_count": applications_count,
        "admin_review_count": admin_review_count,
        "awaiting_decision_count": awaiting_decision_count,
        "complete_count": complete_count,
    }
    return render(request, "admin/admin_dashboard.html", context)


@login_required
def admin_review_list(request):
    return render(request, "admin/admin_review_list.html")


@login_required
def submitted_applications_list(request):
    return render(request, "admin/submitted_applications_list.html")


@login_required
def finalized_applications_list(request):
    return render(request, "admin/finalized_applications_list.html")

