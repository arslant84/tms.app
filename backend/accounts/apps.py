from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        """
        Called when Django starts up.
        Register signal handlers and perform app initialization.
        """
        # Import signals to register handlers for audit logging
        import accounts.signals  # noqa: F401
        # Email settings are now loaded from .env file (no database loading needed)
