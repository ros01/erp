from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import RetrieveAPIView
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Q, Value
from Documents.models import DocumentRequirement, Document
from Accounts.models import *
from .models import VisaApplication, PreviousRefusalLetter, RejectionLetter
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


User = get_user_model()

# views.py
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
                    if "name" in lname:
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
    POST  → upload one or more rejection letters (REJECTED only)
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

        files = request.FILES.getlist("rejection_letters")
        if not files:
            return Response({"error": "No files uploaded"}, status=400)

        for file in files:
            RejectionLetter.objects.create(
                application=application,
                file=file
            )

        # 🔥 IMPORTANT: re-fetch with related data
        application = VisaApplication.objects.prefetch_related(
            "rejection_letters"
        ).get(pk=pk)

        return Response(
            VisaApplicationSerializer(application).data,
            status=200
        )


    # def post(self, request, pk):
    #     application = get_object_or_404(VisaApplication, pk=pk)

    #     # 🚫 Safety: only allow uploads for REJECTED apps
    #     if application.status != "REJECTED":
    #         return Response(
    #             {"error": "Rejection letters can only be uploaded for rejected applications"},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )

    #     files = request.FILES.getlist("rejection_letters")

    #     if not files:
    #         return Response(
    #             {"error": "No rejection files uploaded"},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )

    #     uploaded = []
    #     for file in files:
    #         letter = RejectionLetter.objects.create(
    #             application=application,
    #             file=file
    #         )
    #         uploaded.append(letter.file.url)

    #     return Response(
    #         {
    #             "message": "Rejection letter(s) uploaded successfully",
    #             "rejection_letters": uploaded
    #         },
    #         status=status.HTTP_200_OK
    #     )



class AddVisaApplicationDecisionAPIViewW(APIView):
    def patch(self, request, pk):
        """Approve/Reject a visa application"""
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

        # ✅ Decrease workload on officer (initiator or assigned)
        staff = application.assigned_officer or application.created_by_officer
        if staff and staff.workload > 0:
            staff.workload -= 1
            staff.save(update_fields=["workload"])

        return Response(VisaApplicationSerializer(application).data, status=200)

    def post(self, request, pk):
        """Upload a rejection letter for a rejected application"""
        try:
            application = VisaApplication.objects.get(pk=pk)
        except VisaApplication.DoesNotExist:
            return Response({"error": "Application not found"}, status=404)

        if "rejection_letter" not in request.FILES:
            return Response({"error": "No file uploaded"}, status=400)

        # ✅ Save rejection letter
        application.rejection_letter = request.FILES["rejection_letter"]
        application.save(update_fields=["rejection_letter", "updated_at"])

        return Response(
            {"rejection_letter": application.rejection_letter.url},
            status=200
        )


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


class UploadRejectionLetterAPIViewW(APIView):
    def patch(self, request, pk):
        try:
            application = VisaApplication.objects.get(pk=pk)
        except VisaApplication.DoesNotExist:
            return Response({"error": "Application not found"}, status=404)

        file = request.FILES.get("rejection_letter")
        if not file:
            return Response({"error": "No file uploaded"}, status=400)

        application.rejection_letter = file
        application.save(update_fields=["rejection_letter", "updated_at"])

        return Response(VisaApplicationSerializer(application).data)


# api_views.py

class UploadRejectionLetterAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        application = get_object_or_404(VisaApplication, pk=pk)

        files = request.FILES.getlist("rejection_letters")
        if not files:
            return Response({"detail": "No files uploaded"}, status=400)

        for f in files:
            RejectionLetter.objects.create(
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



