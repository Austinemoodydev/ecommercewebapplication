from io import BytesIO

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
