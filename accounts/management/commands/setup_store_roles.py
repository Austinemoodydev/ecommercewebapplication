from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from accounts.store_roles import (
    ROLE_PERMISSION_MAP,
)


class Command(BaseCommand):

    help = (
        "Create or update store staff "
        "groups and model permissions."
    )


    def handle(
        self,
        *args,
        **options,
    ):

        for group_name, permission_specs in (
            ROLE_PERMISSION_MAP.items()
        ):

            group, created = (
                Group.objects.get_or_create(
                    name=group_name
                )
            )

            permissions = []

            for (
                app_label,
                codename,
            ) in permission_specs:

                permission = (
                    Permission.objects
                    .filter(
                        content_type__app_label=app_label,
                        codename=codename,
                    )
                    .first()
                )

                if permission is None:

                    self.stdout.write(
                        self.style.WARNING(
                            (
                                f"Permission not found: "
                                f"{app_label}.{codename}"
                            )
                        )
                    )

                    continue

                permissions.append(
                    permission
                )


            group.permissions.set(
                permissions
            )

            status = (
                "created"
                if created
                else "updated"
            )

            self.stdout.write(
                self.style.SUCCESS(
                    (
                        f"{group_name}: "
                        f"{status} "
                        f"({len(permissions)} permissions)"
                    )
                )
            )


        self.stdout.write(
            self.style.SUCCESS(
                "Store roles are ready."
            )
        )
