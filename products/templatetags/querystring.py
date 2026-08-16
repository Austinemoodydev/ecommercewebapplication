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