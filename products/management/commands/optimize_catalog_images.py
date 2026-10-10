from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from PIL import Image

from products.models import Product


class Command(BaseCommand):
    help = "Convert oversized PNG catalogue images to lightweight WebP files."

    def add_arguments(self, parser):
        parser.add_argument("--delete-originals", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT).resolve()
        converted = 0
        total_before = 0
        total_after = 0

        for product in Product.objects.exclude(image=""):
            source = Path(product.image.path)
            if source.suffix.lower() != ".png" or not source.is_file():
                continue
            if media_root not in source.resolve().parents:
                self.stderr.write(f"Skipped unsafe path: {source}")
                continue

            destination = source.with_suffix(".webp")
            with Image.open(source) as image:
                image = image.convert("RGB")
                image.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
                image.save(destination, "WEBP", quality=84, method=6)

            total_before += source.stat().st_size
            total_after += destination.stat().st_size
            product.image.name = str(destination.relative_to(media_root)).replace("\\", "/")
            product.save(update_fields=["image", "updated_at"])
            converted += 1

            if options["delete_originals"]:
                source.unlink()

        saved_mb = (total_before - total_after) / (1024 * 1024)
        self.stdout.write(self.style.SUCCESS(
            f"Optimized {converted} product images; reduced transfer size by {saved_mb:.1f} MB."
        ))
