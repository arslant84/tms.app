from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        """
        Called when Django starts up.
        Register signal handlers and perform app initialization.
        """
        # Email settings are now loaded from .env file (no database loading needed)
        pass
