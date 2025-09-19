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
def admin_dashboard_view(request):
    if request.user.role != "Admin":
        return redirect("/")  # role check
    return render(request, "admin/admin_dashboard.html")

