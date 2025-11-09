# 快速开始指南

## 前置要求

1. Python 3.11+
2. MySQL 8.0+
3. Redis 6.0+
4. uv 包管理器

## 安装步骤

### 1. 安装依赖

```bash
# 安装基础依赖
uv sync

# 可选: 安装 LDAP 支持 (需要系统 OpenLDAP 库)
uv sync --extra ldap
```

### 2. 配置数据库

```sql
-- 创建 MySQL 数据库
CREATE DATABASE network_manager CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户并授权
CREATE USER 'network_manager'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON network_manager.* TO 'network_manager'@'localhost';
FLUSH PRIVILEGES;
```

### 3. 配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑 .env 文件,修改数据库密码等配置
# 至少需要修改:
# - DB_PASSWORD
# - DJANGO_SECRET_KEY (生产环境)
```

### 4. 初始化数据库

```bash
# 运行数据库迁移
uv run python manage.py migrate

# 创建超级用户
uv run python manage.py createsuperuser
```

### 5. 启动服务

#### Windows

```bash
# 启动 Django (终端 1)
start_dev.bat

# 启动 Celery Worker (终端 2)
uv run celery -A config worker -l info

# 启动 Celery Beat (终端 3)
uv run celery -A config beat -l info
```

#### Linux/Mac

```bash
# 启动 Django (终端 1)
chmod +x start_dev.sh
./start_dev.sh

# 启动 Celery Worker (终端 2)
uv run celery -A config worker -l info

# 启动 Celery Beat (终端 3)
uv run celery -A config beat -l info
```

## 访问应用

- Django 应用: http://localhost:8000
- 管理后台: http://localhost:8000/admin

## 配置 Celery 定时任务

1. 登录管理后台
2. 导航到 "Periodic tasks" → "Intervals"
3. 创建时间间隔,例如: every 15 minutes
4. 导航到 "Periodic tasks" → "Periodic tasks"
5. 添加任务:
   - Name: "同步所有第三方系统"
   - Task: `sync_manager.tasks.sync_all_active_systems`
   - Interval: 选择刚创建的 15 分钟间隔
   - Enabled: 勾选

## 添加第三方系统

1. 登录管理后台
2. 导航到 "Sync Manager" → "Third party systems"
3. 添加系统:
   - 系统名称: 例如 "第三方API系统"
   - API地址: http://api.example.com/data
   - API密钥: (如果需要)
   - 是否启用: 勾选
   - 同步间隔: 15 (分钟)

## 测试同步

在 Django shell 中测试:

```bash
uv run python manage.py shell
```

```python
# 手动触发同步
from sync_manager.tasks import sync_third_party_data
from sync_manager.models import ThirdPartySystem

# 获取第一个系统
system = ThirdPartySystem.objects.first()

# 触发同步
result = sync_third_party_data.delay(system.id)

# 查看结果
print(result.get())
```

## 切换到生产环境

```bash
# 设置环境变量
export DJANGO_ENV=prod  # Linux/Mac
set DJANGO_ENV=prod     # Windows

# 收集静态文件
uv run python manage.py collectstatic --noinput

# 使用生产服务器 (例如 Gunicorn)
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

## 常见问题

### Q: MySQL 连接失败
A: 检查 MySQL 服务是否运行,用户名密码是否正确

### Q: Redis 连接失败
A: 确保 Redis 服务正在运行: `redis-server`

### Q: Celery 任务不执行
A: 确保 Celery Worker 和 Beat 都在运行

### Q: LDAP 安装失败 (Windows)
A: LDAP 在 Windows 上需要额外的系统库,建议在生产环境(Linux)使用 LDAP

## 更多帮助

查看完整文档: [README.md](README.md)
