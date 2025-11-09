"""
Admin configuration for account app.
"""

from django.contrib import admin

# Register your models here.
# User and Group are already registered by Django's admin


from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, Department


# Department Admin
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """部门管理"""
    list_display = ['id', 'name', 'user_count', 'created_at', 'updated_at']
    search_fields = ['id', 'name']
    list_per_page = 50
    ordering = ['id']
    
    def user_count(self, obj):
        """显示部门人数"""
        return obj.users.count()
    user_count.short_description = '人数'


# User Profile Inline
class UserProfileInline(admin.StackedInline):
    """Inline admin for UserProfile."""
    model = UserProfile
    can_delete = False
    verbose_name = '用户扩展信息'
    verbose_name_plural = '用户扩展信息'
    fields = ['employee_number', 'department', 'phone', 'avatar']
    autocomplete_fields = ['department']


# Extend User Admin
class UserAdmin(BaseUserAdmin):
    """Extended User admin with profile."""
    inlines = (UserProfileInline,)
    list_display = ['username', 'name', 'email', 'employee_number', 'department_name', 'is_staff', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'profile__employee_number', 'profile__department__name']
    list_filter = ['is_staff', 'is_active', 'is_superuser', 'profile__department']
    
    def name(self, obj):
        """显示姓名"""
        return obj.first_name or '-'
    name.short_description = '姓名'
    
    def employee_number(self, obj):
        """显示员工编号"""
        return obj.profile.employee_number if hasattr(obj, 'profile') else '-'
    employee_number.short_description = '员工编号'
    
    def department_name(self, obj):
        """显示部门名称"""
        if hasattr(obj, 'profile') and obj.profile.department:
            return f'{obj.profile.department.name} ({obj.profile.department.id})'
        return '-'
    department_name.short_description = '部门'


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

