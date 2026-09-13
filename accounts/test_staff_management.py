from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.store_roles import (
    STORE_OWNER,
    ORDER_STAFF,
    INVENTORY_STAFF,
    FINANCE_STAFF,
    SUPPORT_STAFF,
)


User = get_user_model()


class StaffManagementTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        call_command(
            "setup_store_roles"
        )

        cls.owner = (
            User.objects.create_user(
                username="owner",
                email="owner@example.com",
                password="StrongPass123!",
                is_staff=True,
                is_active=True,
            )
        )

        cls.owner.groups.add(
            Group.objects.get(
                name=STORE_OWNER
            )
        )


        cls.order_staff = (
            User.objects.create_user(
                username="orders",
                email="orders@example.com",
                password="StrongPass123!",
                is_staff=True,
                is_active=True,
            )
        )

        cls.order_staff.groups.add(
            Group.objects.get(
                name=ORDER_STAFF
            )
        )


        cls.customer = (
            User.objects.create_user(
                username="customer",
                email="customer@example.com",
                password="StrongPass123!",
                is_staff=False,
                is_active=True,
            )
        )


    def test_owner_can_view_staff_management(self):

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            reverse(
                "staff_manage_list"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Staff Management",
        )


    def test_regular_staff_cannot_manage_staff(self):

        self.client.force_login(
            self.order_staff
        )

        response = self.client.get(
            reverse(
                "staff_manage_list"
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "admin_dashboard"
            ),
        )


    def test_customer_cannot_manage_staff(self):

        self.client.force_login(
            self.customer
        )

        response = self.client.get(
            reverse(
                "staff_manage_list"
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )


    def test_owner_can_create_inventory_staff(self):

        self.client.force_login(
            self.owner
        )

        role = Group.objects.get(
            name=INVENTORY_STAFF
        )

        response = self.client.post(
            reverse(
                "staff_manage_create"
            ),
            {
                "username": "inventoryuser",
                "first_name": "Inventory",
                "last_name": "User",
                "email": "inventory@example.com",
                "phone": "0712345678",
                "role_group": role.pk,
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        created = User.objects.get(
            username="inventoryuser"
        )

        self.assertTrue(
            created.is_staff
        )

        self.assertTrue(
            created.groups.filter(
                name=INVENTORY_STAFF
            ).exists()
        )


    def test_staff_toggle_requires_post(self):

        self.client.force_login(
            self.owner
        )

        response = self.client.get(
            reverse(
                "staff_manage_toggle_active",
                args=[
                    self.order_staff.pk
                ],
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )


    def test_owner_can_disable_staff(self):

        self.client.force_login(
            self.owner
        )

        response = self.client.post(
            reverse(
                "staff_manage_toggle_active",
                args=[
                    self.order_staff.pk
                ],
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "staff_manage_list"
            ),
        )

        self.order_staff.refresh_from_db()

        self.assertFalse(
            self.order_staff.is_active
        )


class StoreRoleCreationTests(TestCase):

    def test_setup_command_creates_all_roles(self):

        call_command(
            "setup_store_roles"
        )

        for role_name in [
            STORE_OWNER,
            ORDER_STAFF,
            INVENTORY_STAFF,
            FINANCE_STAFF,
            SUPPORT_STAFF,
        ]:

            self.assertTrue(
                Group.objects.filter(
                    name=role_name
                ).exists()
            )
