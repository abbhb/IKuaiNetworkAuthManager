# Network Manager

一个集成了 LDAP 认证、MySQL、Redis 和 Celery 的 Django 项目，用于管理IKuai网络资源。

## 功能特性

- ✅ **灵活的配置系统**: 支持 dev/prod/default 三层配置，根据环境变量自动加载
- ✅ **LDAP 集成认证**: 专门的 account 应用管理 LDAP 认证和用户同步
  - 登录时自动同步/创建用户
  - 启动时全量同步 LDAP 用户和组织架构
  - 定时任务自动同步（每小时）
  - 本地密码设为 unusable，始终通过 LDAP 认证
- ✅ **登录拦截**: 未认证用户自动跳转到登录页
- ✅ **MySQL 数据库**: 生产级别的关系型数据库支持
- ✅ **Redis 缓存和会话**: 高性能的缓存和会话存储
- ✅ **Celery 异步任务**: 支持后台任务和定时任务

## 项目结构

```
network_manager/
├── config/                      # 项目配置
│   ├── settings/               # 分层配置目录
│   │   ├── __init__.py        # 配置加载器
│   │   ├── default.py         # 默认配置(总是加载)
│   │   ├── dev.py             # 开发环境配置
│   │   └── prod.py            # 生产环境配置
│   ├── celery.py              # Celery 配置
│   ├── middleware.py          # 自定义中间件
│   ├── urls.py                # URL 路由
│   └── wsgi.py                # WSGI 入口
├── account/                   # 认证和用户同步应用
│   ├── backends.py            # 自定义 LDAP 认证后端
│   ├── tasks.py               # 用户同步 Celery 任务
│   ├── apps.py                # 应用配置（启动同步）
│   └── README.md              # 详细文档
├── sync_manager/              # 应用管理模块
│   ├── models.py              # 数据模型（UserProfile）
│   ├── tasks.py               # Celery 任务
│   ├── admin.py               # 管理后台
│   └── ...
├── templates/                 # 模板文件
│   └── registration/
│       └── login.html         # 登录页面
├── manage.py                  # Django 管理命令
├── MIGRATION_GUIDE.md         # 迁移指南
└── pyproject.toml            # 项目依赖
```

## 安装和配置

### 1. 安装依赖

```bash
# 基础依赖
uv sync

# 如果需要 LDAP 支持 (Windows 需要额外安装 OpenLDAP 客户端库)
uv sync --extra ldap
```

### 2. 环境变量配置

创建 `.env` 文件或设置环境变量:

```bash
# 环境选择 (dev/prod, 默认: dev)
DJANGO_ENV=dev

# Django 配置
DJANGO_SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# MySQL 数据库
DB_NAME=network_manager
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=3306

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# LDAP 配置 (可选)
LDAP_SERVER_URI=ldap://ldap.example.com:389
LDAP_BIND_DN=cn=admin,dc=example,dc=com
LDAP_BIND_PASSWORD=admin_password
LDAP_USER_SEARCH_BASE=ou=users,dc=example,dc=com
LDAP_GROUP_SEARCH_BASE=ou=groups,dc=example,dc=com
LDAP_ACTIVE_GROUP=cn=active,ou=groups,dc=example,dc=com
LDAP_STAFF_GROUP=cn=staff,ou=groups,dc=example,dc=com
LDAP_ADMIN_GROUP=cn=admins,ou=groups,dc=example,dc=com
```

### 3. 数据库初始化

```bash
# 创建 MySQL 数据库
mysql -u root -p
CREATE DATABASE network_manager CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 运行迁移
uv run python manage.py makemigrations
uv run python manage.py migrate

# 创建超级用户
uv run python manage.py createsuperuser
```

### 4. 启动服务

#### 开发环境

```bash
# 启动 Django 开发服务器
uv run python manage.py runserver

# 启动 Celery Worker (新终端)
uv run celery -A config worker -l info

# 启动 Celery Beat 定时任务调度器 (新终端)
uv run celery -A config beat -l info
```

#### 生产环境

```bash
# 设置环境变量
set DJANGO_ENV=prod

# 收集静态文件
uv run python manage.py collectstatic --noinput

# 使用 Gunicorn 启动 (Linux)
gunicorn config.wsgi:application --bind 0.0.0.0:8000

# 启动 Celery (后台)
celery -A config worker -l info --detach
celery -A config beat -l info --detach
```

## 配置系统说明

### 配置加载顺序

1. **default.py**: 总是被加载，包含所有基础配置
2. **dev.py** 或 **prod.py**: 根据 `DJANGO_ENV` 环境变量加载，覆盖 default.py 的配置

### 添加新的配置

在 `config/settings/default.py` 中添加默认配置:

```python
MY_NEW_SETTING = 'default_value'
```

在 `config/settings/dev.py` 或 `prod.py` 中覆盖:

```python
MY_NEW_SETTING = 'dev_value'  # 或 'prod_value'
```

## 数据模型

### UserProfile (用户扩展信息)

存储用户的 LDAP 扩展属性和额外信息。

| 字段 | 类型 | 说明 |
|------|------|------|
| user | OneToOneField | 关联的 Django User |
| employee_number | CharField | 员工编号（来自 LDAP employeeNumber） |
| department_number | CharField | 部门编号（来自 LDAP departmentNumber） |
| phone | CharField | 电话 |
| avatar | URLField | 头像 URL |
| created_at | DateTimeField | 创建时间 |
| updated_at | DateTimeField | 更新时间 |

## Celery 任务

### account.tasks.sync_ldap_users_task

定期同步 LDAP 用户和组织架构。

```python
from account.tasks import sync_all_ldap_users_and_groups

# 手动触发全量同步
result = sync_all_ldap_users_and_groups()
print(result)
```

## 设置定时任务

LDAP 用户同步任务已经在配置中自动添加：

- **任务**: `account.tasks.sync_ldap_users_task`
- **频率**: 每小时执行一次
- **功能**: 同步 LDAP 用户和组到本地数据库

如需修改频率，编辑 `config/settings/default.py` 中的 `CELERY_BEAT_SCHEDULE`。

## LDAP 认证说明

### 启用 LDAP

LDAP 认证是可选的。要启用它:

1. 安装 LDAP 依赖:
   ```bash
   uv sync --extra ldap
   ```

2. 配置 LDAP 环境变量 (见上文)

3. 重启 Django 应用

### 禁用 LDAP

如果不需要 LDAP，系统会自动退回到 Django 的默认认证系统。用户可以通过 Django Admin 创建和管理。


## 管理后台

访问 `http://localhost:8000/admin/` 使用管理后台:

- 管理第三方系统配置
- 查看同步记录
- 查看同步的数据项
- 配置 Celery 定时任务

## 开发建议

### 添加新的第三方系统

1. 在 Admin 后台创建 `ThirdPartySystem` 记录
2. 修改 `sync_manager/tasks.py` 中的 `sync_third_party_data` 函数
3. 替换 mock 数据为实际的 API 调用:

```python
import requests

response = requests.get(
    system.api_url,
    headers={'Authorization': f'Bearer {system.api_key}'},
    timeout=30
)
data = response.json()

for item in data:
    DataItem.objects.update_or_create(
        system=system,
        external_id=item['id'],
        defaults={
            'name': item['name'],
            'status': item['status'],
            'data': item
        }
    )
```

### 自定义数据模型

根据实际需求修改 `DataItem` 模型:

```python
class DataItem(models.Model):
    # 添加你自己的字段
    custom_field = models.CharField(max_length=100)
    another_field = models.IntegerField()
    # ...
```

运行迁移:

```bash
uv run python manage.py makemigrations
uv run python manage.py migrate
```

## 故障排除

### MySQL 连接错误

确保 MySQL 服务正在运行，并且配置的用户有权限访问数据库:

```sql
GRANT ALL PRIVILEGES ON network_manager.* TO 'your_user'@'localhost';
FLUSH PRIVILEGES;
```

### Redis 连接错误

确保 Redis 服务正在运行:

```bash
# Windows
redis-server

# Linux
sudo systemctl start redis
```

### Celery 任务不执行

1. 确保 Celery Worker 正在运行
2. 检查 Redis 连接
3. 查看 Celery 日志输出

### LDAP 认证失败

1. 检查 LDAP 服务器是否可访问
2. 验证 bind DN 和密码是否正确
3. 确认用户搜索基础 DN 配置正确
4. 查看详细日志（LDAP 后端会输出 DEBUG 级别日志）

## 相关文档

- **[架构说明](docs/ARCHITECTURE.md)** - 系统架构和设计文档
- **[LDAP 映射](docs/LDAP_MAPPING.md)** - LDAP 属性映射说明
- **[实现文档](docs/IMPLEMENTATION.md)** - 实现细节和技术说明
- **[快速开始](docs/QUICKSTART.md)** - 快速入门指南

## 许可证

MIT License
