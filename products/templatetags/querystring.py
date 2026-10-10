from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def query_transform(context, **kwargs):
    """
    Keeps existing query parameters while updating/removing selected ones.
    """

    query = context["request"].GET.copy()

    for key, value in kwargs.items():

        if value is None or value == "":
            query.pop(key, None)

        else:
            query[key] = value

    return query.urlencode()


@register.simple_tag(takes_context=True)
def remove_query_value(context, key, value):
    """Remove one value from a repeated query-string parameter."""
    query = context["request"].GET.copy()
    remaining = [item for item in query.getlist(key) if item != str(value)]
    query.pop(key, None)
    for item in remaining:
        query.appendlist(key, item)
    query.pop("page", None)
    return query.urlencode()
