from django.shortcuts import render
from .models import VisaApplication
from .serializers import VisaApplicationSerializer
from django.db.models import Count
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from Accounts.models import StaffProfile
from .models import VisaApplication
from django.shortcuts import get_object_or_404
from .models import VisaApplication
from .serializers import VisaApplicationSerializer
import itertools
from collections import defaultdict

# applications/views.py
from CaseManagement.models import ReassignmentLog

class ReassignOfficerView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        officer_id = request.data.get("officer_id")
        try:
            new_officer = StaffProfile.objects.get(pk=officer_id, role="CaseOfficer", is_active=True)
        except StaffProfile.DoesNotExist:
            return Response({"error": "Invalid officer_id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            application = VisaApplication.objects.get(pk=pk)
        except VisaApplication.DoesNotExist:
            return Response({"error": "Application not found"}, status=status.HTTP_404_NOT_FOUND)

        old_officer = application.assigned_officer
        application.assigned_officer = new_officer
        application.save(update_fields=["assigned_officer"])

        # Log reassignment
        ReassignmentLog.objects.create(
            application=application,
            from_officer=old_officer,
            to_officer=new_officer,
            reassigned_by=request.user,
            strategy="manual"
        )

        serializer = VisaApplicationSerializer(application)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BulkReassignOfficerView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        officer_id = request.data.get("officer_id")
        application_ids = request.data.get("application_ids", [])

        try:
            new_officer = StaffProfile.objects.get(pk=officer_id, role="CaseOfficer", is_active=True)
        except StaffProfile.DoesNotExist:
            return Response({"error": "Invalid officer_id"}, status=status.HTTP_400_BAD_REQUEST)

        applications = VisaApplication.objects.filter(pk__in=application_ids)
        updated_apps = []

        for app in applications:
            old_officer = app.assigned_officer
            app.assigned_officer = new_officer
            app.save(update_fields=["assigned_officer"])
            updated_apps.append(app)

            # Log reassignment
            ReassignmentLog.objects.create(
                application=app,
                from_officer=old_officer,
                to_officer=new_officer,
                reassigned_by=request.user,
                strategy="bulk"
            )

        serializer = VisaApplicationSerializer(updated_apps, many=True)
        return Response({
            "message": f"{len(updated_apps)} applications reassigned to {new_officer.user.username}",
            "applications": serializer.data
        }, status=status.HTTP_200_OK)


class BulkAutoReassignView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        strategy = request.data.get("strategy", "round_robin")
        officers = list(StaffProfile.objects.filter(role="CaseOfficer", is_active=True))
        DEFAULT_QUEUE_USERNAME = "default.queue"
        default_user = StaffProfile.objects.filter(user__username=DEFAULT_QUEUE_USERNAME).first()

        apps_to_reassign = VisaApplication.objects.filter(
            assigned_officer=default_user if default_user else None
        )

        updated_apps = []
        if strategy == "round_robin":
            officer_cycle = itertools.cycle(officers)
            for app in apps_to_reassign:
                old_officer = app.assigned_officer
                new_officer = next(officer_cycle)
                app.assigned_officer = new_officer
                app.save(update_fields=["assigned_officer"])
                updated_apps.append(app)

                ReassignmentLog.objects.create(
                    application=app,
                    from_officer=old_officer,
                    to_officer=new_officer,
                    reassigned_by=request.user,
                    strategy="auto-round-robin"
                )

        elif strategy == "workload":
            workload = {
                o.id: VisaApplication.objects.filter(assigned_officer=o, status__in=["pending", "processing"]).count()
                for o in officers
            }
            for app in apps_to_reassign:
                old_officer = app.assigned_officer
                least_loaded_officer_id = min(workload, key=workload.get)
                new_officer = next(o for o in officers if o.id == least_loaded_officer_id)
                app.assigned_officer = new_officer
                app.save(update_fields=["assigned_officer"])
                updated_apps.append(app)
                workload[new_officer.id] += 1

                ReassignmentLog.objects.create(
                    application=app,
                    from_officer=old_officer,
                    to_officer=new_officer,
                    reassigned_by=request.user,
                    strategy="auto-workload"
                )

        serializer = VisaApplicationSerializer(updated_apps, many=True)
        return Response({
            "message": f"{len(updated_apps)} applications auto-reassigned using {strategy} strategy",
            "applications": serializer.data
        }, status=status.HTTP_200_OK)


class BulkAutoReassignView0(APIView):
    """
    Redistribute all unassigned or Default Queue applications
    among available case officers.

    Strategies:
    - round_robin (default): distribute applications evenly in sequence
    - workload: assign to officers with the least active applications
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        strategy = request.data.get("strategy", "round_robin")  # default strategy

        officers = list(StaffProfile.objects.filter(role="CaseOfficer", is_active=True))
        if not officers:
            return Response({"error": "No active case officers available"}, status=status.HTTP_400_BAD_REQUEST)

        DEFAULT_QUEUE_USERNAME = "default.queue"
        default_user = StaffProfile.objects.filter(user__username=DEFAULT_QUEUE_USERNAME).first()

        if default_user:
            apps_to_reassign = VisaApplication.objects.filter(assigned_officer=default_user)
        else:
            apps_to_reassign = VisaApplication.objects.filter(assigned_officer__isnull=True)

        if not apps_to_reassign.exists():
            return Response({"message": "No applications found for auto-reassignment"}, status=status.HTTP_200_OK)

        updated_apps = []

        # --- Strategy: Round Robin ---
        if strategy == "round_robin":
            officer_cycle = itertools.cycle(officers)
            for app in apps_to_reassign:
                officer = next(officer_cycle)
                app.assigned_officer = officer
                app.save(update_fields=["assigned_officer"])
                updated_apps.append(app)

        # --- Strategy: Workload Based ---
        elif strategy == "workload":
            # Count active cases per officer
            workload = {
                officer.id: VisaApplication.objects.filter(assigned_officer=officer, status__in=["pending", "processing"]).count()
                for officer in officers
            }

            for app in apps_to_reassign:
                # Pick officer with minimum workload
                least_loaded_officer_id = min(workload, key=workload.get)
                officer = next(o for o in officers if o.id == least_loaded_officer_id)

                # Assign application
                app.assigned_officer = officer
                app.save(update_fields=["assigned_officer"])
                updated_apps.append(app)

                # Update workload
                workload[officer.id] += 1

        else:
            return Response({"error": "Invalid strategy. Use 'round_robin' or 'workload'."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = VisaApplicationSerializer(updated_apps, many=True)

        return Response({
            "message": f"{len(updated_apps)} applications auto-reassigned across {len(officers)} officers using {strategy} strategy",
            "applications": serializer.data
        }, status=status.HTTP_200_OK)


class BulkAutoReassignView0(APIView):
    """
    Redistribute all unassigned or Default Queue applications
    evenly among available case officers.
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        # Fetch active case officers
        officers = list(StaffProfile.objects.filter(role="CaseOfficer", is_active=True))
        if not officers:
            return Response({"error": "No active case officers available"}, status=status.HTTP_400_BAD_REQUEST)

        # Find Default Queue user (if configured)
        DEFAULT_QUEUE_USERNAME = "default.queue"
        default_user = StaffProfile.objects.filter(user__username=DEFAULT_QUEUE_USERNAME).first()

        # Get applications to redistribute
        if default_user:
            apps_to_reassign = VisaApplication.objects.filter(
                assigned_officer=default_user
            )
        else:
            apps_to_reassign = VisaApplication.objects.filter(assigned_officer__isnull=True)

        if not apps_to_reassign.exists():
            return Response({"message": "No applications found for auto-reassignment"}, status=status.HTTP_200_OK)

        # Round-robin assignment across officers
        officer_cycle = itertools.cycle(officers)
        updated_apps = []
        for app in apps_to_reassign:
            officer = next(officer_cycle)
            app.assigned_officer = officer
            app.save(update_fields=["assigned_officer"])
            updated_apps.append(app)

        serializer = VisaApplicationSerializer(updated_apps, many=True)

        return Response({
            "message": f"{len(updated_apps)} applications auto-reassigned across {len(officers)} officers",
            "applications": serializer.data
        }, status=status.HTTP_200_OK)


class BulkReassignOfficerView0(APIView):
    """
    Allows an admin to reassign multiple VisaApplications
    (e.g. from Default Queue) to a new officer in bulk.
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        officer_id = request.data.get("officer_id")
        application_ids = request.data.get("application_ids", [])

        if not officer_id:
            return Response({"error": "officer_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not application_ids:
            return Response({"error": "application_ids list is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate officer
        try:
            new_officer = StaffProfile.objects.get(pk=officer_id, role="CaseOfficer", is_active=True)
        except StaffProfile.DoesNotExist:
            return Response({"error": "Invalid officer_id"}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch applications
        applications = VisaApplication.objects.filter(pk__in=application_ids)

        updated_apps = []
        for app in applications:
            app.assigned_officer = new_officer
            app.save(update_fields=["assigned_officer"])
            updated_apps.append(app)

        serializer = VisaApplicationSerializer(updated_apps, many=True)

        return Response({
            "message": f"{len(updated_apps)} applications reassigned to {new_officer.user.username}",
            "applications": serializer.data
        }, status=status.HTTP_200_OK)



class ReassignOfficerView0(APIView):
    """
    Allows an admin to reassign a VisaApplication to a new officer.
    Intended for moving from 'Default Queue' to a real officer.
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        application = get_object_or_404(VisaApplication, pk=pk)
        officer_id = request.data.get("officer_id")

        if not officer_id:
            return Response({"error": "officer_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_officer = StaffProfile.objects.get(pk=officer_id, role="CaseOfficer", is_active=True)
        except StaffProfile.DoesNotExist:
            return Response({"error": "Invalid officer_id"}, status=status.HTTP_400_BAD_REQUEST)

        application.assigned_officer = new_officer
        application.save(update_fields=["assigned_officer"])

        return Response({
            "message": f"Application {application.reference_no} reassigned to {new_officer.user.username}",
            "application": VisaApplicationSerializer(application).data
        }, status=status.HTTP_200_OK)



class AutoAssignOfficerView(APIView):
    """
    Automatically assigns an unassigned VisaApplication
    to the officer with the least workload.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            application = VisaApplication.objects.get(pk=pk, assigned_officer__isnull=True)
        except VisaApplication.DoesNotExist:
            return Response({"error": "Application not found or already assigned"},
                            status=status.HTTP_404_NOT_FOUND)

        # Find officer with least open applications
        officers = StaffProfile.objects.filter(role="CaseOfficer", is_active=True) \
            .annotate(open_cases=Count("assigned_applications", filter=~Q(assigned_applications__status="completed"))) \
            .order_by("open_cases")

        if not officers.exists():
            return Response({"error": "No active case officers available"},
                            status=status.HTTP_400_BAD_REQUEST)

        selected_officer = officers.first()
        application.assigned_officer = selected_officer
        application.save()

        return Response({
            "message": f"Application {application.reference_no} assigned to {selected_officer.user.username}",
            "application": VisaApplicationSerializer(application).data
        }, status=status.HTTP_200_OK)


class VisaApplicationCreateView(generics.CreateAPIView):
    """
    Confirmation step: Creates a VisaApplication
    and auto-generates checklist docs.
    """
    queryset = VisaApplication.objects.all()
    serializer_class = VisaApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(client=self.request.user)


class VisaApplicationListView(generics.ListAPIView):
    serializer_class = VisaApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return VisaApplication.objects.filter(client=self.request.user)

