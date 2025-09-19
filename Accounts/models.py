import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.models import BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
# Extend Django’s User model to include role & extra fields

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class MyUserManager(BaseUserManager):
    """
    A custom user manager to deal with emails as unique identifiers for auth
    instead of usernames. The default that's used is "UserManager"
    """
    def create_user(self, email, password, **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model for the ERP system.
    Inherits username, email, first_name, last_name, password, etc.
    """
    ROLE_CHOICES = [
        ("Admin", "Admin"),
        ("Case Officer", "Case Officer"),
        ("Finance", "Finance"),
        ("Support", "Support"),
        ("Client", "Client"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="Client")
    # Example extra fields if needed:
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    middle_name = models.CharField(max_length=30, blank=True)
    slug  = models.SlugField(blank=True, null=True, unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    USERNAME_FIELD = 'email'
    objects = MyUserManager()

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property 
    def get_full_name(self):
        '''
        Returns the first_name plus the last_name, with a space in between.
        '''
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()


    def get_short_name(self):
        return self.email

class ClientProfile(models.Model):
    # full_name = models.CharField(max_length=255)
    # email = models.EmailField(unique=True)
    # phone = models.CharField(max_length=20, blank=True, null=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="client_profile")
    passport_number = models.CharField(max_length=50, unique=True)
    nationality = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    address = models.TextField(blank=True, null=True)
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.last_name} ({self.passport_number})"

    class Meta:
        indexes = [models.Index(fields=["passport_number", "user"])]


class StaffProfile(models.Model):
    """
    Staff-specific profile data (for Admin, CaseOfficer, Finance, Support).
    Clients will usually not have this profile.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="staff_profile")
    department = models.CharField(max_length=100, blank=True, null=True)
    designation = models.CharField(max_length=100, blank=True, null=True)
    is_available = models.BooleanField(default=True)  # For auto-assignment workload strategy
    workload = models.IntegerField(default=0)  # number of active cases
    created_on = models.DateTimeField(auto_now_add=True)


    # def __str__(self):
    #     return f"{self.user.get_full_name()} - {self.user.role}"

    def __str__(self):
        return f"{self.user.last_name} - {self.user.role}"


class AuditLog(models.Model):
    """
    Generic system-wide audit logging.
    Tracks actions (login, CRUD, reassignments, etc.)
    """
    ACTION_TYPES = [
        ("create", "Create"),
        ("read", "Read"),
        ("update", "Update"),
        ("delete", "Delete"),
        ("assign", "Assignment"),
        ("login", "Login"),
        ("logout", "Logout"),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="audit_logs")
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    module = models.CharField(max_length=50)  # e.g., Applications, Finance
    description = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.action} - {self.module}"

