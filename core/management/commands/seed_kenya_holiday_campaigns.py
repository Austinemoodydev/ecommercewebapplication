from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import MarketingCampaign


OFFICIAL_SOURCE = "https://new.kenyalaw.org/akn/ke/act/1912/21/eng@2024-04-26"
FIXED_HOLIDAYS = [
    (1, 1, "New Year's Day", "new_year"),
    (5, 1, "Labour Day", "public_holiday"),
    (6, 1, "Madaraka Day", "public_holiday"),
    (10, 10, "Mazingira Day", "public_holiday"),
    (10, 20, "Mashujaa Day", "public_holiday"),
    (12, 12, "Jamhuri Day", "public_holiday"),
    (12, 25, "Christmas Day", "christmas"),
    (12, 26, "Boxing Day", "festive"),
]


class Command(BaseCommand):
    help = "Create editable draft campaigns for Kenya's recurring fixed-date holidays."

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, default=timezone.localdate().year)
        parser.add_argument("--years", type=int, default=2)

    def handle(self, *args, **options):
        created = 0
        for year in range(options["year"], options["year"] + options["years"]):
            for month, day, name, holiday_type in FIXED_HOLIDAYS:
                holiday_date = datetime(year, month, day)
                starts_at = timezone.make_aware(datetime.combine(holiday_date.date(), time.min))
                ends_at = starts_at + timedelta(days=1)
                _, was_created = MarketingCampaign.objects.get_or_create(
                    name=f"{name} {year}",
                    starts_at=starts_at,
                    defaults={
                        "holiday_type": holiday_type,
                        "headline": f"Happy {name}",
                        "message": f"We wish you a happy {name}. Online shopping remains available.",
                        "chatbot_message": f"Today is {name}. Share the store's approved holiday message and any configured delivery notice.",
                        "ends_at": ends_at,
                        "is_enabled": True,
                        "is_verified_holiday": True,
                        "official_source_url": OFFICIAL_SOURCE,
                        "show_on_website": True,
                    },
                )
                created += int(was_created)
        self.stdout.write(self.style.SUCCESS(f"Created {created} holiday campaign drafts."))
        self.stdout.write("Review dates, add operational notices, and approve each campaign before publication.")
