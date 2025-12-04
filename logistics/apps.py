from django.apps import AppConfig


class LogisticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'logistics'

    def ready(self):
        # Import signals to register them
        from . import signals  # noqa

