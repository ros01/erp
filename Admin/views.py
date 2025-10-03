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
from Applications.models import VisaApplication
from Documents.models import Document


User = get_user_model()



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

