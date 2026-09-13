from .models import StoreSettings


def get_store_settings():

    """
    Return the singleton store settings record.
    """

    settings_obj, _created = (
        StoreSettings.objects.get_or_create(
            pk=StoreSettings.SINGLETON_PK
        )
    )

    return settings_obj


def business_address(
    settings_obj=None,
):

    settings_obj = (
        settings_obj
        or get_store_settings()
    )


    parts = [
        settings_obj.address,
        settings_obj.city,
        settings_obj.county,
        settings_obj.country,
    ]


    return ", ".join(
        str(part).strip()
        for part in parts
        if part
        and str(part).strip()
    )
