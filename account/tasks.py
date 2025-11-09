"""
Celery tasks for LDAP user and organization synchronization.
定时任务：后台定期同步 LDAP 用户和组织架构信息。
"""

import logging
from celery import shared_task
from django.contrib.auth.models import User
from django.conf import settings
from account.models import Department

logger = logging.getLogger(__name__)


def sync_all_ldap_users_and_groups():
    """
    全量同步 LDAP 用户和部门信息
    
    这个函数可以被 Celery 任务调用，也可以在应用启动时直接调用。
    
    功能：
    1. 先从 LDAP 同步部门信息（OU）
    2. 再同步用户信息到本地数据库（创建或更新）
    3. 所有用户密码设置为 unusable
    
    注意：不操作 Django 的 Group，保留给后续的角色权限功能使用
    """
    if settings.LDAP_BACKEND not in settings.AUTHENTICATION_BACKENDS:
        logger.warning("LDAP 未启用，跳过同步")
        return {
            'status': 'skipped',
            'message': 'LDAP not enabled'
        }
    
    try:
        import ldap
        from django_auth_ldap.config import LDAPSearch
        
        logger.info("开始全量同步 LDAP 部门和用户...")
        
        # 统计信息
        stats = {
            'departments_created': 0,
            'departments_updated': 0,
            'users_created': 0,
            'users_updated': 0,
            'users_deactivated': 0,
            'errors': []
        }
        
        # 连接 LDAP
        ldap_conn = _get_ldap_connection()
        if not ldap_conn:
            raise Exception("无法连接到 LDAP 服务器")
        
        try:
            # 先同步部门信息
            _sync_departments(ldap_conn, stats)
            
            # 再同步用户信息
            _sync_users(ldap_conn, stats)
            
            logger.info(f"LDAP 全量同步完成: {stats}")
            
            return {
                'status': 'success',
                'stats': stats
            }
            
        finally:
            ldap_conn.unbind_s()
            
    except Exception as e:
        error_msg = f"LDAP 全量同步失败: {e}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'message': error_msg
        }


@shared_task
def sync_ldap_users_task():
    """
    Celery 定时任务：同步 LDAP 用户
    """
    logger.info("Celery 任务：开始同步 LDAP 用户...")
    result = sync_all_ldap_users_and_groups()
    logger.info(f"Celery 任务：同步完成，结果: {result}")
    return result


def _get_ldap_connection():
    """
    建立 LDAP 连接
    
    Returns:
        LDAP 连接对象，失败返回 None
    """
    try:
        import ldap
        
        # 从配置获取 LDAP 设置
        ldap_uri = settings.AUTH_LDAP_SERVER_URI
        bind_dn = settings.AUTH_LDAP_BIND_DN
        bind_password = settings.AUTH_LDAP_BIND_PASSWORD
        
        logger.debug(f"连接到 LDAP 服务器: {ldap_uri}")
        
        # 建立连接
        conn = ldap.initialize(ldap_uri)
        conn.protocol_version = ldap.VERSION3
        conn.set_option(ldap.OPT_REFERRALS, 0)
        
        # 绑定
        if bind_dn and bind_password:
            conn.simple_bind_s(bind_dn, bind_password)
            logger.debug("LDAP 绑定成功")
        else:
            logger.warning("未配置 LDAP 绑定凭据，使用匿名绑定")
            
        return conn
        
    except Exception as e:
        logger.error(f"连接 LDAP 失败: {e}", exc_info=True)
        return None


def _sync_groups(ldap_conn, stats):
    """
    同步 LDAP 部门信息到 Department 表
    
    注意：此函数已废弃，由 _sync_departments 替代
    
    Args:
        ldap_conn: LDAP 连接对象
        stats: 统计信息字典
    """
    pass  # 不再使用 Django 的 Group，保留给角色权限功能


def _sync_departments(ldap_conn, stats):
    """
    同步 LDAP 部门信息到 Department 表
    
    从 LDAP 的 OU（Organizational Unit）中提取部门信息：
    - cn: 部门ID（外部系统的部门编号）
    - ou: 部门名称
    
    Args:
        ldap_conn: LDAP 连接对象
        stats: 统计信息字典
    """
    try:
        import ldap
        
        # 从配置获取部门搜索基准（通常是组织架构的根节点）
        # 假设部门信息存储在 groupOfNames 对象中
        dept_search_base = settings.LDAP_GROUP_SEARCH_BASE
        dept_filter = "(objectClass=groupOfNames)"
        
        logger.info(f"搜索 LDAP 部门: base={dept_search_base}, filter={dept_filter}")
        
        # 搜索所有部门
        results = ldap_conn.search_s(
            dept_search_base,
            ldap.SCOPE_SUBTREE,
            dept_filter,
            ['ou', 'cn', 'description']
        )
        
        logger.info(f"找到 {len(results)} 个 LDAP 部门")
        
        for dn, attrs in results:
            if not dn:
                continue
            
            try:
                # 从 LDAP 属性中提取部门信息
                # cn 作为部门ID（外部系统的部门编号，必须是数字）
                # ou 作为部门名称
                
                dept_id = None
                dept_name = None
                
                if 'cn' in attrs and attrs['cn']:
                    cn_value = attrs['cn'][0]
                    cn_str = cn_value.decode('utf-8') if isinstance(cn_value, bytes) else cn_value
                    try:
                        dept_id = int(cn_str)
                    except ValueError:
                        logger.warning(f"部门 cn 不是数字，跳过: {cn_str}")
                        continue
                
                if 'ou' in attrs and attrs['ou']:
                    ou_value = attrs['ou'][0]
                    dept_name = ou_value.decode('utf-8') if isinstance(ou_value, bytes) else ou_value
                
                # 必须同时有部门ID和名称
                if dept_id is None or not dept_name:
                    logger.debug(f"跳过不完整的部门记录: dn={dn}")
                    continue
                
                # 创建或更新部门
                department, created = Department.objects.update_or_create(
                    id=dept_id,
                    defaults={'name': dept_name}
                )
                
                if created:
                    stats['departments_created'] += 1
                    logger.debug(f"创建部门: {dept_name} (ID: {dept_id})")
                else:
                    stats['departments_updated'] += 1
                    logger.debug(f"更新部门: {dept_name} (ID: {dept_id})")
                    
            except Exception as e:
                error_msg = f"同步部门 {dn} 失败: {e}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)
                
    except Exception as e:
        error_msg = f"同步部门信息失败: {e}"
        logger.error(error_msg, exc_info=True)
        stats['errors'].append(error_msg)


def _sync_users(ldap_conn, stats):
    """
    同步 LDAP 用户到 Django
    
    Args:
        ldap_conn: LDAP 连接对象
        stats: 统计信息字典
    """
    try:
        import ldap
        
        # 从配置获取用户搜索基准
        user_search_base = settings.AUTH_LDAP_USER_SEARCH.base_dn
        # 修改过滤器以获取所有用户
        user_filter = "(objectClass=inetOrgPerson)"
        
        logger.info(f"搜索 LDAP 用户: base={user_search_base}, filter={user_filter}")
        
        # 搜索所有用户
        results = ldap_conn.search_s(
            user_search_base,
            ldap.SCOPE_SUBTREE,
            user_filter,
            ['cn', 'sn', 'mail', 'employeeNumber', 'departmentNumber', 'memberOf']
        )
        
        logger.info(f"找到 {len(results)} 个 LDAP 用户")
        
        # 记录 LDAP 中存在的用户名
        ldap_usernames = set()
        
        for dn, attrs in results:
            if not dn or 'cn' not in attrs:
                continue
            
            try:
                # 解析用户属性
                username = attrs['cn'][0].decode('utf-8') if isinstance(attrs['cn'][0], bytes) else attrs['cn'][0]
                ldap_usernames.add(username)
                
                first_name = attrs.get('sn', [b''])[0]
                first_name = first_name.decode('utf-8') if isinstance(first_name, bytes) else first_name
                
                email = attrs.get('mail', [b''])[0]
                email = email.decode('utf-8') if isinstance(email, bytes) else email
                
                # 创建或更新用户
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'first_name': first_name,
                        'email': email,
                        'is_active': True,
                    }
                )
                if user.username == settings.SYSTEM_SUPER_ADMIN_USERNAME:
                    user.is_superuser = True
                    user.is_staff = True
                if created:
                    stats['users_created'] += 1
                    logger.debug(f"创建用户: {username}")
                else:
                    # 更新用户信息
                    user.first_name = first_name
                    user.email = email
                    user.is_active = True
                    stats['users_updated'] += 1
                    logger.debug(f"更新用户: {username}")
                
                # 如果密码为空 设置密码为 unusable
                if not user.password:
                    user.set_unusable_password()
                user.save()
                
                # 同步 Profile 信息
                _sync_user_profile_from_ldap(user, attrs)
                
            except Exception as e:
                error_msg = f"同步用户 {dn} 失败: {e}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)
        
        # 可选：禁用 LDAP 中不存在的用户
        _deactivate_removed_users(ldap_usernames, stats)
        
    except Exception as e:
        error_msg = f"同步用户信息失败: {e}"
        logger.error(error_msg, exc_info=True)
        stats['errors'].append(error_msg)


def _sync_user_profile_from_ldap(user, ldap_attrs):
    """
    从 LDAP 属性同步用户 Profile
    
    Args:
        user: Django User 对象
        ldap_attrs: LDAP 属性字典
    """
    try:
        from account.models import UserProfile
        
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        # 同步 employee_number
        if 'employeeNumber' in ldap_attrs and ldap_attrs['employeeNumber']:
            employee_number = ldap_attrs['employeeNumber'][0]
            profile.employee_number = employee_number.decode('utf-8') if isinstance(employee_number, bytes) else employee_number
        
        # 同步部门：从 departmentNumber 获取部门ID，然后关联到 Department 对象
        if 'departmentNumber' in ldap_attrs and ldap_attrs['departmentNumber']:
            department_number = ldap_attrs['departmentNumber'][0]
            dept_id_str = department_number.decode('utf-8') if isinstance(department_number, bytes) else department_number
            
            try:
                dept_id = int(dept_id_str)
                # 尝试获取对应的部门对象
                try:
                    department = Department.objects.get(id=dept_id)
                    profile.department = department
                    logger.debug(f"用户 {user.username} 关联到部门: {department.name} (ID: {dept_id})")
                except Department.DoesNotExist:
                    logger.warning(f"用户 {user.username} 的部门ID {dept_id} 不存在于 Department 表中")
                    profile.department = None
            except ValueError:
                logger.warning(f"用户 {user.username} 的 departmentNumber 不是有效的数字: {dept_id_str}")
                profile.department = None
        if not profile.plain_password:
            profile.plain_password = user.password  # 确保字段不为 None
        profile.save()
        
    except ImportError:
        logger.debug("UserProfile 模型不存在")
    except Exception as e:
        logger.error(f"同步用户 {user.username} Profile 失败: {e}")


def _sync_user_groups_from_ldap(user, ldap_attrs, ldap_conn):
    """
    从 LDAP 属性同步用户组
    
    注意：此函数已废弃，不再操作 Django 的 Group
    保留 Group 功能给后续的角色权限系统使用
    
    Args:
        user: Django User 对象
        ldap_attrs: LDAP 属性字典
        ldap_conn: LDAP 连接对象
    """
    pass  # 不再同步到 Django Group


def _deactivate_removed_users(ldap_usernames, stats):
    """
    禁用在 LDAP 中不存在的用户
    
    Args:
        ldap_usernames: LDAP 中存在的用户名集合
        stats: 统计信息字典
    """
    try:
        # 查找本地存在但 LDAP 中不存在的用户
        local_users = User.objects.filter(is_active=True).exclude(username__in=ldap_usernames)
        
        for user in local_users:
            # 排除超级管理员
            if user.is_superuser:
                continue
                
            user.is_active = False
            user.save()
            stats['users_deactivated'] += 1
            logger.info(f"禁用用户: {user.username} (不在 LDAP 中)")
            
    except Exception as e:
        logger.error(f"禁用已删除用户失败: {e}")
