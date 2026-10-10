from django import template

from accounts.staff_access import (
    can_manage_staff,
    is_store_owner,
)


register = template.Library()


@register.filter
def store_owner(user):

    return is_store_owner(user)


@register.filter
def staff_administrator(user):
    return can_manage_staff(user)
