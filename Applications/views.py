from django.shortcuts import render
from rest_framework import generics, permissions
from .models import VisaApplication
from .serializers import VisaApplicationSerializer

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
