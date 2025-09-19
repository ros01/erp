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
from django.db.models import Count
from Applications.models import VisaApplication
from Documents.models import Document


User = get_user_model()



@login_required
def case_officer_dashboard_view(request):
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


@login_required
def applications_list(request):
    return render(request, "case_officer/applications_list.html")



@login_required
def application_details(request, pk):
    app = get_object_or_404(VisaApplication, pk=pk)
    return render(
        request,
        "case_officer/application_details.html",
        {"application_id": str(app.id)}  # pass only ID, frontend fetches details via API
    )


# views.py
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


# views.py
@login_required
def form_processing_submission(request):
    # app = get_object_or_404(VisaApplication, pk=pk)

    # try:
    #     form_processing = app.form_processing
    # except FormProcessing.DoesNotExist:
    #     form_processing = None

    # if request.method == "POST":
    #     form = FormProcessingForm(request.POST, request.FILES, instance=form_filled)  # ✅ include request.FILES
    #     if form.is_valid():
    #         form_instance = form.save(commit=False)
    #         form_instance.application = app
    #         form_instance.save()  # triggers status change to ADMIN REVIEW
    #         return redirect("CaseManagement:application-details", pk=app.pk)
    # else:
    #     form = FormFilledForm(instance=form_filled)

    return render(request, "case_officer/form_processing.html")
    #     , {
    #     "form": form,
    #     "application": app,
    # }

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