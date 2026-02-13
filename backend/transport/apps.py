from django.apps import AppConfig


class TransportConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'transport'
    verbose_name = 'Transport Management'

    def ready(self):
        """Import signal handlers when app is ready."""
        import transport.signals  # noqa
