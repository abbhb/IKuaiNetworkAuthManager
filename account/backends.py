"""
Custom LDAP authentication backend.
仅使用 LDAP 进行密码验证，不同步用户信息。
用户信息由项目启动时的全量同步任务维护。
"""

import logging
from django.contrib.auth.models import User
from django_auth_ldap.backend import LDAPBackend as BaseLDAPBackend

logger = logging.getLogger(__name__)


class CustomLDAPBackend(BaseLDAPBackend):
    """
    自定义 LDAP 认证后端
    
    功能：
    1. 使用 LDAP 验证用户密码
    2. 验证成功后从本地数据库获取用户
    3. 如果本地数据库不存在该用户，返回 None（认证失败）
    
    注意：用户信息由全量同步任务维护，此后端不负责用户创建和更新
    """
    
    def authenticate_ldap_user(self, ldap_user, password):
        """
        LDAP 认证用户
        
        Args:
            ldap_user: LDAP 用户对象
            password: 用户输入的密码
            
        Returns:
            Django User 对象，认证失败或用户不存在返回 None
        """
        # 获取用户名
        username = ldap_user._username
        
        # 先检查本地数据库是否存在该用户
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            logger.warning(f"用户 {username} 在 LDAP 中存在，但本地数据库中不存在")
            return None
        
        # 调用父类方法进行 LDAP 密码验证
        # 注意：父类的 authenticate_ldap_user 会尝试创建用户，我们需要覆盖这个行为
        # 所以我们直接验证密码而不是调用父类方法
        try:
            # 使用 LDAP 用户对象的 bind 方法验证密码
            if ldap_user.authenticate(password):
                logger.info(f"用户 {username} LDAP 密码验证成功")
                user.password = password  # 更新本地密码缓存,便于用户修改密码后vpn这边密码一致
                user.save()
                return user
            else:
                logger.warning(f"用户 {username} LDAP 密码验证失败")
                return None
        except Exception as e:
            logger.error(f"LDAP 密码验证过程出错: {e}", exc_info=True)
            return None
    
    def get_or_build_user(self, username, ldap_user):
        """
        仅获取本地用户，不创建新用户
        
        Args:
            username: 用户名
            ldap_user: LDAP 用户对象
            
        Returns:
            (User对象, False) 如果用户存在
            (None, False) 如果用户不存在
        """
        try:
            user = User.objects.get(username=username)
            return user, False
        except User.DoesNotExist:
            logger.warning(f"用户 {username} 在本地数据库中不存在，拒绝登录")
            return None, False
