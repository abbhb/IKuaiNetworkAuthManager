"""
Views for OpenVPN Account Management.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.utils import timezone
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json

from account.models import UserProfile

from .models import OpenVPNAccount
from .tasks import create_openvpn_account, delete_openvpn_account


def openvpn_dashboard(request):
    """
    OpenVPN 账号管理首页
    """
    try:
        account = OpenVPNAccount.objects.get(user=request.user)
    except OpenVPNAccount.DoesNotExist:
        account = None
    
    context = {
        'account': account,
        'now': timezone.now(),
    }
    
    return render(request, 'sync_manager/openvpn_dashboard.html', context)


@require_http_methods(["POST"])
def create_account(request):
    """
    申请创建 OpenVPN 账号
    """
    try:
        # 检查用户是否已有账号
        existing_account = OpenVPNAccount.objects.filter(user=request.user).first()
        
        if existing_account:
            if existing_account.status == 'creating':
                return JsonResponse({
                    'success': False,
                    'message': '账号正在创建中，请稍后刷新页面查看'
                })
            elif existing_account.status == 'failed':
                # 允许重新创建失败的账号
                existing_account.delete()
            else:
                return JsonResponse({
                    'success': False,
                    'message': '您已经有OpenVPN账号了'
                })
        
        # 生成账号用户名和密码
        username = f'{request.user.username}'
        
        # 使用数据库密码，如果没有则生成随机密码
        import secrets
        import string
        user_profile = UserProfile.objects.get(user=request.user)
        if (not user_profile) or (not user_profile.plain_password):
            # 生成8位随机密码
            alphabet = string.ascii_letters + string.digits
            password = ''.join(secrets.choice(alphabet) for i in range(8))
        else:
            password = user_profile.plain_password

        # 获取有效期（默认30天）
        expires_days = int(request.POST.get('expires_days', 30))
        
        # 创建本地账号记录
        account = OpenVPNAccount.objects.create(
            user=request.user,
            username=username,
            password=password,
            status='creating',
        )
        
        # 异步创建 iKuai 账号
        task = create_openvpn_account.delay(
            user_id=request.user.id,
            username=username,
            password=password,
            expires_days=expires_days,
        )
        
        account.task_id = task.id
        account.save()
        
        return JsonResponse({
            'success': True,
            'message': '账号创建请求已提交，请稍后刷新页面查看',
            'task_id': task.id,
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'创建账号失败: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def account_status(request):
    """
    获取账号状态（用于AJAX轮询）
    """
    try:
        account = OpenVPNAccount.objects.get(user=request.user)
        
        data = {
            'success': True,
            'status': account.status,
            'username': account.username,
            'password': account.password if account.status == 'active' else None,
            'expires': account.expires.isoformat() if account.expires else None,
            'days_until_expiry': account.days_until_expiry(),
            'is_active': account.is_active(),
            'ip_addr': account.ip_addr,
            'last_conntime': account.last_conntime.isoformat() if account.last_conntime else None,
            'error_message': account.error_message if account.status == 'failed' else None,
        }
        
        return JsonResponse(data)
    
    except OpenVPNAccount.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '账号不存在'
        }, status=404)


@require_http_methods(["GET"])
def download_config(request):
    """
    下载 OpenVPN 配置文件
    """
    try:
        account = OpenVPNAccount.objects.get(user=request.user)
        
        # 检查账号是否可用
        if not account.is_active():
            return HttpResponse('账号不可用或已过期', status=403)
        
        # 获取 OpenVPN 服务器配置
        vpn_config = getattr(settings, 'OPENVPN_CONFIG', {})
        server_host = vpn_config.get('server_host', 'vpn.example.com')
        server_port = vpn_config.get('server_port', '1194')
        protocol = vpn_config.get('protocol', 'udp')
        
        # 渲染配置模板
        context = {
            'username': account.username,
            'password': account.password,
            'server_host': server_host,
            'server_port': server_port,
            'protocol': protocol,
            'ca_cert': vpn_config.get('ca_cert', '请联系管理员获取CA证书'),
        }
        
        config_content = render_to_string('sync_manager/openvpn_config.ovpn', context)
        
        # 返回文件
        response = HttpResponse(config_content, content_type='application/x-openvpn-profile')
        response['Content-Disposition'] = f'attachment; filename="{account.username}.ovpn"'
        
        return response
    
    except OpenVPNAccount.DoesNotExist:
        raise Http404('账号不存在')
    except Exception as e:
        return HttpResponse(f'生成配置文件失败: {str(e)}', status=500)


@login_required
@require_http_methods(["POST"])
def renew_account(request):
    """
    续期账号
    """
    try:
        account = OpenVPNAccount.objects.get(user=request.user)
        
        if account.status not in ['active', 'expired']:
            return JsonResponse({
                'success': False,
                'message': '只能续期正常或已过期的账号'
            })
        
        # 获取续期天数（默认30天）
        extends_days = int(request.POST.get('extends_days', 30))
        
        # 从当前过期时间或当前时间开始延长
        from datetime import timedelta
        if account.expires and account.expires > timezone.now():
            new_expires = account.expires + timedelta(days=extends_days)
        else:
            new_expires = timezone.now() + timedelta(days=extends_days)
        
        account.expires = new_expires
        if account.status == 'expired':
            account.status = 'active'
        account.save()
        
        # TODO: 调用 iKuai API 更新过期时间
        
        return JsonResponse({
            'success': True,
            'message': f'账号已续期{extends_days}天',
            'expires': account.expires.isoformat(),
        })
    
    except OpenVPNAccount.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '账号不存在'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'续期失败: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def delete_account(request):
    """
    删除账号（异步执行）
    """
    try:
        account = OpenVPNAccount.objects.get(user=request.user)
        
        # 检查账号状态
        if account.status == 'deleting':
            return JsonResponse({
                'success': False,
                'message': '账号正在删除中，请稍后刷新页面查看'
            })
        
        if account.status == 'creating':
            return JsonResponse({
                'success': False,
                'message': '账号正在创建中，无法删除，请等待创建完成或者超时（10min）后再进行删除'
            })
        
        # 标记为删除中状态
        account.status = 'deleting'
        account.error_message = ''
        account.save()
        
        # 异步执行删除任务
        task = delete_openvpn_account.delay(account.id)
        
        account.task_id = task.id
        account.save()
        
        return JsonResponse({
            'success': True,
            'message': '账号删除请求已提交，请稍后刷新页面查看',
            'task_id': task.id,
        })
    
    except OpenVPNAccount.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '账号不存在,可能已经删除了，请刷新页面验证'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'删除失败: {str(e)}'
        }, status=500)
