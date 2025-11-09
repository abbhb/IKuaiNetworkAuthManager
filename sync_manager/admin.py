"""
Admin configuration for sync_manager app.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import OpenVPNAccount


@admin.register(OpenVPNAccount)
class OpenVPNAccountAdmin(admin.ModelAdmin):
    """OpenVPN 账号管理"""
    
    list_display = [
        'username',
        'user_link',
        'status_badge',
        'ip_addr',
        'expires_info',
        'last_conntime',
        'enabled',
        'created_at',
    ]
    
    list_filter = [
        'status',
        'enabled',
        ('expires', admin.DateFieldListFilter),
        'created_at',
    ]
    
    search_fields = [
        'username',
        'user__username',
        'user__first_name',
        'user__last_name',
        'user__email',
        'ip_addr',
    ]
    
    readonly_fields = [
        'ikuai_id',
        'task_id',
        'created_at',
        'updated_at',
        'last_conntime',
        'last_offtime',
    ]
    
    fieldsets = (
        ('基本信息', {
            'fields': (
                'user',
                'username',
                'password',
                'status',
                'enabled',
            )
        }),
        ('iKuai 信息', {
            'fields': (
                'ikuai_id',
                'ip_addr',
                'ip_type',
                'mac',
            )
        }),
        ('时间信息', {
            'fields': (
                'start_time',
                'expires',
                'last_conntime',
                'last_offtime',
            )
        }),
        ('连接配置', {
            'fields': (
                'ppptype',
                'pppname',
                'bind_ifname',
                'bind_vlanid',
                'auto_vlanid',
            ),
            'classes': ('collapse',),
        }),
        ('限制配置', {
            'fields': (
                'share',
                'upload',
                'download',
                'duration',
                'packages',
            ),
            'classes': ('collapse',),
        }),
        ('其他信息', {
            'fields': (
                'phone',
                'address',
                'comment',
                'cardid',
                'auto_mac',
            ),
            'classes': ('collapse',),
        }),
        ('任务信息', {
            'fields': (
                'task_id',
                'error_message',
            ),
            'classes': ('collapse',),
        }),
        ('记录时间', {
            'fields': (
                'created_at',
                'updated_at',
            )
        }),
    )
    
    def user_link(self, obj):
        """用户链接"""
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = '系统用户'
    
    def status_badge(self, obj):
        """状态徽章"""
        colors = {
            'creating': '#f59e0b',
            'active': '#10b981',
            'expired': '#ef4444',
            'disabled': '#6b7280',
            'failed': '#ef4444',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; '
            'border-radius: 10px; font-size: 12px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = '状态'
    
    def expires_info(self, obj):
        """过期信息"""
        if not obj.expires:
            return '-'
        
        days = obj.days_until_expiry()
        now = timezone.now()
        
        if obj.expires < now:
            return format_html(
                '<span style="color: #ef4444;">已过期</span>'
            )
        elif days <= 7:
            return format_html(
                '<span style="color: #f59e0b;">{} 天后过期</span>',
                days
            )
        else:
            return format_html(
                '<span style="color: #10b981;">{} 天后过期</span>',
                days
            )
    expires_info.short_description = '过期状态'
    
    def get_queryset(self, request):
        """优化查询"""
        qs = super().get_queryset(request)
        return qs.select_related('user')
    
    actions = ['sync_accounts', 'enable_accounts', 'disable_accounts']
    
    def sync_accounts(self, request, queryset):
        """同步选中的账号"""
        from .tasks import sync_openvpn_accounts
        sync_openvpn_accounts.delay()
        self.message_user(request, '同步任务已提交')
    sync_accounts.short_description = '同步账号状态'
    
    def enable_accounts(self, request, queryset):
        """启用账号"""
        count = queryset.update(enabled=True)
        self.message_user(request, f'已启用 {count} 个账号')
    enable_accounts.short_description = '启用选中的账号'
    
    def disable_accounts(self, request, queryset):
        """禁用账号"""
        count = queryset.update(enabled=False, status='disabled')
        self.message_user(request, f'已禁用 {count} 个账号')
    disable_accounts.short_description = '禁用选中的账号'
