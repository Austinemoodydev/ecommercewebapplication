from django import template

from accounts.staff_access import (
    is_store_owner,
)


register = template.Library()


@register.filter
def store_owner(user):

    return is_store_owner(user)
