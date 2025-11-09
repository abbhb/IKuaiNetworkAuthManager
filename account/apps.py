"""
Account application configuration.
Handles startup initialization including full LDAP sync.
"""

from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class AccountConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'account'
    verbose_name = '用户认证与同步'

    def ready(self):
        """
        应用启动时执行的初始化任务
        """
        # 导入 signals（如果有的话）
        # from . import signals
        
        # 启动时执行一次全量同步
        from django.conf import settings
        import os
        
        # 只在主进程中执行同步，避免在 runserver 的 reloader 进程中重复执行
        if os.environ.get('RUN_MAIN') != 'true' and settings.DEBUG:
            return
            
        # 检查是否启用了 LDAP
        if settings.LDAP_BACKEND in settings.AUTHENTICATION_BACKENDS:
            logger.info("应用启动：开始全量同步 LDAP 用户和组织架构...")
            try:
                from .tasks import sync_all_ldap_users_and_groups
                # 在启动时同步一次（同步执行）
                sync_all_ldap_users_and_groups()
                logger.info("LDAP 全量同步完成")
            except Exception as e:
                logger.error(f"LDAP 全量同步失败: {e}", exc_info=True)
        else:
            logger.info("LDAP 未启用，跳过同步")
