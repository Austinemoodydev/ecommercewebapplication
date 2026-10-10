from django.core.management.base import BaseCommand

from core.models import HomepageSlide


SLIDES = [
    {
        "internal_name": "Everyday Fashion",
        "eyebrow": "Fresh arrivals",
        "heading": "Style for every moment",
        "description": "Discover confident everyday looks selected for comfort, quality, and value.",
        "button_label": "Shop fashion",
        "image_alt": "Contemporary clothing and fashion accessories arranged in a bright studio",
        "desktop_static_path": "images/hero/fashion-desktop.webp",
        "mobile_static_path": "images/hero/fashion-mobile.webp",
        "destination_url": "/shop/",
        "display_order": 10,
    },
    {
        "internal_name": "Beauty Essentials",
        "eyebrow": "Care that shows",
        "heading": "Your daily glow starts here",
        "description": "Shop trusted skincare, grooming, and personal-care essentials in one place.",
        "button_label": "Shop beauty",
        "image_alt": "Premium skincare and personal-care products on a warm neutral background",
        "desktop_static_path": "images/hero/beauty-desktop.webp",
        "mobile_static_path": "images/hero/beauty-mobile.webp",
        "destination_url": "/shop/",
        "display_order": 20,
    },
    {
        "internal_name": "Smart Technology",
        "eyebrow": "Upgrade your day",
        "heading": "Technology that works for you",
        "description": "Explore dependable electronics for work, entertainment, and life on the move.",
        "button_label": "Shop electronics",
        "image_alt": "Laptop, headphones, smartphone, and smart watch on a clean blue background",
        "desktop_static_path": "images/hero/electronics-desktop.webp",
        "mobile_static_path": "images/hero/electronics-mobile.webp",
        "destination_url": "/shop/",
        "display_order": 30,
    },
]


class Command(BaseCommand):
    help = "Create or refresh the professional default homepage banners."

    def handle(self, *args, **options):
        for values in SLIDES:
            name = values["internal_name"]
            HomepageSlide.objects.update_or_create(internal_name=name, defaults=values)
        self.stdout.write(self.style.SUCCESS(f"Homepage banners ready: {len(SLIDES)}"))
