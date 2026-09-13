from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import user_passes_test


def staff_member_required(
    view_func=None,
    redirect_field_name=REDIRECT_FIELD_NAME,
    login_url="staff_login",
):

    """
    Protect store-management pages and redirect
    unauthenticated users to /staff/login/.
    """

    decorator = user_passes_test(
        lambda user: (
            user.is_active
            and user.is_staff
        ),
        login_url=login_url,
        redirect_field_name=redirect_field_name,
    )

    if view_func is not None:
        return decorator(view_func)

    return decorator
