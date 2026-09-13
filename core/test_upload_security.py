from io import BytesIO

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
