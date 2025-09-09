from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model, update_session_auth_hash, authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from Applications.models import VisaApplication
from Documents.models import Document

User = get_user_model()


@login_required
def case_officer_dashboard_view(request):
    if request.user.role != "CaseOfficer":
        return redirect("/")  # role check

    # applications = VisaApplication.objects.filter(client=request.user)
    # apps_data = []
    # for app in applications:
    #     docs = Document.objects.filter(application=app).select_related("requirement")
    #     apps_data.append({
    #         "app": app,
    #         "docs": docs
    #     })
    return render(request, "case_officer/case_officer_dashboard.html")