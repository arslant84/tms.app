from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        """
        Called when Django starts up.
        Load email settings from database into Django settings.
        """
        # Import here to avoid circular imports
        from tms_project.settings import load_email_settings
        load_email_settings()
