from django.apps import AppConfig


class TrfConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'trf'

    def ready(self):
        """Import signal handlers when app is ready."""
        import trf.signals  # noqa
