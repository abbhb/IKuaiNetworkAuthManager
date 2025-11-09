"""
DEPRECATED: This file is deprecated.
Settings have been moved to config/settings/ directory.

Please use the new settings structure:
- config/settings/default.py - Default settings (always loaded)
- config/settings/dev.py - Development environment settings
- config/settings/prod.py - Production environment settings

Set DJANGO_ENV environment variable to 'dev' or 'prod' to load the appropriate settings.
"""

# Import all settings from the new structure
from config.settings import *

