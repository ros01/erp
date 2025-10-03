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
from Applications.models import VisaApplication, PreviousRefusalLetter
from Accounts.models import ClientProfile
from Documents.models import Document
from django.views.generic import TemplateView, ListView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated



User = get_user_model()



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
def application_documents(request, pk):
    app = get_object_or_404(VisaApplication, id=pk)
    client_profile = app.client  # access the related client
    return render(
        request,
        "case_officer/application_documents.html",
        {"application": app, "client_profile": client_profile},
    )



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