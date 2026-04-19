from django.apps import AppConfig


class CombinedRequestConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'combined_request'
    verbose_name = 'Combined Request'

    def ready(self):
        """Import signal handlers when app is ready."""
        pass  # Will add signals later if needed
