"""
Settings package initialization.
Automatically loads the appropriate settings module based on DJANGO_SETTINGS_MODULE environment variable.
"""

import os
from decouple import config

# Determine which settings to use
ENVIRONMENT = config('DJANGO_ENV', default='development')

if ENVIRONMENT == 'production':
    from .production import *
elif ENVIRONMENT == 'staging':
    from .production import *  # Staging uses production with minor tweaks
elif ENVIRONMENT == 'development':
    from .development import *
else:
    # Default to development
    from .development import *

print(f"[SETTINGS] Loaded {ENVIRONMENT} settings")
