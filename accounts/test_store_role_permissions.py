from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.store_roles import (
    STORE_OWNER,
    STORE_MANAGER,
    ORDER_STAFF,
    INVENTORY_STAFF,
    FINANCE_STAFF,
    SUPPORT_STAFF,
)


User = get_user_model()


class StoreRolePermissionMatrixTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        call_command(
            "setup_store_roles"
        )

        cls.users = {}

        role_names = [
            STORE_OWNER,
            STORE_MANAGER,
            ORDER_STAFF,
            INVENTORY_STAFF,
            FINANCE_STAFF,
            SUPPORT_STAFF,
        ]

        for index, role_name in enumerate(
            role_names,
            start=1,
        ):

            user = User.objects.create_user(
                username=f"role-user-{index}",
                email=(
                    f"role-user-{index}"
                    "@example.com"
                ),
                password="StrongPass123!",
                is_active=True,
                is_staff=True,
                role="admin",
            )

            user.groups.add(
                Group.objects.get(
                    name=role_name
                )
            )

            cls.users[
                role_name
            ] = user


        # Deliberately create an is_staff account
        # with NO authorized store role.
        cls.unassigned_staff = (
            User.objects.create_user(
                username="unassigned-staff",
                email="unassigned@example.com",
                password="StrongPass123!",
                is_active=True,
                is_staff=True,
                role="admin",
            )
        )


        # Multiple roles should combine permissions,
        # not accidentally grant unrestricted access.
        cls.multi_role_staff = (
            User.objects.create_user(
                username="multi-role-staff",
                email="multi-role@example.com",
                password="StrongPass123!",
                is_active=True,
                is_staff=True,
                role="admin",
            )
        )

        cls.multi_role_staff.groups.add(
            Group.objects.get(
                name=ORDER_STAFF
            ),
            Group.objects.get(
                name=FINANCE_STAFF
            ),
        )


    # ========================================================
    # HELPERS
    # ========================================================

    def login_role(
        self,
        role_name,
    ):

        self.client.force_login(
            self.users[
                role_name
            ]
        )


    def assert_allowed(
        self,
        url_name,
    ):

        response = self.client.get(
            reverse(
                url_name
            )
        )

        self.assertEqual(
            response.status_code,
            200,
            msg=(
                f"{url_name} should be accessible "
                f"but returned "
                f"{response.status_code}."
            ),
        )


    def assert_denied(
        self,
        url_name,
    ):

        response = self.client.get(
            reverse(
                url_name
            )
        )

        self.assertEqual(
            response.status_code,
            302,
            msg=(
                f"{url_name} should be denied "
                f"but returned "
                f"{response.status_code}."
            ),
        )

        self.assertEqual(
            response.url,
            reverse(
                "admin_dashboard"
            ),
            msg=(
                f"{url_name} did not redirect "
                f"to the store dashboard."
            ),
        )


    # ========================================================
    # STORE OWNER
    # ========================================================

    def test_store_owner_has_full_store_access(self):

        self.login_role(
            STORE_OWNER
        )

        allowed = [
            "admin_dashboard",
            "admin_order_list",
            "delivery_list",
            "admin_product_list",
            "inventory_dashboard",
            "admin_payment_list",
            "admin_returns_refunds",
            "crm_customer_list",
            "admin_notifications",
            "admin_analytics",
            "admin_store_settings",
            "staff_manage_list",
        ]

        for url_name in allowed:

            with self.subTest(
                url_name=url_name
            ):

                self.assert_allowed(
                    url_name
                )


    # ========================================================
    # STORE MANAGER
    # ========================================================

    def test_store_manager_operational_access(self):

        self.login_role(
            STORE_MANAGER
        )

        allowed = [
            "admin_dashboard",
            "admin_order_list",
            "delivery_list",
            "admin_product_list",
            "inventory_dashboard",
            "admin_payment_list",
            "admin_returns_refunds",
            "crm_customer_list",
            "admin_notifications",
            "admin_analytics",
        ]

        for url_name in allowed:

            with self.subTest(
                allowed=url_name
            ):

                self.assert_allowed(
                    url_name
                )


    def test_store_manager_cannot_manage_owner_only_areas(
        self
    ):

        self.login_role(
            STORE_MANAGER
        )

        denied = [
            "admin_store_settings",
            "staff_manage_list",
        ]

        for url_name in denied:

            with self.subTest(
                denied=url_name
            ):

                self.assert_denied(
                    url_name
                )


    # ========================================================
    # ORDERS STAFF
    # ========================================================

    def test_orders_staff_allowed_areas(self):

        self.login_role(
            ORDER_STAFF
        )

        for url_name in [
            "admin_dashboard",
            "admin_order_list",
            "delivery_list",
        ]:

            with self.subTest(
                allowed=url_name
            ):

                self.assert_allowed(
                    url_name
                )


    def test_orders_staff_cannot_access_sensitive_areas(
        self
    ):

        self.login_role(
            ORDER_STAFF
        )

        denied = [
            "admin_product_list",
            "inventory_dashboard",
            "admin_payment_list",
            "admin_returns_refunds",
            "crm_customer_list",
            "admin_notifications",
            "admin_analytics",
            "admin_store_settings",
            "staff_manage_list",
        ]

        for url_name in denied:

            with self.subTest(
                denied=url_name
            ):

                self.assert_denied(
                    url_name
                )


    # ========================================================
    # INVENTORY STAFF
    # ========================================================

    def test_inventory_staff_allowed_areas(self):

        self.login_role(
            INVENTORY_STAFF
        )

        for url_name in [
            "admin_dashboard",
            "admin_product_list",
            "inventory_dashboard",
        ]:

            with self.subTest(
                allowed=url_name
            ):

                self.assert_allowed(
                    url_name
                )


    def test_inventory_staff_cannot_access_other_departments(
        self
    ):

        self.login_role(
            INVENTORY_STAFF
        )

        denied = [
            "admin_order_list",
            "delivery_list",
            "admin_payment_list",
            "admin_returns_refunds",
            "crm_customer_list",
            "admin_notifications",
            "admin_analytics",
            "admin_store_settings",
            "staff_manage_list",
        ]

        for url_name in denied:

            with self.subTest(
                denied=url_name
            ):

                self.assert_denied(
                    url_name
                )


    # ========================================================
    # FINANCE STAFF
    # ========================================================

    def test_finance_staff_allowed_areas(self):

        self.login_role(
            FINANCE_STAFF
        )

        allowed = [
            "admin_dashboard",
            "admin_order_list",
            "admin_payment_list",
            "admin_returns_refunds",
            "admin_analytics",
        ]

        for url_name in allowed:

            with self.subTest(
                allowed=url_name
            ):

                self.assert_allowed(
                    url_name
                )


    def test_finance_staff_cannot_modify_operations(
        self
    ):

        self.login_role(
            FINANCE_STAFF
        )

        denied = [
            "admin_product_list",
            "inventory_dashboard",
            "delivery_list",
            "crm_customer_list",
            "admin_notifications",
            "admin_store_settings",
            "staff_manage_list",
        ]

        for url_name in denied:

            with self.subTest(
                denied=url_name
            ):

                self.assert_denied(
                    url_name
                )


    # ========================================================
    # SUPPORT STAFF
    # ========================================================

    def test_support_staff_allowed_areas(self):

        self.login_role(
            SUPPORT_STAFF
        )

        allowed = [
            "admin_dashboard",
            "admin_order_list",
            "crm_customer_list",
            "admin_notifications",
            "admin_abandoned_cart_list",
        ]

        for url_name in allowed:

            with self.subTest(
                allowed=url_name
            ):

                self.assert_allowed(
                    url_name
                )


    def test_support_staff_cannot_access_finance_or_inventory(
        self
    ):

        self.login_role(
            SUPPORT_STAFF
        )

        denied = [
            "admin_product_list",
            "inventory_dashboard",
            "delivery_list",
            "admin_payment_list",
            "admin_returns_refunds",
            "admin_analytics",
            "admin_store_settings",
            "staff_manage_list",
        ]

        for url_name in denied:

            with self.subTest(
                denied=url_name
            ):

                self.assert_denied(
                    url_name
                )


    # ========================================================
    # DEFENCE IN DEPTH
    # ========================================================

    def test_is_staff_without_store_role_is_not_enough(self):

        self.client.force_login(
            self.unassigned_staff
        )

        for url_name in [
            "admin_order_list",
            "admin_product_list",
            "admin_payment_list",
            "admin_notifications",
        ]:

            with self.subTest(
                denied=url_name
            ):

                self.assert_denied(
                    url_name
                )


    def test_multiple_roles_combine_only_their_permissions(
        self
    ):

        self.client.force_login(
            self.multi_role_staff
        )

        # Orders role
        self.assert_allowed(
            "delivery_list"
        )

        # Finance role
        self.assert_allowed(
            "admin_payment_list"
        )

        # Neither role grants inventory
        self.assert_denied(
            "inventory_dashboard"
        )

        # Neither role grants staff management
        self.assert_denied(
            "staff_manage_list"
        )


    # ========================================================
    # DJANGO MODEL PERMISSIONS
    # ========================================================

    def test_orders_group_model_permissions(self):

        user = self.users[
            ORDER_STAFF
        ]

        self.assertTrue(
            user.has_perm(
                "orders.view_order"
            )
        )

        self.assertTrue(
            user.has_perm(
                "orders.change_order"
            )
        )

        self.assertFalse(
            user.has_perm(
                "payments.change_refundrequest"
            )
        )


    def test_inventory_group_model_permissions(self):

        user = self.users[
            INVENTORY_STAFF
        ]

        self.assertTrue(
            user.has_perm(
                "products.change_product"
            )
        )

        self.assertTrue(
            user.has_perm(
                "inventory.change_inventorymovement"
            )
        )

        self.assertFalse(
            user.has_perm(
                "payments.change_mpesatransaction"
            )
        )


    def test_finance_group_model_permissions(self):

        user = self.users[
            FINANCE_STAFF
        ]

        self.assertTrue(
            user.has_perm(
                "payments.change_mpesatransaction"
            )
        )

        self.assertTrue(
            user.has_perm(
                "payments.change_refundrequest"
            )
        )

        self.assertFalse(
            user.has_perm(
                "products.change_product"
            )
        )


    def test_support_group_model_permissions(self):

        user = self.users[
            SUPPORT_STAFF
        ]

        self.assertTrue(
            user.has_perm(
                "crm.view_customernote"
            )
        )

        self.assertTrue(
            user.has_perm(
                "notifications.view_notification"
            )
        )

        self.assertFalse(
            user.has_perm(
                "payments.change_refundrequest"
            )
        )
