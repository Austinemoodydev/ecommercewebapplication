from accounts.store_roles import STORE_OWNER
from django.contrib.auth.models import Group
from pathlib import Path

from django.contrib.auth import (
    get_user_model,
)

from django.test import (
    TestCase,
)

from django.urls import reverse


User = get_user_model()


class LayoutIsolationTests(
    TestCase
):

    def setUp(self):

        self.staff = (
            User.objects.create_user(
                username="layoutstaff",
                password="pass12345",
                role=User.ADMIN,
                is_staff=True,
            )
        )

        store_owner_group, _ = Group.objects.get_or_create(
            name=STORE_OWNER,
        )

        self.staff.groups.add(
            store_owner_group
        )


    def test_admin_analytics_uses_admin_shell(
        self
    ):

        self.client.login(
            username="layoutstaff",
            password="pass12345",
        )

        response = self.client.get(
            reverse(
                "admin_analytics"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        content = response.content.decode(
            "utf-8"
        )

        self.assertIn(
            "admin-layout",
            content,
        )

        self.assertIn(
            "admin-dashboard.css",
            content,
        )

        self.assertNotIn(
            "storefront-nav",
            content,
        )

        self.assertNotIn(
            "whatsapp-float",
            content,
        )

        self.assertNotIn(
            'css/styles.css',
            content,
        )


    def test_admin_analytics_template_uses_admin_base(
        self
    ):

        root = Path(
            __file__
        ).resolve().parent.parent

        path = (
            root
            / "templates"
            / "dashboard"
            / "admin_analytics.html"
        )

        source = path.read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            '{% extends "dashboard/admin/base.html" %}',
            source,
        )

        self.assertNotIn(
            '{% extends "base.html" %}',
            source,
        )


    def test_admin_base_does_not_load_storefront_css(
        self
    ):

        root = Path(
            __file__
        ).resolve().parent.parent

        path = (
            root
            / "templates"
            / "dashboard"
            / "admin"
            / "base.html"
        )

        source = path.read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            "admin-dashboard.css",
            source,
        )

        self.assertNotIn(
            "css/styles.css",
            source,
        )


    def test_storefront_base_does_not_load_admin_css(
        self
    ):

        root = Path(
            __file__
        ).resolve().parent.parent

        path = (
            root
            / "templates"
            / "base.html"
        )

        source = path.read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            "css/styles.css",
            source,
        )

        self.assertNotIn(
            "admin-dashboard.css",
            source,
        )
