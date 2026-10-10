from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import HomepageSlide


def slide(**overrides):
    values = {
        "internal_name": "Test banner",
        "heading": "Shop confidently",
        "image_alt": "Products on display",
        "desktop_static_path": "images/hero/fashion-desktop.webp",
        "mobile_static_path": "images/hero/fashion-mobile.webp",
        "destination_url": "/shop/",
    }
    values.update(overrides)
    return HomepageSlide.objects.create(**values)


class HomepageSlideTests(TestCase):
    def test_active_slide_is_rendered_with_responsive_image_and_real_link(self):
        slide()
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Shop confidently")
        self.assertContains(response, '<picture>')
        self.assertContains(response, 'href="/shop/"')
        self.assertContains(response, "Pause rotating promotions", count=0)

    def test_expired_and_future_slides_are_not_rendered(self):
        now = timezone.now()
        slide(internal_name="Expired", heading="Expired offer", ends_at=now - timedelta(minutes=1))
        slide(internal_name="Future", heading="Future offer", starts_at=now + timedelta(days=1))
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "Expired offer")
        self.assertNotContains(response, "Future offer")

    def test_multiple_slides_have_controls_and_pause_button(self):
        slide()
        slide(internal_name="Second", heading="Second promotion")
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Previous promotion")
        self.assertContains(response, "Pause rotating promotions")
