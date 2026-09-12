from django.apps import AppConfig


class OrdersConfig(AppConfig):
    name = 'orders'

    def ready(self):
        from . import signals  # noqa: F401
