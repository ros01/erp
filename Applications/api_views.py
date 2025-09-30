from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.generics import RetrieveAPIView
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Q, Value
from Documents.models import DocumentRequirement, Document
from Accounts.models import *
from .models import VisaApplication
from Documents.serializers import DocumentRequirementSerializer
from .serializers import (
    DocumentRequirementSerializer,
    VisaApplicationSerializer,
    VisaApplicationsSerializer,
    VisaApplicationDetailSerializer,
    DocumentSerializer,
    VisaApplicationUrlUpdateSerializer,
    # FormProcessingSerializer,
)
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from Accounts.choices import *
from Documents.serializers import CountrySerializer, VisaTypeSerializer
import uuid
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.db.models import Value


User = get_user_model()

# class FormProcessingDetailUpdateAPIView(generics.RetrieveUpdateAPIView):
#     serializer_class = FormProcessingSerializer
#     permission_classes = [IsAuthenticated]

#     def get_object(self):
#         app_id = self.kwargs["pk"]
#         application = get_object_or_404(VisaApplication, pk=app_id)
#         # Auto-create FormFilled record if it doesn’t exist
#         form_processing, _ = FormProcessing.objects.get_or_create(application=application)
#         return form_processing

class AddVisaApplicationDecisionAPIView(APIView):
    def patch(self, request, pk):
        try:
            application = VisaApplication.objects.get(pk=pk)
        except VisaApplication.DoesNotExist:
            return Response({"error": "Application not found"}, status=404)

        decision = request.data.get("status")
        if decision not in ["APPROVED", "REJECTED"]:
            return Response({"error": "Invalid decision"}, status=400)

        # ✅ Update application decision
        application.status = decision
        application.decision_date = timezone.now()
        application.save(update_fields=["status", "decision_date", "updated_at"])

        # ✅ Decrease workload on officer if assigned or created
        staff = application.assigned_officer or application.created_by_officer
        if staff and staff.workload > 0:
            staff.workload -= 1
            staff.save(update_fields=["workload"])

        return Response(VisaApplicationSerializer(application).data)



class FinalizeVisaApplicationAPIView(APIView):
    def patch(self, request, pk):
        app = get_object_or_404(VisaApplication, pk=pk)

        # Only finalize if not already submitted
        if app.status != "SUBMITTED":
            app.status = "SUBMITTED"
            app.submission_date = timezone.now()
            app.save(update_fields=["status", "submission_date"])

        serializer = VisaApplicationSerializer(app)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VisaApplicationUrlUpdateAPIView(generics.UpdateAPIView):
    queryset = VisaApplication.objects.all()
    serializer_class = VisaApplicationUrlUpdateSerializer
    lookup_field = "id"   # so PATCH /api/applications/<id>/add-url/



class AdminVisaApplicationListAPIView(generics.ListAPIView):
    serializer_class = VisaApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            VisaApplication.objects
            .filter(status="ADMIN REVIEW")
            .select_related("client", "assigned_officer__user")
            .order_by("-created_at")
        )

class DocumentReviewAPIView(generics.UpdateAPIView):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    def perform_update(self, serializer):
        doc = serializer.save(
            verified=True,
            status="REVIEWED",
            verified_by=self.request.user
        )

        # check if all mandatory documents are reviewed
        app = doc.application
        pending_docs = app.documents.filter(
            Q(requirement__is_mandatory=True) & ~Q(status="REVIEWED")
        )
        if not pending_docs.exists():
            app.status = "REVIEWED"
            app.save(update_fields=["status"])


class DocumentUploadAPIView(APIView):
    """
    Upload a file for a specific Document.
    Clients: can upload only their own application documents.
    Case Officers: can upload for any client.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        user = request.user
        file = request.FILES.get("file")

        if not file:
            return Response({"detail": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        # Case Officer or Admin -> full access
        if user.role in ["Case Officer", "Admin"]:
            doc = get_object_or_404(Document, pk=pk)

        # Client -> restricted to their own documents
        elif user.role == "Client":
            try:
                client_profile = user.client_profile
            except ClientProfile.DoesNotExist:
                return Response({"detail": "Client profile not found."}, status=status.HTTP_400_BAD_REQUEST)

            doc = get_object_or_404(Document, pk=pk, application__client=client_profile)

        else:
            return Response({"detail": "You do not have permission to upload files."}, status=status.HTTP_403_FORBIDDEN)

        # Save uploaded file
        doc.file = file
        doc.status = "UPLOADED"
        doc.save()

        return Response({
            "id": str(doc.id),
            "requirement": doc.requirement.name,
            "status": doc.status,
            "file_url": doc.file.url if doc.file else None,
        }, status=status.HTTP_200_OK)



class VisaApplicationListAPIView(generics.ListCreateAPIView, generics.RetrieveUpdateAPIView):
    queryset = VisaApplication.objects.all()
    serializer_class = VisaApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = VisaApplication.objects.all()

        if user.role == "Client":
            qs = qs.filter(client=user.client_profile)

        elif user.role == "Case Officer":
            qs = qs.filter(Q(assigned_officer=user.staff_profile) | Q(created_by_officer=user.staff_profile))

        elif user.role in ["Admin", "Finance", "Support"] or user.is_superuser:
            qs = qs

        else:
            return qs.none()



        # Default ordering: newest first
        return qs.order_by("-created_at")

        # ✅ Order by submission_date (if present), otherwise created_at, descending
        # return qs.order_by(
        #     Coalesce("submission_date", "created_at").desc(nulls_last=True)
        # )

class VisaApplicationListReviewAPIView(generics.ListAPIView):
    serializer_class = VisaApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = VisaApplication.objects.all()

        if user.role == "Client":
            qs = qs.filter(client=user.client_profile)

        elif user.role == "Case Officer":
            qs = qs.filter(Q(assigned_officer=user.staff_profile) | Q(created_by_officer=user.staff_profile))

        elif user.role in ["Admin", "Finance", "Support"] or user.is_superuser:
            pass  # keep all

        else:
            return qs.none()

        # 🔹 only show ASSIGNED or INITIATED apps
        qs = qs.filter(Q(status="ASSIGNED") | Q(status="INITIATED"))

        return qs.order_by("-created_at")

        # 🔹 sort by submission_date first, else created_at
        # return qs.order_by(Coalesce("submission_date", "created_at").desc())


class ReviewedVisaApplicationListAPIView(generics.ListAPIView):
    serializer_class = VisaApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = VisaApplication.objects.all()

        if user.role == "Client":
            qs = qs.filter(client=user.client_profile)

        elif user.role == "Case Officer":
            qs = qs.filter(Q(assigned_officer=user.staff_profile) | Q(created_by_officer=user.staff_profile))

        elif user.role in ["Admin", "Finance", "Support"] or user.is_superuser:
            pass  # keep all

        else:
            return qs.none()

        # 🔹 only show ASSIGNED or INITIATED apps
        qs = qs.filter(status="REVIEWED")

        return qs.order_by("-created_at")


class SubmittedVisaApplicationListAPIView(generics.ListAPIView):
    serializer_class = VisaApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]


    def get_queryset(self):
        user = self.request.user
        qs = VisaApplication.objects.all()

        if user.role == "Client":
            qs = qs.filter(client=user.client_profile)

        elif user.role == "Case Officer":
            qs = qs.filter(Q(assigned_officer=user.staff_profile) | Q(created_by_officer=user.staff_profile))

        elif user.role in ["Admin", "Finance", "Support"] or user.is_superuser:
            pass  # keep all

        else:
            return qs.none()

        # 🔹 only show ASSIGNED or INITIATED apps
        qs = qs.filter(status="SUBMITTED")

        return qs.order_by("-created_at")

class FinalizedVisaApplicationsListAPIView(generics.ListAPIView):
    serializer_class = VisaApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = VisaApplication.objects.all()

        if user.role == "Client":
            qs = qs.filter(client=user.client_profile)

        elif user.role == "Case Officer":
            qs = qs.filter(Q(assigned_officer=user.staff_profile) | Q(created_by_officer=user.staff_profile))

        elif user.role in ["Admin", "Finance", "Support"] or user.is_superuser:
            pass  # keep all

        else:
            return qs.none()

        qs = qs.filter(
                        Q(status="APPROVED") |
                        Q(status="REJECTED") 
                    )

        # 🔹 sort by submission_date first, else created_at
        return qs.order_by(Coalesce("submission_date", "created_at").desc())


class VisaApplicationDetailAPIView(RetrieveAPIView):
    queryset = VisaApplication.objects.all()
    serializer_class = VisaApplicationDetailSerializer
    lookup_field = "id"  # since frontend fetches /api/applications/<id>/





    # def get_serializer_context(self):
    #     ctx = super().get_serializer_context()
    #     # If `id` in kwargs → detail mode, else list mode
    #     ctx["list_mode"] = self.kwargs.get("id") is None
    #     return ctx


class ApplicationDocumentsListAPIView(APIView):
    """
    List all documents + statuses for a specific VisaApplication.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, application_id, *args, **kwargs):
        try:
            client_profile = request.user.client_profile
        except ClientProfile.DoesNotExist:
            return Response({"detail": "Client profile not found."}, status=status.HTTP_400_BAD_REQUEST)

        application = get_object_or_404(VisaApplication, pk=application_id, client=client_profile)

        docs = application.documents.select_related("requirement").all()
        data = [{
            "id": d.id,
            "requirement": d.requirement.name,
            "status": d.status,
            "file_url": d.file.url if d.file else None
        } for d in docs]

        return Response({
            "application": application.id,
            "documents": data
        }, status=status.HTTP_200_OK)


def generate_reference_no():
    return str(uuid.uuid4())[:12].upper()

    
class CountryChoicesView(APIView):
    """
    Returns the restricted COUNTRY_CHOICES from the model.
    """
    def get(self, request, *args, **kwargs):
        # Grab distinct country choices actually in use
        countries = [
            {"code": code, "name": label}
            for code, label in NATIONALITY
        ]
        return Response(countries)


class CountryListAPIView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        countries = (
            DocumentRequirement.objects
            .values_list("country", flat=True)
            .distinct()
        )
        data = [{"code": c, "name": c} for c in countries]
        return Response(data)


class VisaTypeListAPIView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        country = request.query_params.get("country")
        qs = DocumentRequirement.objects.all()
        if country:
            qs = qs.filter(country=country)
        visa_types = qs.values_list("visa_type", flat=True).distinct()
        data = [{"code": v, "name": v} for v in visa_types]
        return Response(data)


class RequirementListAPIView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = DocumentRequirementSerializer

    def get_queryset(self):
        country = self.request.query_params.get("country")
        visa_type = self.request.query_params.get("visa_type")
        qs = DocumentRequirement.objects.all()
        if country:
            qs = qs.filter(country=country)
        if visa_type:
            qs = qs.filter(visa_type=visa_type)
        return qs



class ClientSearchAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        query = request.query_params.get("q", "").strip()
        qs = ClientProfile.objects.select_related("user")
        if query:
            qs = qs.filter(
                Q(user__email__icontains=query) |
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query)
            )

        results = [
            {
                "id": c.id,
                "name": c.user.get_full_name,
                "email": c.user.email,
                "passport_number": c.passport_number,
            }
            for c in qs[:20]
        ]
        return Response(results)


class ClientCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data
        email = data.get("email")
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        passport_number = data.get("passport_number")
        nationality = data.get("nationality")
        dob = data.get("date_of_birth")

        if not email or not passport_number:
            return Response(
                {"detail": "Email and passport number required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ check duplicate email
        if User.objects.filter(email=email).exists():
            return Response(
                {"detail": "User with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ check duplicate passport
        if ClientProfile.objects.filter(passport_number=passport_number).exists():
            return Response(
                {"detail": "Client with this passport number already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ create user with default password
        user = User.objects.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role="Client",
            password="Suave@123%"  # hashed internally
        )

        # ✅ enforce password reset on first login
        user.must_reset_password = True
        user.save()

        # ✅ create client profile
        client = ClientProfile.objects.create(
            user=user,
            passport_number=passport_number,
            nationality=nationality,
            date_of_birth=dob
        )

        return Response({
            "id": client.id,
            "name": user.get_full_name,
            "email": user.email,
            "passport_number": client.passport_number,
        }, status=status.HTTP_201_CREATED)




class ApplicationCreateAPICaseView(generics.GenericAPIView):
    serializer_class = VisaApplicationSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        client_id = request.data.get("client_id")
        country = request.data.get("country")
        visa_type = request.data.get("visa_type")

        if not client_id or not country or not visa_type:
            return Response(
                {"detail": "client_id, country, and visa_type required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        client_profile = get_object_or_404(ClientProfile, id=client_id)

        # ✅ assign logged-in officer
        staff_profile = getattr(request.user, "staff_profile", None)

        application = VisaApplication.objects.create(
            client=client_profile,
            country=country,
            visa_type=visa_type,
            status="INITIATED",
            reference_no=generate_reference_no(),
            # assigned_officer=staff_profile,     # ✅ officer is currently assigned
            created_by_officer=staff_profile,   # ✅ officer initiated the app
        )


        # Auto-create docs
        requirements = DocumentRequirement.objects.filter(
            country=country, visa_type=visa_type
        )
        Document.objects.bulk_create([
            Document(application=application, requirement=req, status="MISSING")
            for req in requirements
        ])

        return Response(
            self.get_serializer(application).data,
            status=status.HTTP_201_CREATED,
        )


class ApplicationCreateAPIView(generics.GenericAPIView):
    """
    Confirm Application:
    Creates VisaApplication + auto-generates Document placeholders
    """
    serializer_class = VisaApplicationSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        country = request.data.get("country")
        visa_type = request.data.get("visa_type")

        if not country or not visa_type:
            return Response(
                {"detail": "country and visa_type are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            client_profile = request.user.client_profile
        except ClientProfile.DoesNotExist:
            return Response(
                {"detail": "No client profile associated with this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Always create a new application (no deduplication)
        application = VisaApplication.objects.create(
            client=client_profile,
            country=country,
            visa_type=visa_type,
            status="QUEUED",
            reference_no=generate_reference_no(),
        )

        # Auto-create docs from requirements
        requirements = DocumentRequirement.objects.filter(
            country=country, visa_type=visa_type
        )
        Document.objects.bulk_create([
            Document(application=application, requirement=req, status="MISSING")
            for req in requirements
        ])

        return Response(
            self.get_serializer(application).data,
            status=status.HTTP_201_CREATED,
        )



class ApplicationCreateAPICaseView0(generics.GenericAPIView):
    serializer_class = VisaApplicationSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        client_id = request.data.get("client_id")
        country = request.data.get("country")
        visa_type = request.data.get("visa_type")

        if not client_id or not country or not visa_type:
            return Response({"detail": "client_id, country, and visa_type required"},
                            status=status.HTTP_400_BAD_REQUEST)

        client_profile = get_object_or_404(ClientProfile, id=client_id)

        application = VisaApplication.objects.create(
            client=client_profile,
            country=country,
            visa_type=visa_type,
            status="INITIATED",
            reference_no=generate_reference_no(),
        )

        # Auto-create docs
        requirements = DocumentRequirement.objects.filter(
            country=country, visa_type=visa_type
        )
        Document.objects.bulk_create([
            Document(application=application, requirement=req, status="MISSING")
            for req in requirements
        ])

        return Response(
            self.get_serializer(application).data,
            status=status.HTTP_201_CREATED,
        )

class ApplicationCreateAPICaseView00(generics.GenericAPIView):
    serializer_class = VisaApplicationSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        country = request.data.get("country")
        visa_type = request.data.get("visa_type")
        client_name = request.data.get("client_name")
        client_email = request.data.get("client_email")

        if not country or not visa_type or not client_name or not client_email:
            return Response(
                {"detail": "country, visa_type, client_name and client_email are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create VisaApplication
        application = VisaApplication.objects.create(
            country=country,
            visa_type=visa_type,
            status="QUEUED",
            reference_no=generate_reference_no(),
            client_name=client_name,
            client_email=client_email,
        )

        # Auto-create docs from requirements
        requirements = DocumentRequirement.objects.filter(
            country=country, visa_type=visa_type
        )
        Document.objects.bulk_create([
            Document(application=application, requirement=req, status="MISSING")
            for req in requirements
        ])

        return Response(
            self.get_serializer(application).data,
            status=status.HTTP_201_CREATED,
        )



class VisaApplicationsListAPIView00(generics.ListAPIView, generics.RetrieveAPIView):
    queryset = VisaApplication.objects.all().select_related("assigned_officer__user")
    serializer_class = VisaApplicationsSerializer
    lookup_field = "id"

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["list_mode"] = self.kwargs.get("id") is None  # True in list, False in detail
        return ctx


    # def get_serializer_context(self):
    #     ctx = super().get_serializer_context()
    #     # mark list mode vs detail mode
    #     ctx["list_mode"] = self.action == "list" if hasattr(self, "action") else self.request.parser_context.get("kwargs", {}).get("id") is None
    #     return ctx



class VisaApplicationDetailAPIView00(generics.RetrieveAPIView):
    queryset = VisaApplication.objects.all()
    serializer_class = VisaApplicationSerializer
    lookup_field = "id"  # since frontend fetches /api/applications/<id>/



class CountryListAPIView1(APIView):
    """
    Returns only countries that have at least one DocumentRequirement.
    """
    def get(self, request, *args, **kwargs):
        # Get unique country codes from requirements
        countries = (
            DocumentRequirement.objects
            .values_list("country", flat=True)
            .distinct()
        )
        # Convert codes to display names
        choices_dict = dict(DocumentRequirement.COUNTRIES)
        data = [{"code": c, "name": choices_dict.get(c, c)} for c in countries]
        return Response(CountrySerializer(data, many=True).data)
        
class VisaTypeListAPIView1(APIView):
    """
    Returns visa types available for a given country,
    based only on existing DocumentRequirement entries.
    """
    def get(self, request, *args, **kwargs):
        country = request.query_params.get("country")
        if not country:
            return Response({"error": "country query param is required"}, status=400)

        visa_types = (
            DocumentRequirement.objects
            .filter(country=country)
            .values_list("visa_type", flat=True)
            .distinct()
        )

        choices_dict = dict(DocumentRequirement.VISA_TYPES)
        data = [{"code": v, "name": choices_dict.get(v, v)} for v in visa_types]
        return Response(VisaTypeSerializer(data, many=True).data)

class ApplicationCreateAPIView00(generics.GenericAPIView):
    """
    Confirm Application:
    Creates VisaApplication + auto-generates Document placeholders
    """
    serializer_class = VisaApplicationSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        country = request.data.get("country")
        visa_type = request.data.get("visa_type")

        if not country or not visa_type:
            return Response(
                {"detail": "country and visa_type are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            client_profile = request.user.client_profile
        except ClientProfile.DoesNotExist:
            return Response(
                {"detail": "No client profile associated with this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Prevent duplicates
        existing = VisaApplication.objects.filter(
            client=client_profile,
            country=country,
            visa_type=visa_type,
        ).first()
        if existing:
            return Response(
                self.get_serializer(existing).data,
                status=status.HTTP_200_OK,
            )

        # Create application
        application = VisaApplication.objects.create(
            client=client_profile,
            country=country,
            visa_type=visa_type,
            status="PENDING",
            reference_no=generate_reference_no(),
        )

        # Auto-create docs from requirements
        requirements = DocumentRequirement.objects.filter(
            country=country, visa_type=visa_type
        )
        Document.objects.bulk_create([
            Document(application=application, requirement=req, status="MISSING")
            for req in requirements
        ])

        return Response(
            self.get_serializer(application).data,
            status=status.HTTP_201_CREATED,
        )


class ApplicationCreateAPIView0(generics.GenericAPIView):
    serializer_class = VisaApplicationSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        country = request.data.get("country")
        visa_type = request.data.get("visa_type")

        if not country or not visa_type:
            return Response(
                {"detail": "country and visa_type are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            client_profile = request.user.clientprofile
        except ClientProfile.DoesNotExist:
            return Response(
                {"detail": "No client profile associated with this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Prevent duplicates: one active application per client per country+visa_type
        existing = VisaApplication.objects.filter(
            client=client_profile,
            country=country,
            visa_type=visa_type,
        ).first()
        if existing:
            return Response(
                self.get_serializer(existing).data,
                status=status.HTTP_200_OK,
            )

        # Create application
        application = VisaApplication.objects.create(
            client=client_profile,
            country=country,
            visa_type=visa_type,
            status="PENDING",
            reference_no=generate_reference_no(),  # helper to generate unique ref
        )

        # Auto-create documents from requirements
        requirements = DocumentRequirement.objects.filter(
            country=country, visa_type=visa_type
        )
        Document.objects.bulk_create([
            Document(application=application, requirement=req, status="MISSING")
            for req in requirements
        ])

        return Response(
            self.get_serializer(application).data,
            status=status.HTTP_201_CREATED,
        )


class ApplicationCreateAPIView1(generics.GenericAPIView):
    """
    Confirm Application:
    Creates VisaApplication + auto-generates Document placeholders
    """
    serializer_class = VisaApplicationSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        country = request.data.get("country")
        visa_type = request.data.get("visa_type")

        if not country or not visa_type:
            return Response(
                {"detail": "country and visa_type are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Prevent duplicates: one active application per client per country+visa_type
        existing = VisaApplication.objects.filter(
            client=request.user,
            country=country,
            visa_type=visa_type,
        ).first()
        if existing:
            return Response(
                self.get_serializer(existing).data,
                status=status.HTTP_200_OK,
            )

        # Create application
        application = VisaApplication.objects.create(
            client=request.user,
            country=country,
            visa_type=visa_type,
            status="PENDING",
        )

        # Auto-create documents from requirements
        requirements = DocumentRequirement.objects.filter(country=country, visa_type=visa_type)
        Document.objects.bulk_create([
            Document(application=application, requirement=req, status="MISSING")
            for req in requirements
        ])

        return Response(
            self.get_serializer(application).data,
            status=status.HTTP_201_CREATED,
        )



#

class ApplicationCreateAPIView2(generics.GenericAPIView):
    """
    Confirm Application:
    Creates VisaApplication + auto-generates Document placeholders
    """
    serializer_class = VisaApplicationSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        country = request.data.get("country")
        visa_type = request.data.get("visa_type")

        if not country or not visa_type:
            return Response(
                {"detail": "country and visa_type are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Prevent duplicates: one active application per client per country+visa_type
        existing = VisaApplication.objects.filter(
            client=request.user,
            country=country,
            visa_type=visa_type,
        ).first()
        if existing:
            return Response(
                self.get_serializer(existing).data,
                status=status.HTTP_200_OK,
            )

        # Create application
        application = VisaApplication.objects.create(
            client=request.user,
            country=country,
            visa_type=visa_type,
            status="DRAFT",
        )

        # Auto-create documents from requirements
        requirements = DocumentRequirement.objects.filter(country=country, visa_type=visa_type)
        Document.objects.bulk_create([
            Document(application=application, requirement=req, status="MISSING")
            for req in requirements
        ])

        return Response(
            self.get_serializer(application).data,
            status=status.HTTP_201_CREATED,
        )





class ApplicationCreateAPIView3(generics.GenericAPIView):
    """
    Confirm Application:
    Creates VisaApplication + auto-generates Document placeholders
    """
    serializer_class = VisaApplicationSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        country = request.data.get("country")
        visa_type = request.data.get("visa_type")

        if not country or not visa_type:
            return Response(
                {"detail": "country and visa_type are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create the application for the logged-in client
        application = VisaApplication.objects.create(
            client=request.user,
            country=country,
            visa_type=visa_type,
            status="PENDING",
        )

        # Auto-create Document placeholders
        requirements = DocumentRequirement.objects.filter(country=country, visa_type=visa_type)
        Document.objects.bulk_create([
            Document(application=application, requirement=req, status="MISSING")
            for req in requirements
        ])

        return Response(
            self.get_serializer(application).data,
            status=status.HTTP_201_CREATED,
        )



class VisaApplicationListAPIView0(generics.ListAPIView):
    serializer_class = VisaApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        try:
            client_profile = self.request.user.client_profile
        except ClientProfile.DoesNotExist:
            return VisaApplication.objects.none()
        return VisaApplication.objects.filter(client=client_profile).order_by("-created_at")


class VisaApplicationDetailAPIView0(generics.RetrieveAPIView):
    """
    Returns a single visa application with its details & documents.
    """
    serializer_class = VisaApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        try:
            client_profile = self.request.user.client_profile
        except Exception:
            return VisaApplication.objects.none()
        return VisaApplication.objects.filter(client=client_profile)


class AddVisaApplicationDecision00APIView(APIView):
    def patch(self, request, pk):
        try:
            application = VisaApplication.objects.get(pk=pk)
        except VisaApplication.DoesNotExist:
            return Response({"error": "Application not found"}, status=404)

        decision = request.data.get("status")
        if decision not in ["APPROVED", "REJECTED"]:
            return Response({"error": "Invalid decision"}, status=400)

        application.status = decision
        application.save(update_fields=["status", "updated_at"])
        return Response(VisaApplicationSerializer(application).data)


class AddVisaApplicationDecisionsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk=None, *args, **kwargs):
        app_id = pk or kwargs.get("pk")
        application = get_object_or_404(VisaApplication, id=app_id)

        decision = request.data.get("status")
        if decision not in ["APPROVED", "REJECTED"]:
            return Response(
                {"error": "Invalid status. Must be APPROVED or REJECTED."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Update status and decision_date
        application.status = decision
        application.decision_date = timezone.now().date()
        application.save()

        serializer = VisaApplicationSerializer(application)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AddVisaApplicationDecisionListAPIView(APIView):
    def patch(self, request, pk):
        app = get_object_or_404(VisaApplication, pk=pk)

        # Only finalize if not already submitted
        if app.status != "SUBMITTED":
            app.status = "SUBMITTED"
            app.submission_date = timezone.now().date()  # ✅ only store date
            app.save(update_fields=["status", "submission_date"])

        serializer = VisaApplicationSerializer(app)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VisaApplicationsListAPIView(generics.ListAPIView, generics.RetrieveAPIView):
    serializer_class = VisaApplicationsSerializer
    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user
        qs = VisaApplication.objects.all().select_related("assigned_officer__user")

        if user.role == "Client":
            # Client sees only their own applications
            qs = qs.filter(client=user.client_profile)

        elif user.role == "Case Officer":
            # Case officer sees only their assigned applications
            qs = qs.filter(assigned_officer=user.staff_profile)

        elif user.role in ["Admin", "Finance", "Support"] or user.is_superuser:
            # Admin, Finance, Support, and superusers see all applications
            qs = qs

        else:
            return qs.none()

        # Default ordering: newest first
        return qs.order_by("-created_at")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        # mark list mode vs detail mode
        ctx["list_mode"] = self.action == "list" if hasattr(self, "action") else self.request.parser_context.get("kwargs", {}).get("id") is None
        return ctx


class DocumentUploadAPIView000(APIView):
    """
    Upload a file for a specific Document (linked to a VisaApplication).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        try:
            client_profile = request.user.client_profile
        except ClientProfile.DoesNotExist:
            return Response({"detail": "Client profile not found."}, status=status.HTTP_400_BAD_REQUEST)

        doc = get_object_or_404(Document, pk=pk, application__client=client_profile)
        file = request.FILES.get("file")

        if not file:
            return Response({"detail": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        doc.file = file
        doc.status = "UPLOADED"
        doc.save()

        return Response({
            "id": doc.id,
            "requirement": doc.requirement.name,
            "status": doc.status,
            "file_url": doc.file.url if doc.file else None,
        }, status=status.HTTP_200_OK)


class VisaApplicationListReviewAPIViewOld(generics.ListAPIView):
    serializer_class = VisaApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Start with all applications
        qs = VisaApplication.objects.all().select_related("assigned_officer__user")

        if user.role == "Client":
            qs = qs.filter(client=user.client_profile)

        elif user.role == "Case Officer":
            qs = qs.filter(assigned_officer=user.staff_profile)

        elif user.role in ["Admin", "Finance", "Support"] or user.is_superuser:
            pass  # keep all

        else:
            return qs.none()

        # 🔹 Final filter: only ASSIGNED applications
        qs = qs.filter(status="ASSIGNED")

        # 🔹 Sort: submission_date first, else created_at
        return qs.order_by(Coalesce("submission_date", "created_at").desc())

class VisaApplicationListReviewAPIView011(generics.ListAPIView):
    serializer_class = VisaApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = VisaApplication.objects.all().select_related("assigned_officer__user")

        if user.role == "Client":
            qs = qs.filter(client=user.client_profile)

        elif user.role == "Case Officer":
            qs = qs.filter(assigned_officer=user.staff_profile)

        elif user.role in ["Admin", "Finance", "Support"] or user.is_superuser:
            pass  # keep all

        else:
            return qs.none()

        # 🔹 only show ASSIGNED apps
        qs = qs.filter(status="ASSIGNED")

        # 🔹 sort by submission_date first, else created_at
        return qs.order_by(Coalesce("submission_date", "created_at").desc())




class VisaApplicationListReviewAPIView0000(generics.ListCreateAPIView, generics.RetrieveUpdateAPIView):
    queryset = VisaApplication.objects.all()
    serializer_class = VisaApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = VisaApplication.objects.all().select_related("assigned_officer__user")

        if user.role == "Client":
            # Client sees only their own applications
            qs = qs.filter(client=user.client_profile)

        elif user.role == "Case Officer":
            # Case officer sees only their assigned applications
            qs = qs.filter(assigned_officer=user.staff_profile)

        elif user.role in ["Admin", "Finance", "Support"] or user.is_superuser:
            # Admin, Finance, Support, and superusers see all applications
            qs = qs

        else:
            return qs.none()

        # Sort: submission_date first (if available), else created_at
        # return qs.order_by("-created_at")
        return qs.order_by(Coalesce("submission_date", "created_at").desc())


class VisaApplicationListAPIView1(generics.ListCreateAPIView, generics.RetrieveUpdateAPIView):
    """
    Returns a paginated list of visa applications
    belonging to the logged-in client.
    """
    queryset = VisaApplication.objects.all()
    serializer_class = VisaApplicationsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = VisaApplication.objects.all().select_related("assigned_officer__user")

        if user.role == "Client":
            # Client sees only their own applications
            qs = qs.filter(client=user.client_profile)

        elif user.role == "Case Officer":
            # Case officer sees only their assigned applications
            qs = qs.filter(assigned_officer=user.staff_profile)

        elif user.role in ["Admin", "Finance", "Support"] or user.is_superuser:
            # Admin, Finance, Support, and superusers see all applications
            qs = qs

        else:
            return qs.none()

        # Sort: submission_date first (if available), else created_at

        return qs.order_by(Coalesce("submission_date", "created_at").desc())
# class FinalizeVisaApplicationAPIView(APIView):
#     def patch(self, request, pk):
#         app = get_object_or_404(VisaApplication, pk=pk)
#         app.status = "SUBMITTED"
#         app.submission_date = timezone.now()  # ✅ set current date/time
#         app.save(update_fields=["status", "submission_date"])
#         serializer = VisaApplicationSerializer(app)
#         return Response(serializer.data, status=status.HTTP_200_OK)



# class FinalizeVisaApplicationAPIView(APIView):
#     def patch(self, request, pk):
#         app = get_object_or_404(VisaApplication, pk=pk)
#         app.status = "SUBMITTED"
#         app.save(update_fields=["status"])
#         serializer = VisaApplicationSerializer(app)
#         return Response(serializer.data, status=status.HTTP_200_OK)

# class DocumentUploadAPIView(APIView):
#     """
#     Handle file upload for a specific document requirement in a visa application.
#     """
#     permission_classes = [IsAuthenticated]

#     def post(self, request, pk, *args, **kwargs):
#         try:
#             client_profile = request.user.client_profile  # OneToOneField from User → ClientProfile
#         except ClientProfile.DoesNotExist:
#             return Response({"detail": "Client profile not found."}, status=status.HTTP_400_BAD_REQUEST)

#         doc = get_object_or_404(Document, pk=pk, application__client=client_profile)
#         file = request.FILES.get("file")

#         if not file:
#             return Response({"detail": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

#         # Save file and update status
#         doc.file = file
#         doc.status = "UPLOADED"
#         doc.save()

#         return Response({
#             "id": doc.id,
#             "requirement": doc.requirement.name,
#             "status": doc.status
#         }, status=status.HTTP_200_OK)



# class DocumentUploadAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request, pk):
#         doc = get_object_or_404(Document, pk=pk, application__client=request.user.client_profile)
#         file = request.FILES.get("file")
#         if not file:
#             return Response({"detail": "No file provided"}, status=400)

#         doc.file = file
#         doc.status = "UPLOADED"
#         doc.save()
#         return Response({"id": doc.id, "status": doc.status})



