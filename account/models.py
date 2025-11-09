"""
Account models - uses Django's built-in User model.
"""

from django.db import models

# 使用 Django 自带的 User 模型
# from django.contrib.auth.models import User

from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from encrypted_model_fields.fields import EncryptedCharField


class Department(models.Model):
    """
    部门表，对应 LDAP 的 OU（Organizational Unit）
    部门ID来自外部系统，不使用自增ID
    """
    
    id = models.BigIntegerField(
        '部门ID',
        primary_key=True,
        help_text='从LDAP cn字段同步，外部系统提供的部门ID'
    )
    
    name = models.CharField(
        '部门名称',
        max_length=200,
        help_text='从LDAP ou字段同步的部门名称'
    )
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'department'
        verbose_name = '部门'
        verbose_name_plural = '部门'
        ordering = ['id']
    
    def __str__(self):
        return f'{self.name} ({self.id})'


class UserProfile(models.Model):
    """
    用户扩展信息，存储 LDAP 额外属性
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='用户'
    )
    
    # LDAP 属性
    employee_number = models.CharField(
        '员工编号',
        max_length=50,
        blank=True,
        help_text='LDAP employeeNumber 字段'
    )
    
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name='所属部门',
        help_text='关联到部门表，从LDAP departmentNumber字段同步'
    )
    
    # 额外信息
    phone = models.CharField('电话', max_length=20, blank=True)
    avatar = models.URLField('头像', blank=True)
    
    # 加密存储的明文密码（用于LDAP或其他系统认证）
    plain_password = EncryptedCharField(
        '明文密码',
        max_length=128,
        blank=True,
        default='',
        help_text='加密存储的明文密码，用于LDAP认证或同步到其他系统'
    )
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'user_profile'
        verbose_name = '用户信息'
        verbose_name_plural = '用户信息'
        indexes = [
            models.Index(fields=['employee_number']),
            models.Index(fields=['department']),
        ]
    
    def __str__(self):
        return f'{self.user.username} Profile'


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """创建或更新用户 Profile"""
    if created:
        UserProfile.objects.get_or_create(user=instance)
    elif hasattr(instance, 'profile'):
        instance.profile.save()

