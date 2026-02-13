"""
Lazy email settings loader.
Loads email settings from database only when first needed, not at app startup.
This avoids database access during app initialization.
"""
from django.conf import settings as django_settings
from threading import Lock
import sys


class EmailSettingsLoader:
    """
    Singleton class to lazily load email settings from database.
    Settings are loaded only once, on first access, and cached.
    """
    _instance = None
    _lock = Lock()
    _loaded = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def load_settings(self, force_reload=False):
        """
        Load email settings from database into Django settings.
        Uses caching to avoid multiple database queries.

        Args:
            force_reload: If True, reload settings even if already loaded
        """
        if self._loaded and not force_reload:
            return  # Already loaded, skip

        with self._lock:
            if self._loaded and not force_reload:
                return  # Double-check after acquiring lock

            try:
                # Import here to avoid circular imports and ensure models are ready
                from accounts.models import ApplicationSetting

                # Settings mapping
                settings_map = {
                    'smtp_host': 'EMAIL_HOST',
                    'smtp_port': 'EMAIL_PORT',
                    'smtp_use_tls': 'EMAIL_USE_TLS',
                    'smtp_use_ssl': 'EMAIL_USE_SSL',
                    'smtp_username': 'EMAIL_HOST_USER',
                    'smtp_password': 'EMAIL_HOST_PASSWORD',
                    'from_email': 'DEFAULT_FROM_EMAIL',  # Also try 'from_email' key
                    'default_from_email': 'DEFAULT_FROM_EMAIL',
                    'server_email': 'SERVER_EMAIL',
                }

                loaded_values = {}
                settings_loaded = False

                for db_key, setting_key in settings_map.items():
                    value = ApplicationSetting.get_setting(db_key)
                    if value is not None:
                        # Update Django settings
                        setattr(django_settings, setting_key, value)
                        loaded_values[setting_key] = value
                        settings_loaded = True

                if settings_loaded:
                    print(f"[OK] Loaded {len(loaded_values)} email settings from database", file=sys.stderr)
                    print(f"   SMTP Host: {loaded_values.get('EMAIL_HOST', 'N/A')}", file=sys.stderr)
                    print(f"   SMTP User: {loaded_values.get('EMAIL_HOST_USER', 'N/A')}", file=sys.stderr)
                    self._loaded = True
                else:
                    print("[INFO] No email settings found in database, using defaults from settings.py", file=sys.stderr)

            except Exception as e:
                # Fail gracefully - use default settings from settings.py
                print(f"[WARNING] Could not load email settings from database: {e}", file=sys.stderr)
                print("[INFO] Using default email settings from settings.py", file=sys.stderr)


# Global singleton instance
_email_settings_loader = EmailSettingsLoader()


def ensure_email_settings_loaded():
    """
    Ensure email settings are loaded from database.
    Call this before sending emails to guarantee settings are loaded.
    This is safe to call multiple times - settings are loaded only once.
    """
    _email_settings_loader.load_settings()


def reload_email_settings():
    """
    Force reload email settings from database.
    Useful when settings are updated in the admin panel.
    """
    _email_settings_loader.load_settings(force_reload=True)
