from django.contrib.auth.decorators import user_passes_test


def customer_required(view_func):
    return user_passes_test(
        lambda u: u.is_authenticated and u.role == "customer"
    )(view_func)


def admin_required(view_func):
    return user_passes_test(
        lambda u: u.is_authenticated and u.role == "admin"
    )(view_func)