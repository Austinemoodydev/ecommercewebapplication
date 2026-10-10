from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):

    CUSTOMER = "customer"
    ADMIN = "admin"

    ROLE_CHOICES = [
        (CUSTOMER, "Customer"),
        (ADMIN, "Administrator"),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=CUSTOMER,
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
    )

    avatar = models.ImageField(
        upload_to="avatars/",
        blank=True,
        null=True,
    )

    email_verified = models.BooleanField(
        default=False,
    )

    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=True)

    def __str__(self):
        return self.username

class UserProfile(models.Model):

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    date_of_birth = models.DateField(
        null=True,
        blank=True,
    )

    gender = models.CharField(
        max_length=20,
        blank=True,
    )

    bio = models.TextField(
        blank=True,
    )

    def __str__(self):
        return self.user.username

class Address(models.Model):

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="addresses",
    )

    full_name = models.CharField(max_length=150)

    phone = models.CharField(max_length=20)

    county = models.CharField(max_length=100)

    city = models.CharField(max_length=100)

    estate = models.CharField(max_length=150)

    house_number = models.CharField(max_length=50)

    landmark = models.CharField(
        max_length=255,
        blank=True,
    )

    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.full_name


class StaffSecurityEvent(models.Model):
    ACTION_CREATED = "created"
    ACTION_UPDATED = "updated"
    ACTION_ROLE_CHANGED = "role_changed"
    ACTION_SUSPENDED = "suspended"
    ACTION_REACTIVATED = "reactivated"
    ACTION_MFA_ENABLED = "mfa_enabled"
    ACTION_MFA_RESET = "mfa_reset"

    ACTION_CHOICES = [
        (ACTION_CREATED, "Account created"),
        (ACTION_UPDATED, "Profile updated"),
        (ACTION_ROLE_CHANGED, "Role changed"),
        (ACTION_SUSPENDED, "Account suspended"),
        (ACTION_REACTIVATED, "Account reactivated"),
        (ACTION_MFA_ENABLED, "MFA enabled"),
        (ACTION_MFA_RESET, "MFA reset"),
    ]

    actor = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True,
        related_name="staff_security_actions",
    )
    target = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE,
        related_name="staff_security_history",
    )
    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        permissions = [
            ("manage_staff", "Can manage department staff"),
            ("manage_managers", "Can manage store managers"),
            ("assign_sensitive_staff_roles", "Can assign sensitive staff roles"),
            ("reset_staff_mfa", "Can reset staff MFA"),
            ("view_staff_security_history", "Can view staff security history"),
        ]

    def __str__(self):
        return f"{self.get_action_display()}: {self.target}"
