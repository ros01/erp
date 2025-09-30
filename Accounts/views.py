# from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import login as auth_login, authenticate, logout
from django.shortcuts import render, redirect
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model, update_session_auth_hash, authenticate, login as auth_login
from django.contrib import messages, auth
from .models import ClientProfile
from .serializers import ClientRegistrationSerializer
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from Applications.models import VisaApplication
from Documents.models import Document
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash, get_user_model

User = get_user_model()




@login_required
def force_password_reset1(request):
    if request.method == "POST":
        pw1 = request.POST.get("new_password1")
        pw2 = request.POST.get("new_password2")

        if pw1 != pw2:
            messages.error(request, "Passwords do not match.")
        elif len(pw1) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
        else:
            user = request.user
            user.set_password(pw1)
            user.must_reset_password = False  # ✅ clear the flag
            user.save()

            # Keep the user logged in after password change
            update_session_auth_hash(request, user)

            messages.success(request, "Password changed successfully.")
            return redirect("Clients:client_dashboard")

    return render(request, "accounts/reset.html")



def force_password_reset(request):
    if request.method == "POST":
        new_password = request.POST.get("password1")
        confirm_password = request.POST.get("password2")
        user_id = request.session.get("reset_user_id")

        if new_password != confirm_password:
            return render(request, "accounts/reset.html", {"error": "Passwords do not match"})

        user = User.objects.get(id=user_id)
        user.set_password(new_password)
        user.must_reset_password = False  # ✅ reset flag
        user.save()

        # auto-login after reset
        # in force_password_reset
        auth_login(request, user)
        return redirect("Clients:client_dashboard")

    return render(request, "accounts/reset.html")



def login(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, email=email, password=password)

        if user is not None:
            if user.must_reset_password:   # 🚨 check flag
                # don't log them in yet — redirect to reset page
                request.session["reset_user_id"] = user.id
                return redirect("Accounts:force_password_reset")

        if user is not None and user.role == "Client":
            auth_login(request, user)
            return redirect("Clients:client_dashboard")

        elif user is not None and user.role == "Case Officer":
            auth_login(request, user)
            return redirect("CaseManagement:case_officer_dashboard")
        elif user is not None and user.role == "Admin":
            auth_login(request, user)
            return redirect("Admin:admin_dashboard")
        return render(request, "pages/login.html", {"error": "Invalid credentials"})
    return render(request, "pages/login.html")

def logout(request):
  if request.method == 'POST':
    auth.logout(request)
    messages.success(request, 'You are now logged out')
    return redirect('Pages:index')

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


class ClientRegistrationView(generics.CreateAPIView):
    """
    POST /api/clients/register/
    Creates both User (role=Client) and ClientProfile in one request.
    """
    queryset = ClientProfile.objects.all()
    serializer_class = ClientRegistrationSerializer
    permission_classes = [permissions.AllowAny]  # Publicly accessible

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


# class RegisterClientAPIView(generics.CreateAPIView):
#     """
#     Public registration for new clients
#     """
#     serializer_class = UserSerializer
#     permission_classes = []  # allow anyone

#     def create(self, request, *args, **kwargs):
#         data = request.data.copy()
#         data["role"] = "CLIENT"
#         serializer = self.get_serializer(data=data)
#         serializer.is_valid(raise_exception=True)
#         user = serializer.save()
#         return Response(
#             {"detail": "Client registered successfully"},
#             status=status.HTTP_201_CREATED
#         )


# class LoginAPIView(generics.GenericAPIView):
#     """
#     JWT login endpoint
#     """
#     serializer_class = UserSerializer  # reuse for email/password

#     def post(self, request, *args, **kwargs):
#         from django.contrib.auth import authenticate

#         email = request.data.get("email")
#         password = request.data.get("password")
#         user = authenticate(request, username=email, password=password)
#         if not user:
#             return Response({"detail": "Invalid credentials"}, status=400)

#         refresh = RefreshToken.for_user(user)
#         return Response({
#             "refresh": str(refresh),
#             "access": str(refresh.access_token),
#             "role": user.role,
#             "id": user.id,
#         })