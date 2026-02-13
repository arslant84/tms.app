from django.apps import AppConfig


class AccommodationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accommodation'
    verbose_name = 'Accommodation Management'

    def ready(self):
        """Import signal handlers when app is ready."""
        import accommodation.signals  # noqa
