"""
Custom middleware for the network_manager project.
"""

import re
from django.shortcuts import redirect
from django.conf import settings
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin


def login_exempt(view_func):
    """
    Decorator to mark a view as exempt from login requirements.
    """
    view_func.login_exempt = True
    return view_func


class LoginRequiredMiddleware(MiddlewareMixin):
    """
    Middleware that requires a user to be authenticated to view any page.
    Exemptions can be specified using the @login_exempt decorator.
    """

    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        检查用户是否已登录,未登录则重定向到登录页面
        
        Args:
            request: HTTP 请求对象
            view_func: 视图函数
            view_args: 视图位置参数
            view_kwargs: 视图关键字参数
            
        Returns:
            None 表示继续处理,或返回 HttpResponse 进行重定向
        """
        # 检查视图是否被标记为 login_exempt
        if getattr(view_func, "login_exempt", False):
            return None
        
        # 检查用户是否已认证
        if request.user.is_authenticated:
            return None
        
        # 未登录用户重定向到登录页面
        # 使用相对路径,让 Django 根据 request 的协议和域名自动构建正确的 URL
        next_url = request.get_full_path()
        return redirect(f'{settings.LOGIN_URL}?next={next_url}')
