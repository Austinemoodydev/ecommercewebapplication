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
    #Later, we'll preload Nairobi estates and support GPS/location detection.