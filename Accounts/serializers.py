from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ClientProfile

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "middle_name",
            "phone",
            "role",
            "is_active",
            "is_staff",
            "full_name",
        ]
        read_only_fields = ["id", "is_active", "is_staff", "role", "full_name"]


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Used when creating a new client user."""

    password = serializers.CharField(write_only=True, min_length=8)
    full_name = serializers.CharField(source="get_full_name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "password",
            "first_name",
            "last_name",
            "middle_name",
            "phone",
            "role",
            "full_name",
        ]
        extra_kwargs = {"role": {"default": "Client"}}

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.role = "Client"
        user.save()
        return user


class ClientProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), write_only=True, source="user"
    )

    class Meta:
        model = ClientProfile
        fields = [
            "id",
            "user",
            "user_id",
            "passport_number",
            "nationality",
            "date_of_birth",
            "address",
            "created_on",
        ]
        read_only_fields = ["id", "created_on", "user"]


# class ClientRegistrationSerializer(serializers.ModelSerializer):
#     """
#     Combines User + ClientProfile creation in one serializer.
#     Useful when registering a new Client from the frontend.
#     """

#     user = UserRegistrationSerializer()

#     class Meta:
#         model = ClientProfile
#         fields = [
#             "id",
#             "user",
#             "passport_number",
#             "nationality",
#             "date_of_birth",
#             "address",
#             "created_on",
#         ]
#         read_only_fields = ["id", "created_on"]

#     def create(self, validated_data):
#         user_data = validated_data.pop("user")
#         user = UserRegistrationSerializer().create(user_data)
#         client_profile = ClientProfile.objects.create(user=user, **validated_data)
#         return client_profile






class ClientRegistrationSerializer(serializers.ModelSerializer):
    user = UserRegistrationSerializer()

    class Meta:
        model = ClientProfile
        fields = [
            "user",
            "passport_number",
            "nationality",
            "date_of_birth",
            "address",
        ]

    def create(self, validated_data):
        # Extract user data
        user_data = validated_data.pop("user")

        # Default role to Client if not explicitly provided
        user_data.setdefault("role", "Client")

        # Create User first
        user = User.objects.create_user(**user_data)

        # Create ClientProfile linked to this user
        client_profile = ClientProfile.objects.create(user=user, **validated_data)

        return client_profile

    def to_representation(self, instance):
        """
        Ensures response includes both user and client details.
        """
        rep = super().to_representation(instance)
        rep["user"] = UserRegistrationSerializer(instance.user).data
        return rep

