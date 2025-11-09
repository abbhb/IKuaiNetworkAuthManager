"""
Celery tasks for sync_manager app - OpenVPN Account Management.
"""

import logging
import requests
from celery import shared_task
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta
from sync_manager.client.ikuai import IKuaiAPIClient

logger = logging.getLogger(__name__)



@shared_task(bind=True, max_retries=1)
def create_openvpn_account(self, user_id, username, password, expires_days=30, **kwargs):
    """
    创建 OpenVPN 账号的 Celery 任务
    
    Args:
        user_id: Django User ID
        username: VPN账号用户名
        password: VPN账号密码
        expires_days: 账号有效期（天）
        **kwargs: 其他可选参数
    """
    from sync_manager.models import OpenVPNAccount
    from django.conf import settings
    
    try:
        # 获取用户
        user = User.objects.get(id=user_id)
        
        # 获取或创建账号记录
        account, created = OpenVPNAccount.objects.get_or_create(
            user=user,
            defaults={
                'username': username,
                'password': password,
                'status': 'creating',
                'task_id': self.request.id,
            }
        )
        
        
        if not created:
            account.status = 'creating'
            account.task_id = self.request.id
            account.error_message = ''
            account.save()
        if created and account.status == 'creating':
            return {'status': 'already creating'}
        # 获取 iKuai 配置
        ikuai_config = getattr(settings, 'IKUAI_CONFIG', {})
        base_url = ikuai_config.get('base_url', 'http://192.168.1.1')
        admin_user = ikuai_config.get('username', 'admin')
        admin_pass = ikuai_config.get('password', 'admin')
        
        # 创建 API 客户端
        client = IKuaiAPIClient(base_url, admin_user, admin_pass)
        
        # 调用 iKuai API 创建账号
        result = client.create_account(
            username=username,
            password=password,
            expires_days=expires_days,
            comment=f'Created for user: {user.username}',
            **kwargs
        )
        
        # 获取创建后的账号信息
        ikuai_account = client.get_account(username)
        
        if ikuai_account:
            # 更新本地账号信息
            account.update_from_ikuai_data(ikuai_account)
            account.status = 'active'
            account.save()
            
            logger.info(f'Successfully created OpenVPN account for user {user.username}')
            return {
                'status': 'success',
                'account_id': account.id,
                'username': username,
            }
        else:
            raise Exception('Account created but not found in iKuai system')
    
    except Exception as exc:
        logger.error(f'Error creating OpenVPN account: {str(exc)}')
        
        # 更新账号状态为失败
        try:
            account = OpenVPNAccount.objects.get(user_id=user_id)
            account.status = 'failed'
            account.error_message = str(exc)
            account.save()
        except Exception as exc:
            logger.error(f'Failed to update account status for user {user_id} after creation error: {str(exc)}')
            pass
        
        # 重试任务
        # raise self.retry(exc=exc, countdown=60)


@shared_task
def sync_openvpn_accounts():
    """
    同步所有 OpenVPN 账号状态的定时任务
    """
    from sync_manager.models import OpenVPNAccount
    from django.conf import settings
    MIDDLE_STATE = ['creating', 'deleting']
    try:
        ikuai_config = getattr(settings, 'IKUAI_CONFIG', {})
        base_url = ikuai_config.get('base_url', 'http://192.168.1.1')
        admin_user = ikuai_config.get('username', 'admin')
        admin_pass = ikuai_config.get('password', 'admin')
        
        client = IKuaiAPIClient(base_url, admin_user, admin_pass)
        
        # 获取所有活跃账号
        accounts = OpenVPNAccount.objects.filter(
            status__in=['active', 'creating']
        )
        
        synced_count = 0
        for account in accounts:
            try:
                ikuai_account = client.get_account(account.username)
                
                if ikuai_account:
                    account.update_from_ikuai_data(ikuai_account)
                    account.save()
                    synced_count += 1
                else:
                    logger.warning(f'Account {account.username} not found in iKuai')
            except Exception as e:
                logger.error(f'Error syncing account {account.username}: {str(e)}')
                # 如果创建时间超时1小时，则标记为失败
                if account.status in MIDDLE_STATE and timezone.now() - account.created_at > timedelta(hours=1):
                    account.status = 'failed'
                    account.error_message = '操作超时,请手动重试。'
                    account.save()
                continue
        
        logger.info(f'Successfully synced {synced_count} OpenVPN accounts')
        return {'status': 'success', 'synced_count': synced_count}
    
    except Exception as e:
        logger.error(f'Error in sync_openvpn_accounts: {str(e)}')
        raise


@shared_task
def check_expired_accounts():
    """
    检查并更新过期账号状态的定时任务
    """
    from sync_manager.models import OpenVPNAccount
    
    try:
        now = timezone.now()
        
        # 查找已过期但状态还是active的账号
        expired_accounts = OpenVPNAccount.objects.filter(
            status='active',
            expires__lt=now
        )
        
        count = expired_accounts.update(status='expired')
        
        logger.info(f'Marked {count} accounts as expired')
        return {'status': 'success', 'expired_count': count}
    
    except Exception as e:
        logger.error(f'Error checking expired accounts: {str(e)}')
        raise


@shared_task(bind=True, max_retries=3)
def delete_openvpn_account(self, account_id):
    """
    删除 OpenVPN 账号的 Celery 任务
    
    Args:
        account_id: OpenVPNAccount ID
    """
    from sync_manager.models import OpenVPNAccount
    from django.conf import settings
    
    try:
        # 获取账号记录
        try:
            account = OpenVPNAccount.objects.get(id=account_id)
        except OpenVPNAccount.DoesNotExist:
            logger.warning(f'Account {account_id} does not exist in database')
            return {'status': 'already_deleted', 'message': 'Account not found in database'}
        if account.status == 'deleting':
            # 可能被用户二次触发删除了
            logger.info(f'Account {account_id} is already being deleted')
            return {'status': 'already_deleting', 'message': 'Account is already being deleted'}

        # 更新状态为删除中
        account.status = 'deleting'
        account.task_id = self.request.id
        account.error_message = ''
        account.save()
        
        # 获取 iKuai 配置
        ikuai_config = getattr(settings, 'IKUAI_CONFIG', {})
        base_url = ikuai_config.get('base_url', 'http://192.168.1.1')
        admin_user = ikuai_config.get('username', 'admin')
        admin_pass = ikuai_config.get('password', 'admin')
        
        # 创建 API 客户端
        client = IKuaiAPIClient(base_url, admin_user, admin_pass)
        
        # 如果有 iKuai ID，尝试从 iKuai 删除账号
        if account.ikuai_id:
            try:
                client.delete_account(account.ikuai_id)
                logger.info(f'Successfully deleted account {account.username} (ID: {account.ikuai_id}) from iKuai')
            except Exception as ikuai_error:
                # 容错处理：检查账号是否已经在 iKuai 中不存在了
                try:
                    ikuai_account = client.get_account(account.username)
                    if ikuai_account is None:
                        # 账号在 iKuai 中已经不存在，视为已删除
                        logger.info(f'Account {account.username} does not exist in iKuai, treating as deleted')
                    else:
                        # 账号仍然存在，删除失败
                        raise ikuai_error
                except Exception as check_error:
                    # 如果检查也失败，记录错误但仍然尝试删除本地记录
                    logger.error(f'Error checking account existence in iKuai: {str(check_error)}')
                    logger.warning(f'Proceeding with local deletion for account {account.username}')
        
        # 删除本地数据库记录
        username = account.username
        user_id = account.user.id if account.user else None
        account.delete()
        
        logger.info(f'Successfully deleted local account record for {username} (user_id: {user_id})')
        return {
            'status': 'success',
            'username': username,
            'user_id': user_id,
        }
    
    except OpenVPNAccount.DoesNotExist:
        # 账号已经被删除
        logger.info(f'Account {account_id} already deleted')
        account = OpenVPNAccount.objects.filter(id=account_id).first()
        if account:
            account.delete()
        return {'status': 'already_deleted'}
    
    except Exception as exc:
        logger.error(f'Error deleting OpenVPN account {account_id}: {str(exc)}')
        
        # 更新账号状态为失败
        try:
            account = OpenVPNAccount.objects.get(id=account_id)
            account.status = 'failed'
            account.error_message = f'删除失败: {str(exc)}'
            account.save()
        except Exception as exc:
            logger.error(f'Failed to update account status for {account_id} after deletion error: {str(exc)}')
            pass
        
        # 重试任务
        raise self.retry(exc=exc, countdown=60)


