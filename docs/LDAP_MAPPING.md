# LDAP 字段映射说明

## 字段映射表

### Django User 表

| Django 字段 | LDAP 属性 | 说明 |
|------------|----------|------|
| `id` | (自增) | 表主键 |
| `username` | `cn` | 登录用户名 |
| `first_name` | `sn` | 姓名 |
| `email` | `mail` | 邮箱 |

### Department 部门表

| Department 字段 | LDAP 属性 | 说明 |
|----------------|----------|------|
| `id` | `cn` | 部门ID（Long类型，非自增，来自外部系统） |
| `name` | `ou` | 部门名称 |

### UserProfile 扩展表

| Profile 字段 | LDAP 属性 | 说明 |
|-------------|----------|------|
| `employee_number` | `employeeNumber` | 业务用户ID |
| `department` | `departmentNumber` | 部门外键（关联到 Department 表） |

## 同步流程

1. **先同步部门**：从 LDAP 的 `organizationalUnit` 对象类型中获取部门信息
   - `cn` → Department.id（必须是数字）
   - `ou` → Department.name

2. **再同步用户**：从 LDAP 的 `inetOrgPerson` 对象类型中获取用户信息
   - 基本信息同步到 User 表
   - 扩展信息同步到 UserProfile 表
   - `departmentNumber` 关联到已存在的 Department 对象

## 重要说明

- **Django Group 保留**：不从 LDAP 同步，保留给后续的角色权限功能使用
- **Department 表**：对应组织架构中的部门概念，不是权限组
- **外键关联**：用户通过 `UserProfile.department` 外键关联到部门

## 使用示例

```python
from django.contrib.auth.models import User
from account.models import Department

# 获取用户
user = User.objects.get(username='zhangsan')

# 访问字段
print(user.username)                    # 登录用户名
print(user.first_name)                  # 姓名 (可以理解为 name)
print(user.email)                       # 邮箱
print(user.profile.employee_number)     # 业务用户ID
print(user.profile.department)          # 部门对象
print(user.profile.department.name)     # 部门名称
print(user.profile.department.id)       # 部门ID

# 查询部门下的所有用户
dept = Department.objects.get(id=10001)
users = dept.users.all()  # 反向查询
```

## 环境变量配置

```bash
LDAP_SERVER_URI=ldap://localhost:388
LDAP_BIND_DN=cn=admin,dc=example,dc=top
LDAP_BIND_PASSWORD=123456
LDAP_USER_SEARCH_BASE=ou=ikuaier,dc=example,dc=top
LDAP_GROUP_SEARCH_BASE=ou=groups,dc=example,dc=top
# 可选：部门搜索基准（默认使用 USER_SEARCH_BASE）
# LDAP_DEPT_SEARCH_BASE=ou=ikuaier,dc=example,dc=top
```
