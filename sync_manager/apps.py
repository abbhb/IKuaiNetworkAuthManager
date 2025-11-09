"""
Sync Manager application configuration.
"""

from django.apps import AppConfig


class SyncManagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sync_manager'
    verbose_name = '应用管理'
