from pathlib import Path
import shutil

FORMS = Path("accounts/forms.py")
VIEWS = Path("accounts/views.py")
TESTS = Path("accounts/test_ship_phase2.py")

for path in [FORMS, VIEWS]:
    if not path.exists():
        raise RuntimeError(f"Missing required file: {path}")

    backup = Path(str(path) + ".shipphase2backup")

    if not backup.exists():
        shutil.copy2(path, backup)


# ============================================================
# 1. FORMS
# ============================================================

forms = FORMS.read_text(encoding="utf-8-sig")

old = '''class RegisterForm(UserCreationForm):

    email = forms.EmailField(required=True)

    class Meta:

        model = CustomUser

        fields = (
            "username",
            "email",
            "phone",
            "password1",
            "password2",
        )
'''

new = '''class RegisterForm(UserCreationForm):

    email = forms.EmailField(required=True)

    class Meta:

        model = CustomUser

        fields = (
            "username",
            "email",
            "phone",
            "password1",
            "password2",
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if CustomUser.objects.filter(
            email__iexact=email
        ).exists():
            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email
'''

if old in forms:
    forms = forms.replace(old, new, 1)
elif "def clean_email(self):" not in forms:
    raise RuntimeError(
        "Could not safely patch RegisterForm."
    )
else:
    print("RegisterForm email protection already present.")


old_profile = '''class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ("first_name", "last_name", "email", "phone", "avatar", "email_notifications", "sms_notifications")
'''

new_profile = '''class ProfileForm(forms.ModelForm):

    class Meta:
        model = CustomUser
        fields = (
            "first_name",
            "last_name",
            "email",
            "phone",
            "avatar",
            "email_notifications",
            "sms_notifications",
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        queryset = CustomUser.objects.filter(
            email__iexact=email
        )

        if self.instance and self.instance.pk:
            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():
            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email
'''

if old_profile in forms:
    forms = forms.replace(
        old_profile,
        new_profile,
        1,
    )
elif forms.count("def clean_email(self):") < 2:
    raise RuntimeError(
        "Could not safely patch ProfileForm."
    )
else:
    print("ProfileForm email protection already present.")

FORMS.write_text(forms, encoding="utf-8")


# ============================================================
# 2. VIEWS
# ============================================================

views = VIEWS.read_text(encoding="utf-8-sig")

import_marker = (
    "from django.contrib.auth.decorators import login_required"
)

if (
    "from django.views.decorators.http import require_POST"
    not in views
):
    if import_marker not in views:
        raise RuntimeError(
            "Could not locate views import section."
        )

    views = views.replace(
        import_marker,
        import_marker
        + "\nfrom django.views.decorators.http import require_POST",
        1,
    )


old_profile_view = '''@login_required
def profile(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("profile")
    return render(request, "accounts/profile.html", {"form": form})
'''

new_profile_view = '''@login_required
def profile(request):
    form = ProfileForm(
        request.POST or None,
        request.FILES or None,
        instance=request.user,
    )

    if request.method == "POST" and form.is_valid():

        old_email = (
            request.user.email or ""
        ).strip().lower()

        user = form.save(commit=False)

        new_email = (
            user.email or ""
        ).strip().lower()

        email_changed = (
            old_email != new_email
        )

        if email_changed:
            # A verified status belongs to the old address,
            # never automatically to a replacement address.
            user.email_verified = False

        user.save()

        if email_changed:
            messages.warning(
                request,
                (
                    "Your email address changed. "
                    "The new address must be verified "
                    "before it is treated as verified."
                ),
            )
        else:
            messages.success(
                request,
                "Profile updated successfully.",
            )

        return redirect("profile")

    return render(
        request,
        "accounts/profile.html",
        {"form": form},
    )
'''

if old_profile_view in views:
    views = views.replace(
        old_profile_view,
        new_profile_view,
        1,
    )
elif "old_email =" not in views:
    raise RuntimeError(
        "Could not safely patch profile()."
    )
else:
    print("Profile email verification protection already present.")


old_delete = '''@login_required
def delete_address(request, address_id):

    address = get_object_or_404(Address, id=address_id, user=request.user)
    address.delete()

    return redirect("addresses")
'''

new_delete = '''@login_required
@require_POST
def delete_address(request, address_id):

    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user,
    )

    address.delete()

    return redirect("addresses")
'''

if old_delete in views:
    views = views.replace(
        old_delete,
        new_delete,
        1,
    )
elif (
    "@require_POST\ndef delete_address"
    not in views
):
    raise RuntimeError(
        "Could not safely patch delete_address()."
    )


old_default = '''@login_required
def set_default_address(request, address_id):

    address = get_object_or_404(Address, id=address_id, user=request.user)

    Address.objects.filter(user=request.user).update(is_default=False)

    address.is_default = True
    address.save()

    return redirect("addresses")
'''

new_default = '''@login_required
@require_POST
@transaction.atomic
def set_default_address(request, address_id):

    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user,
    )

    Address.objects.filter(
        user=request.user
    ).update(
        is_default=False
    )

    address.is_default = True
    address.save(
        update_fields=["is_default"]
    )

    return redirect("addresses")
'''

if old_default in views:
    views = views.replace(
        old_default,
        new_default,
        1,
    )
elif (
    "@require_POST\n@transaction.atomic\n"
    "def set_default_address"
    not in views
):
    raise RuntimeError(
        "Could not safely patch set_default_address()."
    )

VIEWS.write_text(views, encoding="utf-8")


# ============================================================
# 3. SECURITY REGRESSION TESTS
# ============================================================

TESTS.write_text(
r'''
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.forms import RegisterForm
from accounts.models import Address


User = get_user_model()


class Phase2AccountSecurityTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="phase2-user",
            email="verified@example.com",
            password="StrongPass123!",
            email_verified=True,
            is_active=True,
        )

        self.other = User.objects.create_user(
            username="phase2-other",
            email="other@example.com",
            password="StrongPass123!",
            email_verified=True,
            is_active=True,
        )

    def _address(self, user, **extra):
        data = {
            "user": user,
            "full_name": "Test Customer",
            "phone": "0712345678",
            "county": "Nairobi",
            "city": "Nairobi",
            "estate": "CBD",
            "house_number": "10",
            "landmark": "",
            "is_default": False,
        }

        data.update(extra)

        return Address.objects.create(**data)

    def test_registration_rejects_duplicate_email_case_insensitively(self):

        form = RegisterForm(
            data={
                "username": "new-user",
                "email": "VERIFIED@EXAMPLE.COM",
                "phone": "0711111111",
                "password1": "StrongPass987!",
                "password2": "StrongPass987!",
            }
        )

        self.assertFalse(form.is_valid())

        self.assertIn(
            "email",
            form.errors,
        )

    def test_changing_verified_email_removes_verified_status(self):

        self.client.force_login(self.user)

        response = self.client.post(
            reverse("profile"),
            data={
                "first_name": "Phase",
                "last_name": "Two",
                "email": "new-email@example.com",
                "phone": "0712345678",
                "email_notifications": "on",
                "sms_notifications": "on",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.user.refresh_from_db()

        self.assertEqual(
            self.user.email,
            "new-email@example.com",
        )

        self.assertFalse(
            self.user.email_verified
        )

    def test_profile_rejects_another_users_email(self):

        self.client.force_login(self.user)

        response = self.client.post(
            reverse("profile"),
            data={
                "first_name": "Phase",
                "last_name": "Two",
                "email": "OTHER@EXAMPLE.COM",
                "phone": "0712345678",
                "email_notifications": "on",
                "sms_notifications": "on",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.user.refresh_from_db()

        self.assertEqual(
            self.user.email,
            "verified@example.com",
        )

        self.assertTrue(
            self.user.email_verified
        )

    def test_address_delete_rejects_get(self):

        address = self._address(
            self.user
        )

        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "delete_address",
                args=[address.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

        self.assertTrue(
            Address.objects.filter(
                pk=address.pk
            ).exists()
        )

    def test_address_delete_post_works_for_owner(self):

        address = self._address(
            self.user
        )

        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "delete_address",
                args=[address.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertFalse(
            Address.objects.filter(
                pk=address.pk
            ).exists()
        )

    def test_user_cannot_delete_another_users_address(self):

        address = self._address(
            self.other
        )

        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "delete_address",
                args=[address.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertTrue(
            Address.objects.filter(
                pk=address.pk
            ).exists()
        )

    def test_default_address_rejects_get(self):

        address = self._address(
            self.user
        )

        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "set_default_address",
                args=[address.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

        address.refresh_from_db()

        self.assertFalse(
            address.is_default
        )

    def test_user_cannot_make_another_users_address_default(self):

        mine = self._address(
            self.user,
            is_default=True,
        )

        theirs = self._address(
            self.other,
            is_default=False,
        )

        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "set_default_address",
                args=[theirs.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        mine.refresh_from_db()
        theirs.refresh_from_db()

        self.assertTrue(
            mine.is_default
        )

        self.assertFalse(
            theirs.is_default
        )

    def test_setting_default_address_updates_only_owner(self):

        old_default = self._address(
            self.user,
            is_default=True,
        )

        new_default = self._address(
            self.user,
            is_default=False,
        )

        other_default = self._address(
            self.other,
            is_default=True,
        )

        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "set_default_address",
                args=[new_default.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        old_default.refresh_from_db()
        new_default.refresh_from_db()
        other_default.refresh_from_db()

        self.assertFalse(
            old_default.is_default
        )

        self.assertTrue(
            new_default.is_default
        )

        self.assertTrue(
            other_default.is_default
        )
'''.strip() + "\n",
encoding="utf-8",
)

print()
print("=" * 72)
print("PHASE 2A AUTHENTICATION SECURITY PATCH APPLIED")
print("=" * 72)
print("Added:")
print(" - duplicate-email registration protection")
print(" - duplicate-email profile protection")
print(" - verified-email invalidation after email change")
print(" - POST-only address deletion")
print(" - POST-only default-address mutation")
print(" - transactional default-address change")
print(" - ownership/security regression tests")
