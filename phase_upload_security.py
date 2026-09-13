from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys


ROOT = Path.cwd()

if not (ROOT / "manage.py").exists():
    raise SystemExit(
        "ERROR: Run this from the Django project root."
    )


# ============================================================
# BACKUPS
# ============================================================

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

backup_dir = (
    ROOT
    / ".upload_security_backups"
    / stamp
)

backup_dir.mkdir(
    parents=True,
    exist_ok=True,
)


def backup(path):

    if not path.exists():
        return

    destination = (
        backup_dir
        / path.relative_to(ROOT)
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        path,
        destination,
    )


files_to_backup = [
    ROOT / "accounts" / "forms.py",
    ROOT / "dashboard" / "forms.py",
    ROOT / "dashboard" / "catalog_forms.py",
    ROOT / "core" / "upload_security.py",
    ROOT / "core" / "test_upload_security.py",
]


for file_path in files_to_backup:
    backup(file_path)


# ============================================================
# 1. CENTRAL IMAGE VALIDATOR
# ============================================================

validator_file = (
    ROOT
    / "core"
    / "upload_security.py"
)


validator_file.write_text(
r'''from io import BytesIO

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


ALLOWED_IMAGE_FORMATS = {
    "JPEG",
    "PNG",
    "WEBP",
}

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


def validate_uploaded_image(
    upload,
    *,
    max_size_mb=5,
    max_width=6000,
    max_height=6000,
    max_pixels=25_000_000,
):
    """
    Validate a newly uploaded image.

    Security checks:
    - maximum byte size
    - allowed MIME type
    - actual Pillow-detected image format
    - corruption/truncation
    - maximum width/height
    - maximum total pixel count

    Existing FieldFile objects are left alone because this
    function is intended for new browser uploads.
    """

    if not upload:
        return upload

    # Existing model FieldFile rather than new UploadedFile.
    if not hasattr(
        upload,
        "content_type",
    ):
        return upload


    max_bytes = (
        max_size_mb
        * 1024
        * 1024
    )


    if upload.size > max_bytes:

        raise ValidationError(
            (
                f"Image must not be larger than "
                f"{max_size_mb} MB."
            )
        )


    content_type = (
        getattr(
            upload,
            "content_type",
            "",
        )
        or ""
    ).lower()


    if (
        content_type
        not in ALLOWED_CONTENT_TYPES
    ):

        raise ValidationError(
            (
                "Unsupported image type. "
                "Use JPEG, PNG, or WebP."
            )
        )


    try:

        upload.seek(0)

        raw = upload.read()

        image = Image.open(
            BytesIO(raw)
        )

        detected_format = (
            image.format or ""
        ).upper()

        width, height = image.size


        if (
            detected_format
            not in ALLOWED_IMAGE_FORMATS
        ):

            raise ValidationError(
                (
                    "Unsupported image format. "
                    "Use JPEG, PNG, or WebP."
                )
            )


        if (
            width <= 0
            or height <= 0
        ):

            raise ValidationError(
                "Image dimensions are invalid."
            )


        if (
            width > max_width
            or height > max_height
        ):

            raise ValidationError(
                (
                    "Image dimensions are too large. "
                    f"Maximum dimensions are "
                    f"{max_width} × {max_height} pixels."
                )
            )


        if (
            width * height
            > max_pixels
        ):

            raise ValidationError(
                (
                    "Image contains too many pixels. "
                    "Please resize it before uploading."
                )
            )


        # Pillow verify() checks that the underlying image
        # structure is internally consistent.
        image.verify()


    except ValidationError:
        raise

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        SyntaxError,
    ):

        raise ValidationError(
            (
                "The uploaded file is not a valid "
                "or readable image."
            )
        )

    finally:

        try:
            upload.seek(0)
        except Exception:
            pass


    return upload
''',
    encoding="utf-8",
)

print(
    "[CREATED] core/upload_security.py"
)


# ============================================================
# 2. CUSTOMER AVATAR
# ============================================================

accounts_forms = (
    ROOT
    / "accounts"
    / "forms.py"
)

text = accounts_forms.read_text(
    encoding="utf-8-sig"
)


import_line = (
    "from core.upload_security "
    "import validate_uploaded_image"
)


if import_line not in text:

    # Put import after existing import section.
    lines = text.splitlines()

    insert_at = 0

    for i, line in enumerate(lines):

        if (
            line.startswith("from ")
            or line.startswith("import ")
        ):
            insert_at = i + 1

    lines.insert(
        insert_at,
        import_line,
    )

    text = "\n".join(lines) + "\n"


avatar_method = '''
    def clean_avatar(self):

        avatar = self.cleaned_data.get(
            "avatar"
        )

        if avatar:

            validate_uploaded_image(
                avatar,
                max_size_mb=2,
                max_width=3000,
                max_height=3000,
                max_pixels=9_000_000,
            )

        return avatar
'''


if "def clean_avatar(self):" not in text:

    marker = '''
    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
'''

    # We need the ProfileForm clean_email, not RegisterForm.
    profile_marker = "class ProfileForm(forms.ModelForm):"

    if profile_marker not in text:

        raise SystemExit(
            "ERROR: ProfileForm not found."
        )

    before, profile = text.split(
        profile_marker,
        1,
    )

    if marker not in profile:

        raise SystemExit(
            "ERROR: ProfileForm clean_email not found."
        )

    profile = profile.replace(
        marker,
        avatar_method
        + "\n"
        + marker,
        1,
    )

    text = (
        before
        + profile_marker
        + profile
    )


accounts_forms.write_text(
    text,
    encoding="utf-8",
)

print(
    "[PATCHED] Avatar security"
)


# ============================================================
# 3. PRODUCT PRIMARY + PRODUCT GALLERY
# ============================================================

dashboard_forms = (
    ROOT
    / "dashboard"
    / "forms.py"
)

text = dashboard_forms.read_text(
    encoding="utf-8-sig"
)


import_line = (
    "from core.upload_security "
    "import validate_uploaded_image"
)


if import_line not in text:

    marker = (
        "from orders.models import Order"
    )

    if marker not in text:

        raise SystemExit(
            "ERROR: dashboard/forms.py import marker not found."
        )

    text = text.replace(
        marker,
        marker
        + "\n"
        + import_line,
        1,
    )


product_clean = '''
    def clean_image(self):

        image = self.cleaned_data.get(
            "image"
        )

        if image:

            validate_uploaded_image(
                image,
                max_size_mb=5,
                max_width=6000,
                max_height=6000,
                max_pixels=25_000_000,
            )

        return image

'''


if "def clean_image(self):" not in text:

    marker = '''
    def clean_sku(self):

        sku = self.cleaned_data["sku"].strip().upper()
'''

    if marker not in text:

        raise SystemExit(
            "ERROR: AdminProductForm clean_sku marker not found."
        )

    text = text.replace(
        marker,
        product_clean
        + marker,
        1,
    )


# Strengthen existing gallery validation.

old_gallery = '''        max_size = 5 * 1024 * 1024

        for image in images:

            if image.size > max_size:
                raise ValidationError(
                    (
                        f"{image.name} is larger than "
                        "5 MB."
                    )
                )

        return images
'''


new_gallery = '''        for image in images:

            validate_uploaded_image(
                image,
                max_size_mb=5,
                max_width=6000,
                max_height=6000,
                max_pixels=25_000_000,
            )

        return images
'''


if old_gallery in text:

    text = text.replace(
        old_gallery,
        new_gallery,
        1,
    )

elif (
    "validate_uploaded_image("
    not in text.split(
        "class AdminProductGalleryForm",
        1,
    )[1]
):

    raise SystemExit(
        "ERROR: Could not safely patch gallery validation."
    )


dashboard_forms.write_text(
    text,
    encoding="utf-8",
)

print(
    "[PATCHED] Product and gallery security"
)


# ============================================================
# 4. CATEGORY + BRAND UPLOAD SECURITY
# ============================================================

catalog_forms = (
    ROOT
    / "dashboard"
    / "catalog_forms.py"
)

text = catalog_forms.read_text(
    encoding="utf-8-sig"
)


import_line = (
    "from core.upload_security "
    "import validate_uploaded_image"
)


if import_line not in text:

    marker = (
        "from products.models import Brand"
    )

    if marker not in text:

        raise SystemExit(
            "ERROR: catalog_forms import marker not found."
        )

    text = text.replace(
        marker,
        marker
        + "\n"
        + import_line,
        1,
    )


category_method = '''
    def clean_image(self):

        image = self.cleaned_data.get(
            "image"
        )

        if image:

            validate_uploaded_image(
                image,
                max_size_mb=3,
                max_width=4000,
                max_height=4000,
                max_pixels=16_000_000,
            )

        return image

'''


brand_method = '''
    def clean_logo(self):

        logo = self.cleaned_data.get(
            "logo"
        )

        if logo:

            validate_uploaded_image(
                logo,
                max_size_mb=3,
                max_width=4000,
                max_height=4000,
                max_pixels=16_000_000,
            )

        return logo

'''


if "def clean_image(self):" not in text:

    marker = '''
    def clean_name(self):

        name = (
            self.cleaned_data["name"]
'''

    if marker not in text:

        raise SystemExit(
            "ERROR: Category clean_name marker not found."
        )

    text = text.replace(
        marker,
        category_method
        + marker,
        1,
    )


brand_marker = "class AdminBrandForm(forms.ModelForm):"

if brand_marker not in text:

    raise SystemExit(
        "ERROR: AdminBrandForm not found."
    )


before_brand, brand_section = text.split(
    brand_marker,
    1,
)


if "def clean_logo(self):" not in brand_section:

    marker = '''
    def clean_name(self):

        name = (
            self.cleaned_data["name"]
'''

    if marker not in brand_section:

        raise SystemExit(
            "ERROR: Brand clean_name marker not found."
        )

    brand_section = brand_section.replace(
        marker,
        brand_method
        + marker,
        1,
    )


text = (
    before_brand
    + brand_marker
    + brand_section
)


catalog_forms.write_text(
    text,
    encoding="utf-8",
)

print(
    "[PATCHED] Category and brand security"
)


# ============================================================
# 5. SECURITY TESTS
# ============================================================

test_file = (
    ROOT
    / "core"
    / "test_upload_security.py"
)


test_file.write_text(
r'''from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image

from core.upload_security import (
    validate_uploaded_image,
)


def make_image(
    *,
    name="test.png",
    width=100,
    height=100,
    format_name="PNG",
    content_type="image/png",
):

    stream = BytesIO()

    image = Image.new(
        "RGB",
        (width, height),
        "white",
    )

    image.save(
        stream,
        format=format_name,
    )

    return SimpleUploadedFile(
        name,
        stream.getvalue(),
        content_type=content_type,
    )


class UploadSecurityTests(SimpleTestCase):

    def test_valid_png_is_accepted(self):

        upload = make_image()

        result = validate_uploaded_image(
            upload,
        )

        self.assertIs(
            result,
            upload,
        )


    def test_valid_jpeg_is_accepted(self):

        upload = make_image(
            name="photo.jpg",
            format_name="JPEG",
            content_type="image/jpeg",
        )

        validate_uploaded_image(
            upload
        )


    def test_fake_image_is_rejected(self):

        upload = SimpleUploadedFile(
            "fake.jpg",
            b"This is not an image.",
            content_type="image/jpeg",
        )

        with self.assertRaises(
            ValidationError
        ):

            validate_uploaded_image(
                upload
            )


    def test_disallowed_mime_type_is_rejected(self):

        upload = make_image(
            name="image.png",
            content_type="application/octet-stream",
        )

        with self.assertRaises(
            ValidationError
        ):

            validate_uploaded_image(
                upload
            )


    def test_gif_is_rejected(self):

        upload = make_image(
            name="animated.gif",
            format_name="GIF",
            content_type="image/gif",
        )

        with self.assertRaises(
            ValidationError
        ):

            validate_uploaded_image(
                upload
            )


    def test_oversized_file_is_rejected(self):

        upload = make_image()

        # Simulate uploaded size beyond policy without
        # allocating many megabytes in the test suite.
        upload.size = (
            6 * 1024 * 1024
        )

        with self.assertRaises(
            ValidationError
        ):

            validate_uploaded_image(
                upload,
                max_size_mb=5,
            )


    def test_excessive_width_is_rejected(self):

        upload = make_image(
            width=6001,
            height=1,
        )

        with self.assertRaises(
            ValidationError
        ):

            validate_uploaded_image(
                upload,
                max_width=6000,
                max_height=6000,
            )


    def test_excessive_height_is_rejected(self):

        upload = make_image(
            width=1,
            height=6001,
        )

        with self.assertRaises(
            ValidationError
        ):

            validate_uploaded_image(
                upload,
                max_width=6000,
                max_height=6000,
            )


    def test_pixel_bomb_style_image_is_rejected(self):

        upload = make_image(
            width=5000,
            height=5000,
        )

        with self.assertRaises(
            ValidationError
        ):

            validate_uploaded_image(
                upload,
                max_width=6000,
                max_height=6000,
                max_pixels=20_000_000,
            )


    def test_upload_pointer_is_reset_after_validation(self):

        upload = make_image()

        validate_uploaded_image(
            upload
        )

        self.assertEqual(
            upload.tell(),
            0,
        )
''',
    encoding="utf-8",
)

print(
    "[CREATED] core/test_upload_security.py"
)


# ============================================================
# 6. IGNORE LOCAL PATCH BACKUPS
# ============================================================

gitignore = ROOT / ".gitignore"

if gitignore.exists():

    text = gitignore.read_text(
        encoding="utf-8-sig"
    )

    entry = ".upload_security_backups/"

    if entry not in text:

        if not text.endswith("\n"):
            text += "\n"

        text += (
            "\n# Upload security patch backups\n"
            + entry
            + "\n"
        )

        gitignore.write_text(
            text,
            encoding="utf-8",
        )


# ============================================================
# 7. VALIDATION
# ============================================================

commands = [

    [
        sys.executable,
        "manage.py",
        "check",
    ],

    [
        sys.executable,
        "manage.py",
        "makemigrations",
        "--check",
        "--dry-run",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        "core.test_upload_security",
        "-v",
        "2",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        "accounts",
        "dashboard",
        "categories",
        "products",
        "-v",
        "1",
    ],
]


for command in commands:

    print()
    print("=" * 72)
    print(
        ">",
        " ".join(command)
    )
    print("=" * 72)

    result = subprocess.run(
        command,
        cwd=ROOT,
    )

    if result.returncode != 0:

        print()
        print("=" * 72)
        print(
            "UPLOAD SECURITY VALIDATION FAILED"
        )
        print("=" * 72)

        print()
        print(
            "Do not weaken the upload policy."
        )

        print(
            "Send the exact failing output."
        )

        print()
        print(
            "Backup directory:"
        )

        print(
            backup_dir
        )

        raise SystemExit(
            result.returncode
        )


print()
print("=" * 72)
print(
    "UPLOAD SECURITY TARGETED TESTS PASSED"
)
print("=" * 72)

print()
print(
    "Protected upload surfaces:"
)

print(
    "  - Customer avatar"
)

print(
    "  - Product primary image"
)

print(
    "  - Product gallery"
)

print(
    "  - Category image"
)

print(
    "  - Brand logo"
)

print()
print(
    "Allowed formats:"
)

print(
    "  JPEG / PNG / WebP"
)

print()
print(
    "Security checks:"
)

print(
    "  - file size"
)

print(
    "  - declared MIME type"
)

print(
    "  - actual image format"
)

print(
    "  - corrupt/fake image rejection"
)

print(
    "  - width and height limits"
)

print(
    "  - total pixel limit"
)

print()
print(
    "Backup directory:"
)

print(
    backup_dir
)

print()
print(
    "FINAL PROJECT GATE:"
)

print(
    "python manage.py test -v 1"
)

