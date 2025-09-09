# accounts/api_views.py
from rest_framework import generics, status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserSerializer

User = get_user_model()

class RegisterClientAPIView(generics.CreateAPIView):
    """
    Public registration for new clients
    """
    serializer_class = UserSerializer
    permission_classes = []  # allow anyone

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data["role"] = "CLIENT"
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"detail": "Client registered successfully"},
            status=status.HTTP_201_CREATED
        )


class LoginAPIView(generics.GenericAPIView):
    """
    JWT login endpoint
    """
    serializer_class = UserSerializer  # reuse for email/password

    def post(self, request, *args, **kwargs):
        from django.contrib.auth import authenticate

        email = request.data.get("email")
        password = request.data.get("password")
        user = authenticate(request, username=email, password=password)
        if not user:
            return Response({"detail": "Invalid credentials"}, status=400)

        refresh = RefreshToken.for_user(user)
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "role": user.role,
            "id": user.id,
        })
