"""
Django settings loader based on environment.

Loads default settings first, then overlays environment-specific settings.
Set DJANGO_ENV environment variable to 'dev' or 'prod' (defaults to 'dev').
"""

import os

# Import all default settings
from .default import *

# Get environment from DJANGO_ENV (default to 'dev')
ENVIRONMENT = os.environ.get('DJANGO_ENV', 'dev').lower()

# Load environment-specific settings
if ENVIRONMENT == 'prod':
    try:
        from .prod import *
        print(f"Loaded production settings")
    except ImportError:
        pass
elif ENVIRONMENT == 'dev':
    try:
        from .dev import *
        print(f"Loaded development settings")
    except ImportError:
        pass
else:
    print(f"Warning: Unknown environment '{ENVIRONMENT}', using default settings only")
