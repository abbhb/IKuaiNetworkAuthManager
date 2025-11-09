"""
Models for sync_manager app - OpenVPN Account Management.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator
from encrypted_model_fields.fields import EncryptedCharField


class OpenVPNAccount(models.Model):
    """
    OpenVPN 账号模型，与 iKuai 系统账号对应
    与系统用户建立一对一关系
    """
    
    STATUS_CHOICES = [
        ('creating', '创建中'),
        ('active', '正常'),
        ('expired', '已过期'),
        ('disabled', '已禁用'),
        ('failed', '创建失败'),
        ('deleting', '删除中'),
    ]
    
    # 与系统用户一对一关系
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='openvpn_account',
        verbose_name='系统用户'
    )
    
    # iKuai 账号基本信息
    ikuai_id = models.IntegerField(
        'iKuai账号ID',
        null=True,
        blank=True,
        unique=True,
        help_text='iKuai系统返回的账号ID'
    )
    
    username = models.CharField(
        'VPN账号',
        max_length=100,
        unique=True,
        help_text='OpenVPN登录用户名'
    )
    
    password = EncryptedCharField(
        'VPN密码',
        max_length=100,
        help_text='OpenVPN登录密码（加密存储）'
    )
    
    # 账号状态
    status = models.CharField(
        '账号状态',
        max_length=20,
        choices=STATUS_CHOICES,
        default='creating',
        db_index=True
    )
    
    enabled = models.BooleanField(
        '是否启用',
        default=True,
        help_text='对应iKuai的enabled字段'
    )
    
    # 时间相关字段
    start_time = models.DateTimeField(
        '开始时间',
        null=True,
        blank=True,
        help_text='账号生效时间'
    )
    
    expires = models.DateTimeField(
        '过期时间',
        null=True,
        blank=True,
        db_index=True,
        help_text='账号到期时间'
    )
    
    last_conntime = models.DateTimeField(
        '最后连接时间',
        null=True,
        blank=True,
        help_text='最后一次连接VPN的时间'
    )
    
    last_offtime = models.DateTimeField(
        '最后离线时间',
        null=True,
        blank=True,
        help_text='最后一次断开连接的时间'
    )
    
    # iKuai 详细配置
    ip_addr = models.GenericIPAddressField(
        'IP地址',
        null=True,
        blank=True,
        help_text='分配的VPN IP地址'
    )
    
    ip_type = models.IntegerField(
        'IP类型',
        default=0,
        help_text='0=自动分配'
    )
    
    mac = models.CharField(
        'MAC地址',
        max_length=17,
        blank=True,
        default=''
    )
    
    phone = models.CharField(
        '电话',
        max_length=20,
        blank=True,
        default=''
    )
    
    address = models.CharField(
        '地址',
        max_length=200,
        blank=True,
        default=''
    )
    
    comment = models.TextField(
        '备注',
        blank=True,
        default=''
    )
    
    # 连接配置
    ppptype = models.CharField(
        'PPP类型',
        max_length=20,
        default='any'
    )
    
    pppname = models.CharField(
        'PPP名称',
        max_length=50,
        blank=True,
        default=''
    )
    
    bind_ifname = models.CharField(
        '绑定接口',
        max_length=50,
        default='any'
    )
    
    bind_vlanid = models.CharField(
        '绑定VLAN ID',
        max_length=20,
        default='0'
    )
    
    auto_vlanid = models.IntegerField(
        '自动VLAN',
        default=1
    )
    
    # 流量和连接限制
    share = models.IntegerField(
        '共享连接数',
        default=1,
        validators=[MinValueValidator(1)],
        help_text='允许的最大并发连接数'
    )
    
    upload = models.BigIntegerField(
        '上传限速',
        default=0,
        help_text='上传速度限制(KB/s)，0为不限速'
    )
    
    download = models.BigIntegerField(
        '下载限速',
        default=0,
        help_text='下载速度限制(KB/s)，0为不限速'
    )
    
    duration = models.IntegerField(
        '在线时长',
        default=0,
        help_text='累计在线时长(秒)'
    )
    
    packages = models.BigIntegerField(
        '流量包',
        default=0,
        help_text='流量包大小(字节)'
    )
    
    # 其他字段
    cardid = models.CharField(
        '卡号',
        max_length=100,
        blank=True,
        default=''
    )
    
    auto_mac = models.IntegerField(
        '自动MAC',
        default=1
    )
    
    # 任务相关
    task_id = models.CharField(
        'Celery任务ID',
        max_length=100,
        blank=True,
        default='',
        help_text='创建账号的Celery任务ID'
    )
    
    error_message = models.TextField(
        '错误信息',
        blank=True,
        default='',
        help_text='创建失败时的错误信息'
    )
    
    # 记录创建和更新时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'openvpn_account'
        verbose_name = 'OpenVPN账号'
        verbose_name_plural = 'OpenVPN账号'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['expires']),
            models.Index(fields=['username']),
        ]
    
    def __str__(self):
        return f'{self.username} ({self.user.username})'
    
    def is_expired(self):
        """检查账号是否过期"""
        if not self.expires:
            return False
        return timezone.now() > self.expires
    
    def is_active(self):
        """检查账号是否可用"""
        return (
            self.status == 'active' and
            self.enabled and
            not self.is_expired()
        )
    
    def days_until_expiry(self):
        """返回距离过期的天数"""
        if not self.expires:
            return None
        delta = self.expires - timezone.now()
        return delta.days if delta.days > 0 else 0
    
    def update_from_ikuai_data(self, data):
        """从 iKuai API 返回的数据更新账号信息"""
        from datetime import datetime
        
        # 基本信息
        self.ikuai_id = data.get('id')
        self.username = data.get('username', self.username)
        self.password = data.get('passwd', self.password)
        self.enabled = data.get('enabled') == 'yes'
        
        # IP和网络配置
        self.ip_addr = data.get('ip_addr') or None
        self.ip_type = data.get('ip_type', 0)
        self.mac = data.get('mac', '')
        
        # 联系信息
        self.phone = data.get('phone', '')
        self.address = data.get('address', '')
        self.comment = data.get('comment', '')
        
        # 连接配置
        self.ppptype = data.get('ppptype', 'any')
        self.pppname = data.get('pppname', '')
        self.bind_ifname = data.get('bind_ifname', 'any')
        self.bind_vlanid = data.get('bind_vlanid', '0')
        self.auto_vlanid = data.get('auto_vlanid', 1)
        
        # 限制配置
        self.share = data.get('share', 1)
        self.upload = data.get('upload', 0)
        self.download = data.get('download', 0)
        self.duration = data.get('duration', 0)
        self.packages = data.get('packages', 0)
        
        # 其他
        self.cardid = data.get('cardid', '')
        self.auto_mac = data.get('auto_mac', 1)
        
        # 时间字段（Unix时间戳转换为timezone-aware datetime）
        if data.get('start_time'):
            self.start_time = datetime.fromtimestamp(data['start_time'], tz=timezone.get_current_timezone())
        
        if data.get('expires'):
            self.expires = datetime.fromtimestamp(data['expires'], tz=timezone.get_current_timezone())
        
        if data.get('last_conntime'):
            self.last_conntime = datetime.fromtimestamp(data['last_conntime'], tz=timezone.get_current_timezone())
        
        if data.get('last_offtime'):
            self.last_offtime = datetime.fromtimestamp(data['last_offtime'], tz=timezone.get_current_timezone())
        
        # 更新状态
        if self.is_expired():
            self.status = 'expired'
        elif self.enabled and self.ikuai_id:
            self.status = 'active'
        elif not self.enabled:
            self.status = 'disabled'

