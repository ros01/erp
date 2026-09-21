from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import RetrieveAPIView
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Q, Value, Count, Case, When, IntegerField
from Documents.models import DocumentRequirement, Document
from Accounts.models import *
from CaseManagement.models import TaskAssignment, ReassignmentLog
from .models import VisaApplication, PreviousRefusalLetter, RefusalLetter
from .services import *
# from Documents.serializers import DocumentRequirementSerializer
from .serializers import (
    DocumentRequirementSerializer,
    VisaApplicationSerializer,
    VisaApplicationsSerializer,
    VisaApplicationDetailSerializer,
    DocumentSerializer,
    VisaApplicationUrlUpdateSerializer,
    ReapplyApplicationSerializer,
    PreviousRefusalLetterSerializer,
    RefusalLetterSerializer,
    # FormProcessingSerializer,
)
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from Accounts.choices import *
from Documents.serializers import CountrySerializer, VisaTypeSerializer
import uuid
import calendar
from datetime import datetime, timedelta
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
from django.http import FileResponse, HttpResponseNotFound, JsonResponse, Http404
from django.views import View
from pathlib import Path
from rest_framework.decorators import api_view
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
#from pdfrw import PdfReader, PdfWriter, PdfDict
#from PyPDF2.generic import NameObject, TextStringObject
from django.contrib.auth import get_user_model
from django.conf import settings
import io, os
from io import BytesIO
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import pypdf
from pypdf.generic import NameObject 
from django.contrib.auth.mixins import LoginRequiredMixin

User = get_user_model()


from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count, Q
from collections import defaultdict

class OfficerDocumentAnalyticsAPIViewOld(APIView):

    def get(self, request):

        officer = request.user.staff_profile

        documents = (
            Document.objects
            .filter(application__created_by_officer=officer)
            .select_related("requirement", "application")
        )

        total_documents = documents.count()

        # -----------------------------
        # Status percentages
        # -----------------------------
        reviewed_count = documents.filter(status="REVIEWED").count()
        missing_count = documents.filter(status="MISSING").count()

        reviewed_percent = round(
            (reviewed_count / total_documents) * 100, 2
        ) if total_documents else 0

        missing_percent = round(
            (missing_count / total_documents) * 100, 2
        ) if total_documents else 0

        # -----------------------------
        # Stage Breakdown
        # -----------------------------
        stage_counter = defaultdict(int)

        for doc in documents:
            stage = None

            if doc.requirement:
                stage = doc.requirement.stage

            # 🔥 Handle non-student visas / empty stage
            if not stage:
                stage = "GENERAL"

            # 🔥 Normalize numeric or inconsistent values
            stage = str(stage).upper().strip()

            stage_counter[stage] += 1

        stage_labels = list(stage_counter.keys())
        stage_counts = list(stage_counter.values())

        return Response({
            "total_documents": total_documents,
            "reviewed_percent": reviewed_percent,
            "missing_percent": missing_percent,
            "stage_labels": stage_labels,
            "stage_counts": stage_counts
        })


class OfficerDocumentAnalyticsAPIView(LoginRequiredMixin, View):

    def get(self, request):

        officer = request.user.staff_profile

        documents = Document.objects.select_related(
            "application",
            "requirement"
        ).filter(
            Q(application__created_by_officer=officer) |
            Q(application__assigned_officer=officer)
        )

        total_docs = documents.count()

        reviewed_docs = documents.filter(status="REVIEWED").count()
        missing_docs = documents.filter(status="MISSING").count()

        reviewed_percent = (
            round((reviewed_docs / total_docs) * 100, 1)
            if total_docs > 0 else 0
        )

        missing_percent = (
            round((missing_docs / total_docs) * 100, 1)
            if total_docs > 0 else 0
        )

        stage_breakdown = (
            documents
            .values("requirement__stage")
            .annotate(count=Count("id"))
        )

        return JsonResponse({
            "total_documents": total_docs,
            "reviewed_percent": reviewed_percent,
            "missing_percent": missing_percent,
            "stage_labels": [
                item["requirement__stage"] or "OTHER"
                for item in stage_breakdown
            ],
            "stage_counts": [
                item["count"]
                for item in stage_breakdown
            ]
        })


class OfficerDocumentsDataAPIView(LoginRequiredMixin, View):

    def get(self, request):

        officer = request.user.staff_profile

        draw = int(request.GET.get("draw", 1))
        start = int(request.GET.get("start", 0))
        length = int(request.GET.get("length", 10))
        search_value = request.GET.get("search[value]", "")

        queryset = Document.objects.select_related(
            "application",
            "application__client__user",
            "requirement"
        ).filter(
            Q(application__created_by_officer=officer) |
            Q(application__assigned_officer=officer)
        )

        total_records = queryset.count()

        if search_value:
            queryset = queryset.filter(
                Q(application__reference_no__icontains=search_value) |
                Q(application__client__user__first_name__icontains=search_value) |
                Q(application__client__user__last_name__icontains=search_value) |
                Q(requirement__name__icontains=search_value)
            )

        filtered_records = queryset.count()

        queryset = queryset.order_by("-uploaded_at")[start:start + length]

        data = []
        for doc in queryset:
            data.append({
                "reference": doc.application.reference_no,
                "client": doc.application.client.user.get_full_name,
                "requirement": doc.requirement.name if doc.requirement else "-",
                "stage": doc.requirement.stage if doc.requirement else "-",
                "status": doc.status,
                "uploaded": doc.uploaded_at.strftime("%d %b %Y %H:%M")
            })

        return JsonResponse({
            "draw": draw,
            "recordsTotal": total_records,
            "recordsFiltered": filtered_records,
            "data": data
        })






class StartAdmissionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        client = request.user.client_profile
        country = request.data.get("country")

        pipeline = StudentApplicationPipeline.objects.create(
            client=client,
            country=country,
            current_stage="ADMISSION"
        )

        admission = AdmissionApplication.objects.create(pipeline=pipeline)
        pipeline.admission_application = admission
        pipeline.save()

        # Create document placeholders
        requirements = DocumentRequirement.objects.filter(
            country=country, visa_type="STUDENT", stage="ADMISSION"
        )

        Document.objects.bulk_create([
            Document(application=None, requirement=req, status="MISSING")
            for req in requirements
        ])

        return Response(StudentPipelineSerializer(pipeline).data)


class SubmitAdmissionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        pipeline = StudentApplicationPipeline.objects.get(
            client=request.user.client_profile
        )

        if pipeline.current_stage != "ADMISSION":
            return Response({"detail": "Invalid stage"}, status=403)

        admission = pipeline.admission_application
        admission.status = "SUBMITTED"
        admission.save()

        return Response({"status": "submitted"})



class UploadOfferLetterAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        admission = AdmissionApplication.objects.get(pk=pk)
        admission.offer_letter = request.FILES["offer_letter"]
        admission.status = "OFFER_RECEIVED"
        admission.save()

        pipeline = admission.pipeline
        pipeline.current_stage = "CAS"
        pipeline.save()

        return Response({"status": "offer uploaded"})

class StartCASAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        pipeline = StudentApplicationPipeline.objects.get(
            client=request.user.client_profile
        )

        if pipeline.current_stage != "CAS":
            return Response({"detail": "Invalid stage"}, status=403)

        cas = CASApplication.objects.create(pipeline=pipeline)
        pipeline.cas_application = cas
        pipeline.save()

        return Response({"status": "cas started"})


class IssueCASAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        cas = CASApplication.objects.get(pk=pk)
        cas.cas_letter = request.FILES["cas_letter"]
        cas.status = "CAS_ISSUED"
        cas.save()

        pipeline = cas.pipeline

        visa = VisaApplication.objects.create(
            client=pipeline.client,
            country=pipeline.country,
            visa_type="STUDENT",
            reference_no=generate_reference_no(),
            status="QUEUED"
        )

        pipeline.visa_application = visa
        pipeline.current_stage = "VISA"
        pipeline.save()

        return Response({"visa_application_id": visa.id})




class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = {
            "id": user.id,
            "email": user.email,
            "full_name": user.get_full_name,
            "role": user.role,
        }
        return Response(data)
        

class AutoFilledPDFView(View):
    def get(self, request):
        country = request.GET.get("country")
        visa_type = request.GET.get("visa_type")

        # 1️⃣ Get matching document requirement that has a form file
        req = (
            DocumentRequirement.objects
            .filter(country=country, visa_type=visa_type)
            .exclude(form_file__exact="")
            .exclude(form_file__isnull=True)
            .order_by("-id")
            .first()
        )
        if not req or not req.form_file:
            return HttpResponseNotFound("No PDF form found for this visa type.")

        form_path = req.form_file.path

        try:
            reader = PdfReader(form_path)
        except Exception as e:
            return JsonResponse({"error": f"Failed to open PDF: {e}"}, status=500)

        writer = PdfWriter()

        # Copy all pages from reader
        for page in reader.pages:
            writer.add_page(page)

        # ✅ Copy the /AcroForm dictionary so that form fields are preserved
        if "/AcroForm" in reader.trailer["/Root"]:
            writer._root_object.update({
                NameObject("/AcroForm"): reader.trailer["/Root"]["/AcroForm"]
            })

        # 2️⃣ Prepare user info
        user = request.user if request.user.is_authenticated else None
        if user:
            full_name = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
            email = getattr(user, "email", "")
            passport_no = (
                getattr(user.client_profile, "passport_number", "")
                if hasattr(user, "client_profile")
                else ""
            )
        else:
            full_name = email = passport_no = ""

        # 3️⃣ Try to fill the form if fields exist
        try:
            fields = reader.get_fields() or {}
            if fields:
                field_data = {}
                for field_name in fields.keys():
                    lname = field_name.lower()
                    if "full_name" in lname:
                        field_data[field_name] = full_name
                    elif "email" in lname:
                        field_data[field_name] = email
                    elif "passport" in lname:
                        field_data[field_name] = passport_no

                if field_data:
                    first_page = writer.pages[0]
                    writer.update_page_form_field_values(first_page, field_data)
            else:
                raise ValueError("No form fields found")
        except Exception as e:
            # 🟡 Hybrid fallback: generate a simple summary PDF with reportlab
            output = BytesIO()
            c = canvas.Canvas(output, pagesize=A4)
            c.setFont("Helvetica-Bold", 14)
            c.drawString(100, 780, f"Visa Application Form - {country} / {visa_type}")
            c.setFont("Helvetica", 12)
            c.drawString(100, 740, f"Full Name: {full_name}")
            c.drawString(100, 720, f"Email: {email}")
            c.drawString(100, 700, f"Passport Number: {passport_no}")
            c.setFont("Helvetica-Oblique", 10)
            c.drawString(100, 660, "(Auto-generated because the original PDF form was not fillable.)")
            c.showPage()
            c.save()
            output.seek(0)

            filename = f"{country}_{visa_type}_summary.pdf".replace(" ", "_")
            return FileResponse(output, as_attachment=True, filename=filename)

        # 4️⃣ Return filled form
        output = BytesIO()
        writer.write(output)
        output.seek(0)
        filename = f"{country}_{visa_type}_filled.pdf".replace(" ", "_")
        return FileResponse(output, as_attachment=True, filename=filename)



@login_required
def pdf_form_fill(request):
    user = request.user
    client_profile = getattr(user, "clientprofile", None)

    template_path = os.path.join(
    settings.BASE_DIR, "media", "pdf_forms", "UK_Application_Fillable_tNuNy6m.pdf"
    )

    with open(template_path, "rb") as f:
        reader = PdfReader(f)
        writer = PdfWriter()

        page = reader.pages[0]

        # Try to fill PDF fields
        try:
            writer.update_page_form_field_values(page, {
                "Full Name": user.get_full_name,
                "Passport Number": getattr(client, "passport_number", "N/A"),
                "Email": user.email,
            })
        except Exception:
            pass  # ignore if fields don't exist

        writer.add_page(page)

        output_stream = io.BytesIO()
        writer.write(output_stream)
        output_stream.seek(0)

    filename = f"{user.last_name}_VisaForm.pdf"
    return FileResponse(output_stream, as_attachment=True, filename=filename)




@api_view(["GET"])
def get_requirements(request):
    country = request.GET.get("country")
    visa_type = request.GET.get("visa_type")

    qs = DocumentRequirement.objects.filter(country=country, visa_type=visa_type, is_active=True)
    serializer = DocumentRequirementSerializer(qs, many=True, context={"request": request})
    return Response(serializer.data)



@api_view(["GET"])
def pdf_form(request):
    country = request.GET.get("country")
    visa_type = request.GET.get("visa_type")
    if not (country and visa_type):
        return Response({"error": "Missing parameters"}, status=400)

    pdf_path = Path(f"media/pdf_forms/{country}_{visa_type}.pdf")
    if not pdf_path.exists():
        raise Http404("Form not found")

    return FileResponse(open(pdf_path, "rb"), as_attachment=True, filename=pdf_path.name)




@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_refusals(request, pk):
    app = get_object_or_404(VisaApplication, id=pk)

    files = request.FILES.getlist("refusal_files")
    uploaded = []

    for f in files:
        letter = PreviousRefusalLetter.objects.create(
            application=app,
            file=f,
        )
        uploaded.append({
            "id": str(letter.id),
            "file_url": letter.file.url,
            "uploaded_at": letter.uploaded_at.isoformat()
        })

    return Response({
        "success": True,
        "files_uploaded": len(uploaded),
        "refusal_letters": uploaded
    })

class ApplicationReapplyView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReapplyApplicationSerializer
    lookup_field = "pk"

    def get_queryset(self):
        return (
            VisaApplication.objects
            .select_related("client", "client__user")
            .prefetch_related(
                "documents",
                "refusal_letter"   # 🔥 REQUIRED
            )
        )

    def get(self, request, pk):
        application = self.get_queryset().get(pk=pk)

        if application.status not in ["APPROVED", "REJECTED"]:
            return Response(
                {"error": "Reapplication only allowed for APPROVED or REJECTED applications."},
                status=400
            )

        serializer = self.get_serializer(application)
        return Response(serializer.data)

    def post(self, request, pk):
        application = get_object_or_404(VisaApplication, pk=pk)
        staff_profile = getattr(request.user, "staff_profile", None)

        # ===============================
        # ✅ Update client profile
        # ===============================
        client = application.client
        client.passport_number = request.data.get(
            "passport_number", client.passport_number
        )
        client.save()

        # ✅ Update linked user
        user = client.user
        user.first_name = request.data.get("first_name", user.first_name)
        user.last_name = request.data.get("last_name", user.last_name)
        user.email = request.data.get("email", user.email)
        user.phone = request.data.get("phone", user.phone)
        user.save()

        # ===============================
        # ✅ Create new application
        # ===============================
        new_app = VisaApplication.objects.create(
            client=client,
            country=request.data.get("country", application.country),
            visa_type=request.data.get("visa_type", application.visa_type),
            status="INITIATED",
            reference_no=generate_reference_no(),
            created_by_officer=staff_profile,
        )

        # ===============================
        # 🔁 COPY EXISTING REFUSAL LETTERS
        # ===============================
        copied_letters = []
        for old_letter in application.refusal_letter.all():
            copied_letters.append(
                RefusalLetter.objects.create(
                    application=new_app,
                    file=old_letter.file   # ✅ reuse same file (no disk copy)
                )
            )

        # ===============================
        # ➕ SAVE NEWLY UPLOADED LETTERS
        # ===============================
        uploaded_letters = []
        for f in request.FILES.getlist("refusal_letters"):
            uploaded_letters.append(
                RefusalLetter.objects.create(
                    application=new_app,
                    file=f
                )
            )

        # ===============================
        # ✅ Copy documents
        # ===============================
        for doc_id in request.data.getlist("doc_id[]"):
            old_doc = get_object_or_404(Document, pk=doc_id)
            new_file = request.FILES.get(f"document_{doc_id}")

            Document.objects.create(
                application=new_app,
                requirement=old_doc.requirement,
                file=new_file or old_doc.file,
                status="UPLOADED"
            )

        # ===============================
        # ✅ Return ALL refusal letters
        # ===============================
        all_letters = list(copied_letters) + list(uploaded_letters)

        return Response({
            "success": True,
            "new_application_id": new_app.id,
            "reference_no": new_app.reference_no,
            "refusal_letters": RefusalLetterSerializer(
                all_letters, many=True
            ).data
        })


class ApplicationReapplyViewWL(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReapplyApplicationSerializer
    lookup_field = "pk"

    def get_queryset(self):
        return (
            VisaApplication.objects
            .select_related("client", "client__user")
            .prefetch_related(
                "documents",
                "refusal_letter"   # 🔥 REQUIRED
            )
        )

    def get(self, request, pk):
        application = self.get_queryset().get(pk=pk)

        if application.status not in ["APPROVED", "REJECTED"]:
            return Response(
                {"error": "Reapplication only allowed for APPROVED or REJECTED applications."},
                status=400
            )

        serializer = self.get_serializer(application)
        return Response(serializer.data)

    def post(self, request, pk):
        application = get_object_or_404(VisaApplication, pk=pk)
        staff_profile = getattr(request.user, "staff_profile", None)

        # ✅ Update client profile
        client = application.client
        client.passport_number = request.data.get(
            "passport_number", client.passport_number
        )
        client.save()

        # ✅ Update linked user
        user = client.user
        user.first_name = request.data.get("first_name", user.first_name)
        user.last_name = request.data.get("last_name", user.last_name)
        user.email = request.data.get("email", user.email)
        user.phone = request.data.get("phone", user.phone)
        user.save()

        # ✅ Create new application
        new_app = VisaApplication.objects.create(
            client=client,
            country=request.data.get("country", application.country),
            visa_type=request.data.get("visa_type", application.visa_type),
            status="INITIATED",
            reference_no=generate_reference_no(),
            created_by_officer=staff_profile,
        )

        # ✅ SAVE REFUSAL LETTERS (FIXED MODEL + FIELD)
        uploaded_letters = []
        for f in request.FILES.getlist("refusal_letters"):
            letter = RefusalLetter.objects.create(
                application=new_app,
                file=f
            )
            uploaded_letters.append(letter)

        # ✅ Copy documents
        for doc_id in request.data.getlist("doc_id[]"):
            old_doc = get_object_or_404(Document, pk=doc_id)
            new_file = request.FILES.get(f"document_{doc_id}")

            Document.objects.create(
                application=new_app,
                requirement=old_doc.requirement,
                file=new_file or old_doc.file,
                status="UPLOADED"
            )

        return Response({
            "success": True,
            "new_application_id": new_app.id,
            "reference_no": new_app.reference_no,
            "refusal_letters": RefusalLetterSerializer(
                uploaded_letters, many=True
            ).data
        })




class ApplicationReapplyViewW(generics.RetrieveAPIView):
    queryset = VisaApplication.objects.all()
    serializer_class = ReapplyApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        application = get_object_or_404(VisaApplication, pk=pk)

        if application.status not in ["APPROVED", "REJECTED"]:
            return Response(
                {"error": "Reapplication only allowed for APPROVED or REJECTED applications."},
                status=400
            )

        serializer = self.get_serializer(application)
        return Response(serializer.data)

    def post(self, request, pk):
        application = get_object_or_404(VisaApplication, pk=pk)
        staff_profile = getattr(request.user, "staff_profile", None)

        # ✅ Update client profile fields
        client = application.client
        client.passport_number = request.data.get("passport_number", client.passport_number)
        client.save()

        # ✅ Update user fields linked to client
        user = client.user
        user.first_name = request.data.get("first_name", user.first_name)
        user.last_name = request.data.get("last_name", user.last_name)
        user.email = request.data.get("email", user.email)
        user.phone = request.data.get("phone", user.phone)
        user.save()

        # ✅ Create new VisaApplication
        new_app = VisaApplication.objects.create(
            client=client,
            country=request.data.get("country", application.country),
            visa_type=request.data.get("visa_type", application.visa_type),
            status="INITIATED",
            reference_no=generate_reference_no(),
            created_by_officer=staff_profile,
        )

        # ✅ Handle refusal letters upload
        refusal_files = request.FILES.getlist("refusal_letters")
        uploaded_letters = []
        for f in refusal_files:
            letter = PreviousRefusalLetter.objects.create(application=new_app, file=f)
            uploaded_letters.append(letter)

        # ✅ Handle documents
        doc_ids = request.data.getlist("doc_id[]")
        for doc_id in doc_ids:
            file_field = request.FILES.get(f"document_{doc_id}")
            old_doc = get_object_or_404(Document, pk=doc_id)

            if file_field:
                Document.objects.create(
                    application=new_app,
                    requirement=old_doc.requirement,
                    file=file_field,
                    status="UPLOADED"
                )
            else:
                Document.objects.create(
                    application=new_app,
                    requirement=old_doc.requirement,
                    file=old_doc.file,
                    status="UPLOADED"
                )

        return Response({
            "success": True,
            "new_application_id": new_app.id,
            "reference_no": new_app.reference_no,
            "refusal_letters": PreviousRefusalLetterSerializer(uploaded_letters, many=True).data
        })

        

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


class AddVisaApplicationDecisionAPIView(APIView):
    """
    PATCH → approve / reject application
    POST  → upload one or more refusal letters (REJECTED only)
    """

    def patch(self, request, pk):
        application = get_object_or_404(VisaApplication, pk=pk)

        decision = request.data.get("status")
        if decision not in ["APPROVED", "REJECTED"]:
            return Response(
                {"error": "Invalid decision"},
                status=status.HTTP_400_BAD_REQUEST
            )

        from Applications.notifications import notify_visa_decision

        application.status = decision
        application.decision_date = timezone.now()
        application.save(update_fields=["status", "decision_date", "updated_at"])
        notify_visa_decision(application)  # ✅ SEND EMAIL

        # 🔽 Reduce officer workload
        staff = application.assigned_officer or application.created_by_officer
        if staff and staff.workload > 0:
            staff.workload -= 1
            staff.save(update_fields=["workload"])

        return Response(
            VisaApplicationSerializer(application).data,
            status=status.HTTP_200_OK
        )

    def post(self, request, pk):
        try:
            application = VisaApplication.objects.get(pk=pk)
        except VisaApplication.DoesNotExist:
            return Response({"error": "Application not found"}, status=404)

        files = request.FILES.getlist("refusal_letters")
        if not files:
            return Response({"error": "No files uploaded"}, status=400)

        for file in files:
            RefusalLetter.objects.create(
                application=application,
                file=file
            )

        # 🔥 IMPORTANT: re-fetch with related data
        application = VisaApplication.objects.prefetch_related(
            "refusal_letter"
        ).get(pk=pk)

        return Response(
            VisaApplicationSerializer(application).data,
            status=200
        )


class VisaApplicationDetailAPIView(RetrieveAPIView):
    serializer_class = VisaApplicationDetailSerializer
    lookup_field = "id"

    def get_queryset(self):
        return (
            VisaApplication.objects
            .select_related(
                "client",
                "created_by_officer",
                "assigned_officer"
            )
            .prefetch_related(
                "refusal_letter",     # 🔥 THIS IS THE KEY
                "documents",
            )
        )

    def get_object(self):
        application = super().get_object()
        # 🔒 This is the "View Details" endpoint on the Case Officer's
        # applications list - a Case Officer can't even view an
        # auto-assigned application until Admin validates or reassigns it.
        enforce_officer_not_locked(
            application,
            self.request.user,
            message="Contact Admin to validate this application before you can proceed.",
        )
        return application


class CaseOfficerDashboardApplicationDetailAPIView(VisaApplicationDetailAPIView):
    """
    Same application-detail data as VisaApplicationDetailAPIView, but
    WITHOUT the Admin-validation gate. Backs the "Latest Applications"
    widget on the Case Officer's own dashboard
    (case_officer/case_officer_dashboard1.html) - that View Details modal
    is read-only (no stage-transition action is reachable from it), so
    there is nothing to gate there. CaseManagement/applications/ (the
    View/Review Applications table) keeps the gate via the parent view;
    this is a deliberate, narrow bypass for the dashboard widget only.
    """

    def get_object(self):
        # Intentionally skip VisaApplicationDetailAPIView.get_object()'s
        # gate - go straight to RetrieveAPIView's lookup.
        return RetrieveAPIView.get_object(self)


    # def post(self, request, pk):
    #     application = get_object_or_404(VisaApplication, pk=pk)

    #     # 🚫 Safety: only allow uploads for REJECTED apps
    #     if application.status != "REJECTED":
    #         return Response(
    #             {"error": "Rejection letters can only be uploaded for rejected applications"},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )

    #     files = request.FILES.getlist("refusal_letters")

    #     if not files:
    #         return Response(
    #             {"error": "No rejection files uploaded"},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )

    #     uploaded = []
    #     for file in files:
    #         letter = RefusalLetter.objects.create(
    #             application=application,
    #             file=file
    #         )
    #         uploaded.append(letter.file.url)

    #     return Response(
    #         {
    #             "message": "Rejection letter(s) uploaded successfully",
    #             "refusal_letters": uploaded
    #         },
    #         status=status.HTTP_200_OK
    #     )



class AddVisaApplicationDecisionAPIView00(APIView):
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


# api_views.py

class UploadRefusalLetterAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        application = get_object_or_404(VisaApplication, pk=pk)

        files = request.FILES.getlist("refusal_letters")
        if not files:
            return Response({"detail": "No files uploaded"}, status=400)

        for f in files:
            RefusalLetter.objects.create(
                application=application,
                file=f
            )

        return Response({
            "success": True,
            "files_uploaded": len(files)
        })



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


class AssignedApplicationsListAPIView(generics.ListAPIView):
    """
    Applications auto-assigned to a Case Officer and STILL awaiting Admin
    action (status == "ASSIGNED", admin_validated == False). Backs the
    Admin dashboard's "Assigned Applications" queue - Admin either
    validates the auto-assignment or reassigns it to a different officer
    before the officer can act on it (see
    Applications.services.enforce_officer_not_locked). The moment either
    action happens, admin_validated flips to True and the application
    drops off this queue - it then lives on in the "All Applications"
    list (see AllApplicationsListAPIView), where it can still be
    reassigned at any later point in its lifecycle.
    """
    serializer_class = VisaApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            VisaApplication.objects
            .filter(status="ASSIGNED", admin_validated=False)
            .select_related("client", "client__user", "assigned_officer__user")
            .order_by("-created_at")
        )


class AllApplicationsListAPIView(generics.ListAPIView):
    """
    Every application, regardless of status. Backs the Admin dashboard's
    "All Applications" list, from which Admin can reassign an
    application to a different Case Officer at any point in its
    lifecycle (see ReassignApplicationOfficerAPIView) - unlike
    AssignedApplicationsListAPIView, which only surfaces applications
    still pending Admin's initial validate/reassign action.
    """
    serializer_class = VisaApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            VisaApplication.objects
            .select_related("client", "client__user", "assigned_officer__user")
            .order_by("-created_at")
        )


class AvailableCaseOfficersListAPIView(APIView):
    """
    Lists Case Officers, for the Admin dashboard's "Reassign" picker.

    Pass ?application_id=<uuid> to exclude that application's current
    assigned_officer and created_by_officer (initiating officer) from
    the list - reassigning "to" either of them is a no-op the picker
    shouldn't offer in the first place.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        officers = (
            StaffProfile.objects
            .filter(user__role="Case Officer")
            .select_related("user")
            .order_by("workload", "id")
        )

        application_id = request.query_params.get("application_id")
        if application_id:
            application = VisaApplication.objects.filter(pk=application_id).first()
            if application:
                exclude_ids = [
                    pk for pk in (
                        application.assigned_officer_id,
                        application.created_by_officer_id,
                    ) if pk
                ]
                if exclude_ids:
                    officers = officers.exclude(pk__in=exclude_ids)

        data = [
            {
                "id": officer.id,
                "name": officer.user.get_full_name or officer.user.email,
                "email": officer.user.email,
                "workload": officer.workload,
                "is_available": officer.is_available,
            }
            for officer in officers
        ]
        return Response(data, status=status.HTTP_200_OK)


class ValidateApplicationAssignmentAPIView(APIView):
    """
    Admin validates the current auto-assignment as-is: the assigned Case
    Officer is confirmed and can now review documents / continue
    processing the application (see Applications.services.enforce_officer_not_locked).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        if not (user.role == "Admin" or user.is_superuser):
            return Response({"error": "Only Admin can validate an assignment."}, status=status.HTTP_403_FORBIDDEN)

        application = get_object_or_404(VisaApplication, pk=pk)

        if application.status != "ASSIGNED":
            return Response(
                {"error": "Only applications with status ASSIGNED can be validated."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        application.admin_validated = True
        application.validated_by = getattr(user, "staff_profile", None)
        application.validated_at = timezone.now()
        application.save(update_fields=["admin_validated", "validated_by", "validated_at"])

        AuditLog.objects.create(
            user=user,
            action="assign",
            module="Applications",
            description=(
                f"Validated auto-assignment of {application.reference_no} "
                f"to {application.assigned_officer}"
            ),
        )

        return Response(VisaApplicationSerializer(application).data, status=status.HTTP_200_OK)


class ReassignApplicationOfficerAPIView(APIView):
    """
    Admin reassigns an application to a different Case Officer, at ANY
    point in its lifecycle - not just while status == "ASSIGNED". Backs
    the "Reassign" action on both the Admin dashboard's "Assigned
    Applications" queue (pre-validation hand-off) and its "All
    Applications" list (ownership changes later in the lifecycle).
    This also validates the assignment (no separate validate step needed
    afterwards) - the newly-assigned officer can immediately review
    documents / continue processing. For an application that isn't
    status == "ASSIGNED", admin_validated is already irrelevant to
    gating (Applications.services.is_pending_admin_validation only
    locks "ASSIGNED" applications), so setting it True here is a no-op
    for those cases.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        if not (user.role == "Admin" or user.is_superuser):
            return Response({"error": "Only Admin can reassign an application."}, status=status.HTTP_403_FORBIDDEN)

        application = get_object_or_404(VisaApplication, pk=pk)

        officer_id = request.data.get("officer_id")
        if not officer_id:
            return Response({"error": "officer_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_officer = StaffProfile.objects.get(pk=officer_id, user__role="Case Officer")
        except StaffProfile.DoesNotExist:
            return Response({"error": "Invalid officer_id"}, status=status.HTTP_400_BAD_REQUEST)

        old_officer = application.assigned_officer

        if old_officer and old_officer.pk == new_officer.pk:
            return Response({"error": "Application is already assigned to this officer."}, status=status.HTTP_400_BAD_REQUEST)

        if application.created_by_officer_id and application.created_by_officer_id == new_officer.pk:
            return Response(
                {"error": "Cannot reassign to the officer who initiated this application."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Move workload from old officer to new officer
        if old_officer and old_officer.workload > 0:
            old_officer.workload -= 1
            old_officer.save(update_fields=["workload"])

        new_officer.workload += 1
        new_officer.save(update_fields=["workload"])

        application.assigned_officer = new_officer
        application.admin_validated = True
        application.validated_by = getattr(user, "staff_profile", None)
        application.validated_at = timezone.now()
        application.save(update_fields=[
            "assigned_officer", "admin_validated", "validated_by", "validated_at",
        ])

        # TaskAssignment is OneToOne with the application - update in place
        # rather than creating a second row.
        TaskAssignment.objects.update_or_create(
            application=application,
            defaults={
                "assigned_to": new_officer,
                "status": "Assigned",
                "description": f"Reassigned by Admin for application {application.reference_no}",
                "completed": False,
            },
        )

        ReassignmentLog.objects.create(
            application=application,
            from_officer=old_officer,
            to_officer=new_officer,
            reason=request.data.get("reason", ""),
            reassigned_by=getattr(user, "staff_profile", None),
            strategy="manual",
        )

        AuditLog.objects.create(
            user=user,
            action="assign",
            module="Applications",
            description=(
                f"Reassigned {application.reference_no} from {old_officer} to {new_officer}"
            ),
        )

        return Response(VisaApplicationSerializer(application).data, status=status.HTTP_200_OK)


class DocumentReviewAPIView(generics.UpdateAPIView):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    def perform_update(self, serializer):
        enforce_officer_not_locked(serializer.instance.application, self.request.user)

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

    - Clients can upload only documents belonging to their own application
    - Case Officers / Admins can upload for any application
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        user = request.user
        file = request.FILES.get("file")

        if not file:
            return Response(
                {"detail": "No file uploaded"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 🔐 Resolve document based on role
        if user.role in ["Case Officer", "Admin"]:
            doc = get_object_or_404(Document, pk=pk)

        elif user.role == "Client":
            try:
                client_profile = user.client_profile
            except ClientProfile.DoesNotExist:
                return Response(
                    {"detail": "Client profile not found."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            doc = get_object_or_404(
                Document,
                pk=pk,
                application__client=client_profile
            )
        else:
            return Response(
                {"detail": "You do not have permission to upload files."},
                status=status.HTTP_403_FORBIDDEN
            )

        # 💾 Save uploaded file
        doc.file = file
        doc.status = "UPLOADED"
        doc.save(update_fields=["file", "status"])

        # 🚀 Attempt automatic stage advancement
        advance_result = try_advance_stage(doc.application)
        """
        advance_result MUST return:
        {
            "stage_advanced": bool,
            "final_stage_completed": bool,
            "stage": "ADMISSION" | "CAS" | "VISA",
            "progress": int (0–100)
        }
        """

        # ✅ Single, consistent response for frontend
        return Response(
            {
                "id": str(doc.id),
                "requirement": doc.requirement.name,
                "status": doc.status,
                "file_url": doc.file.url if doc.file else None,

                # 🔑 stage logic
                "stage_advanced": advance_result["stage_advanced"],
                "final_stage_completed": advance_result["final_stage_completed"],
                "new_stage": advance_result["stage"],
                "progress": advance_result["progress"],
            },
            status=status.HTTP_200_OK
        )






class DocumentUploadAPIViewWW(APIView):
    """
    Upload a file for a specific Document.
    Clients: can upload only their own application documents.
    Case Officers/Admin: can upload for any client.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        user = request.user
        file = request.FILES.get("file")

        if not file:
            return Response(
                {"detail": "No file uploaded"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Case Officer or Admin → full access
        if user.role in ["Case Officer", "Admin"]:
            doc = get_object_or_404(Document, pk=pk)

        # Client → only their own documents
        elif user.role == "Client":
            try:
                client_profile = user.client_profile
            except ClientProfile.DoesNotExist:
                return Response(
                    {"detail": "Client profile not found."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            doc = get_object_or_404(
                Document,
                pk=pk,
                application__client=client_profile
            )
        else:
            return Response(
                {"detail": "You do not have permission to upload files."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Save uploaded file
        doc.file = file
        doc.status = "UPLOADED"
        doc.save(update_fields=["file", "status"])

        # 🔑 Attempt stage advancement

        stage_advanced = try_advance_stage(doc.application)

        return Response({
            "id": str(doc.id),
            "requirement": doc.requirement.name,
            "status": doc.status,
            "file_url": doc.file.url if doc.file else None,
            "stage_advanced": stage_advanced,
            "new_stage": doc.application.stage,
            "progress": doc.application.progress,
        }, status=status.HTTP_200_OK)



        advance_result = try_advance_stage(doc.application)

        return Response({
            "id": str(doc.id),
            "status": doc.status,
            "file_url": doc.file.url if doc.file else None,
            **advance_result,
        }, status=status.HTTP_200_OK)




        # stage_advanced = try_advance_stage(doc.application)

        # return Response(
        #     {
        #         "id": str(doc.id),
        #         "requirement": doc.requirement.name,
        #         "status": doc.status,
        #         "file_url": doc.file.url if doc.file else None,

        #         # ✅ frontend control flags
        #         "stage_advanced": stage_advanced,
        #         "new_stage": doc.application.stage if stage_advanced else None,
        #         "progress": doc.application.progress,
        #     },
        #     status=status.HTTP_200_OK
        # )

class DocumentUploadAPIViewLL(APIView):
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

        try_advance_stage(doc.application)


        return Response({
            "id": str(doc.id),
            "requirement": doc.requirement.name,
            "status": doc.status,
            "file_url": doc.file.url if doc.file else None,
            "new_stage": doc.application.stage,
            "progress": doc.application.progress,
        }, status=status.HTTP_200_OK)


        # return Response({
        #     "status": doc.status,
        #     "file_url": doc.file.url,
        #     "new_stage": doc.application.stage,
        #     "progress": doc.application.progress,
        # })


class VisaApplicationListStudentAPIView(generics.ListAPIView):
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
        #qs = qs.filter(Q(status="ASSIGNED") | Q(status="INITIATED"))
        qs = qs.filter(Q(status__in=["ASSIGNED", "INITIATED"]), visa_type="STUDENT")

        return qs.order_by("-created_at")



class VisaApplicationListStudentAdminAPIView(generics.ListAPIView):
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
        #qs = qs.filter(Q(status="ASSIGNED") | Q(status="INITIATED"))
        qs = qs.filter(visa_type="STUDENT")

        return qs.order_by("-created_at")


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
    """
    Applications with a recorded decision (status APPROVED/REJECTED)
    that Admin has NOT yet notified the client about. Backs the Admin
    dashboard's "Finalized Applications" list - once Admin clicks
    "Notify Client" (see NotifyClientAPIView), the application drops off
    this list and moves to "Notified Applications"
    (see NotifiedApplicationsListAPIView).
    """
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
                    ).filter(client_notified=False)

        # 🔹 sort by submission_date first, else created_at
        return qs.order_by(Coalesce("submission_date", "created_at").desc())


class NotifiedApplicationsListAPIView(generics.ListAPIView):
    """
    Applications with a recorded decision that Admin HAS notified the
    client about (client_notified=True). Backs the Admin dashboard's
    "Notified Applications" list - the counterpart queue an application
    moves to once NotifyClientAPIView fires for it.
    """
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
                    ).filter(client_notified=True)

        return qs.order_by(Coalesce("client_notified_at", "submission_date", "created_at").desc())


class NotifyClientAPIView(APIView):
    """
    Admin notifies the client that a decision (APPROVED/REJECTED) has
    been recorded. Until this fires, client-facing serializers cap the
    application's visible status at "SUBMITTED" ("Awaiting Embassy
    Decision") - see VisaApplicationSerializer.to_representation and
    VisaApplicationDetailSerializer.to_representation. Backs the
    "Notify Client" action on the Admin dashboard's Finalized
    Applications list - once notified, the application moves off that
    list onto "Notified Applications" (see NotifiedApplicationsListAPIView).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        if not (user.role == "Admin" or user.is_superuser):
            return Response({"error": "Only Admin can notify the client."}, status=status.HTTP_403_FORBIDDEN)

        application = get_object_or_404(VisaApplication, pk=pk)

        if application.status not in ("APPROVED", "REJECTED"):
            return Response(
                {"error": "Only applications with a recorded decision (Approved/Rejected) can be notified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if application.client_notified:
            return Response(
                {"error": "Client has already been notified for this application."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        application.client_notified = True
        application.notified_by = getattr(user, "staff_profile", None)
        application.client_notified_at = timezone.now()
        application.save(update_fields=["client_notified", "notified_by", "client_notified_at"])

        AuditLog.objects.create(
            user=user,
            action="update",
            module="Applications",
            description=(
                f"Notified client of {application.get_status_display()} decision "
                f"for {application.reference_no}"
            ),
        )

        return Response(
            VisaApplicationSerializer(application, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class VisaApplicationDetailAPIViewW(RetrieveAPIView):
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

    # Deterministic stage order (Admission -> CAS -> Visa) so the
    # "tabbed"/grouped-by-stage requirement views on the front end never
    # depend on incidental DB insertion order.
    STAGE_ORDER = Case(
        When(stage="ADMISSION", then=0),
        When(stage="CAS", then=1),
        When(stage="VISA", then=2),
        default=3,
        output_field=IntegerField(),
    )

    def get_queryset(self):
        country = self.request.query_params.get("country")
        visa_type = self.request.query_params.get("visa_type")
        qs = DocumentRequirement.objects.all()
        if country:
            qs = qs.filter(country=country)
        if visa_type:
            qs = qs.filter(visa_type=visa_type)
        return qs.annotate(stage_order=self.STAGE_ORDER).order_by("stage_order", "name")



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
    authentication_classes = [SessionAuthentication]
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
        from Applications.notifications import notify_visa_decision

        # after updating status
        application.status = decision
        application.decision_date = timezone.now().date()
        application.save(update_fields=["status", "decision_date"])

        notify_visa_decision(application)  # ✅ SEND EMAIL
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





# ------------------------------------------------------------------
# Shared dashboard-metrics helpers, used by both
# CaseOfficerDashboardMetricsAPIView (scoped to one officer's caseload)
# and AdminDashboardMetricsAPIView (system-wide) so the "Monthly Output",
# "Visa Applications" and "Trending visa locations" widgets compute
# identically regardless of which dashboard is asking - only the
# queryset scope (and, for Admin, the activity source) differs.
# ------------------------------------------------------------------

def _dashboard_month_bounds(year, month):
    start = timezone.make_aware(datetime(year, month, 1))
    last_day = calendar.monthrange(year, month)[1]
    end = timezone.make_aware(datetime(year, month, last_day, 23, 59, 59))
    return start, end


def _dashboard_monthly_output(applications, now):
    """
    this month's decided-applications count within `applications`, the
    month-over-month % change, and a radial "share of the total set
    closed out this month" percentage.
    """
    this_start, this_end = _dashboard_month_bounds(now.year, now.month)
    prev_month = now.month - 1 or 12
    prev_year = now.year if now.month > 1 else now.year - 1
    prev_start, prev_end = _dashboard_month_bounds(prev_year, prev_month)

    decided = applications.filter(status__in=["APPROVED", "REJECTED"])
    this_month_count = decided.filter(decision_date__range=(this_start, this_end)).count()
    previous_month_count = decided.filter(decision_date__range=(prev_start, prev_end)).count()

    if previous_month_count == 0:
        percent_change = 100 if this_month_count > 0 else 0
        trend = "up" if this_month_count > 0 else "flat"
    else:
        percent_change = round(
            (this_month_count - previous_month_count) / previous_month_count * 100
        )
        trend = "up" if percent_change > 0 else ("down" if percent_change < 0 else "flat")

    total = applications.count()
    radial_percent = (
        min(100, round(this_month_count / total * 100))
        if total else 0
    )

    return {
        "this_month": this_month_count,
        "previous_month": previous_month_count,
        "percent_change": abs(percent_change),
        "trend": trend,
        "radial_percent": radial_percent,
    }


def _dashboard_visa_applications_series(applications, now):
    """
    Week / Month / Year stacked series (Approved / Rejected / Pending) of
    `applications`, bucketed by created_at.
    """
    rows = list(applications.values("created_at", "status"))

    def build_series(labels, key_fn):
        buckets = {label: {"Approved": 0, "Rejected": 0, "Pending": 0} for label in labels}
        for row in rows:
            created = timezone.localtime(row["created_at"])
            key = key_fn(created)
            if key not in buckets:
                continue
            if row["status"] == "APPROVED":
                buckets[key]["Approved"] += 1
            elif row["status"] == "REJECTED":
                buckets[key]["Rejected"] += 1
            else:
                buckets[key]["Pending"] += 1
        return {
            "categories": labels,
            "series": [
                {"name": "Approved", "data": [buckets[l]["Approved"] for l in labels]},
                {"name": "Rejected", "data": [buckets[l]["Rejected"] for l in labels]},
                {"name": "Pending", "data": [buckets[l]["Pending"] for l in labels]},
            ],
        }

    # Year: Jan..Dec of the current year
    year_labels = [calendar.month_abbr[m] for m in range(1, 13)]
    year_data = build_series(
        year_labels,
        lambda d: calendar.month_abbr[d.month] if d.year == now.year else None,
    )

    # Month: every day of the current month
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    month_labels = [str(d) for d in range(1, days_in_month + 1)]
    month_data = build_series(
        month_labels,
        lambda d: str(d.day) if (d.year, d.month) == (now.year, now.month) else None,
    )

    # Week: the last 7 days, including today
    week_dates = [(now - timedelta(days=i)).date() for i in range(6, -1, -1)]
    week_labels = [d.strftime("%a %d") for d in week_dates]
    week_label_by_date = dict(zip(week_dates, week_labels))
    week_data = build_series(
        week_labels,
        lambda d: week_label_by_date.get(d.date()),
    )

    return {"week": week_data, "month": month_data, "year": year_data}


def _dashboard_trending_locations():
    """System-wide top 3 destination countries by total application count."""
    country_counts = list(
        VisaApplication.objects.values("country")
        .annotate(total=Count("id"))
        .order_by("-total")[:3]
    )
    country_display = dict(VisaApplication.COUNTRIES)
    max_count = country_counts[0]["total"] if country_counts else 0
    return [
        {
            "country": country_display.get(c["country"], c["country"]),
            "count": c["total"],
            "percent": round(c["total"] / max_count * 100) if max_count else 0,
        }
        for c in country_counts
    ]


class CaseOfficerDashboardMetricsAPIView(APIView):
    """
    Aggregated metrics for the Case Officer dashboard
    (case_officer/case_officer_dashboard1.html), replacing the theme's
    static/hardcoded placeholder numbers:

      - monthly_output: this month's decided-applications count for the
        officer, the month-over-month % change, and a radial "share of
        total caseload closed out this month" percentage.
      - visa_applications: Week / Month / Year stacked series (Approved /
        Rejected / Pending) of the officer's own applications (assigned to
        or initiated by them), bucketed by created_at.
      - activity: the officer's last 4 real events - application
        initiated, decision recorded, a task assigned to them, or a
        reassignment to/from them - merged from VisaApplication /
        TaskAssignment / ReassignmentLog and sorted by timestamp.
      - trending_locations: system-wide top 3 destination countries by
        total application count.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        officer = getattr(request.user, "staff_profile", None)
        if officer is None:
            return Response(
                {"error": "No case officer profile for this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        applications = VisaApplication.objects.filter(
            Q(created_by_officer=officer) | Q(assigned_officer=officer)
        )

        now = timezone.localtime(timezone.now())

        monthly_output = _dashboard_monthly_output(applications, now)
        visa_applications = _dashboard_visa_applications_series(applications, now)

        # ------------------------------------------------------------
        # Activity - the officer's last 4 real events
        # ------------------------------------------------------------
        events = []

        initiated = VisaApplication.objects.filter(
            created_by_officer=officer
        ).select_related("client__user")
        for app in initiated:
            events.append({
                "timestamp": app.created_at,
                "description": (
                    f"You initiated application {app.reference_no} for "
                    f"{app.client.user.get_full_name}"
                ),
            })

        decisions = applications.filter(
            status__in=["APPROVED", "REJECTED"], decision_date__isnull=False
        )
        for app in decisions:
            events.append({
                "timestamp": app.decision_date,
                "description": (
                    f"You recorded a decision ({app.get_status_display()}) "
                    f"on {app.reference_no}"
                ),
            })

        tasks = TaskAssignment.objects.filter(assigned_to=officer).select_related("application")
        for task in tasks:
            events.append({
                "timestamp": task.created_at,
                "description": f"Application {task.application.reference_no} was assigned to you",
            })

        reassigned_to_me = ReassignmentLog.objects.filter(to_officer=officer).select_related("application")
        for log in reassigned_to_me:
            events.append({
                "timestamp": log.created_at,
                "description": f"Application {log.application.reference_no} was reassigned to you",
            })

        reassigned_from_me = ReassignmentLog.objects.filter(from_officer=officer).select_related("application")
        for log in reassigned_from_me:
            events.append({
                "timestamp": log.created_at,
                "description": f"Application {log.application.reference_no} was reassigned away from you",
            })

        events.sort(key=lambda e: e["timestamp"], reverse=True)
        activity = [
            {
                "date": timezone.localtime(e["timestamp"]).strftime("%d %b"),
                "description": e["description"],
            }
            for e in events[:4]
        ]

        return Response({
            "monthly_output": monthly_output,
            "visa_applications": visa_applications,
            "activity": activity,
            "trending_locations": _dashboard_trending_locations(),
        })


class AdminDashboardMetricsAPIView(APIView):
    """
    Aggregated metrics for the Admin dashboard (admin/admin_dashboard.html),
    replacing the theme's static/hardcoded placeholder numbers. Unlike the
    Case Officer version, everything here is system-wide (all applications,
    not one officer's caseload):

      - monthly_output: this month's system-wide decided-applications
        count, the month-over-month % change, and a radial "share of all
        applications closed out this month" percentage.
      - visa_applications: Week / Month / Year stacked series (Approved /
        Rejected / Pending) across every application, bucketed by
        created_at.
      - activity: the logged-in Admin's own last 4 actions, read from
        AuditLog (validate-assignment, reassign, notify-client - the
        actions Admin views already write there).
      - trending_locations: system-wide top 3 destination countries by
        total application count (identical computation to the Case
        Officer dashboard's version, since it was never officer-scoped).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not (user.role == "Admin" or user.is_superuser):
            return Response(
                {"error": "Only Admin can view this dashboard's metrics."},
                status=status.HTTP_403_FORBIDDEN,
            )

        applications = VisaApplication.objects.all()
        now = timezone.localtime(timezone.now())

        monthly_output = _dashboard_monthly_output(applications, now)
        visa_applications = _dashboard_visa_applications_series(applications, now)

        # ------------------------------------------------------------
        # Activity - this Admin's last 4 logged actions
        # ------------------------------------------------------------
        recent_logs = AuditLog.objects.filter(user=user).order_by("-timestamp")[:4]
        activity = [
            {
                "date": timezone.localtime(log.timestamp).strftime("%d %b"),
                "description": log.description or log.get_action_display(),
            }
            for log in recent_logs
        ]

        return Response({
            "monthly_output": monthly_output,
            "visa_applications": visa_applications,
            "activity": activity,
            "trending_locations": _dashboard_trending_locations(),
        })
