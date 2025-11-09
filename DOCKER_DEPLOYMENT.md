# Network Manager - Docker 部署指南

## 快速开始

### 1. 准备环境变量

复制环境变量示例文件并修改配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，修改以下关键配置：

- `DJANGO_SECRET_KEY`: Django 密钥（生产环境必须修改）
- `DB_PASSWORD`: MySQL 数据库密码
- `REDIS_PASSWORD`: Redis 密码
- `IKUAI_BASE_URL`, `IKUAI_USERNAME`, `IKUAI_PASSWORD`: iKuai 路由器配置
- `OPENVPN_SERVER_HOST`: OpenVPN 服务器地址
- `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_PASSWORD`: 管理员账号

### 2. 构建和启动服务

```bash
# 构建镜像
docker-compose build

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 3. 访问应用

- **OpenVPN 管理**: http://localhost:8000/openvpn/
- **Django Admin**: http://localhost:8000/admin/
- **默认管理员账号**: 在 `.env` 文件中配置的 `DJANGO_SUPERUSER_USERNAME` 和 `DJANGO_SUPERUSER_PASSWORD`

### 4. 常用命令

```bash
# 停止服务
docker-compose stop

# 重启服务
docker-compose restart

# 查看服务状态
docker-compose ps

# 查看特定服务日志
docker-compose logs -f web

# 进入容器
docker-compose exec web bash

# 运行 Django 管理命令
docker-compose exec web python manage.py shell
docker-compose exec web python manage.py createsuperuser

# 查看 Supervisor 进程状态
docker-compose exec web supervisorctl status

# 重启某个进程
docker-compose exec web supervisorctl restart django
docker-compose exec web supervisorctl restart celery-worker
docker-compose exec web supervisorctl restart celery-beat
```

## 架构说明

### 服务组成

1. **web**: Django + Celery (通过 Supervisor 管理)
   - Django Web Server (端口 8000)
   - Celery Worker (异步任务处理)
   - Celery Beat (定时任务调度)

2. **db**: MySQL 8.0 数据库

3. **redis**: Redis 7 (用于缓存和 Celery 消息队列)

### Supervisor 进程管理

所有 Python 进程由 Supervisor 统一管理，配置文件：`supervisord.conf`

进程列表：
- `django`: Django Web 服务器
- `celery-worker`: Celery 异步任务处理器
- `celery-beat`: Celery 定时任务调度器

## 生产环境部署

### 1. 安全配置

修改 `.env` 文件中的敏感信息：

```env
DJANGO_SECRET_KEY=<生成一个复杂的随机密钥>
DJANGO_ENV=prod
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# 使用强密码
DB_PASSWORD=<强密码>
REDIS_PASSWORD=<强密码>
```

生成 Django Secret Key：

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 2. 使用外部数据库

如果使用外部 MySQL 数据库，修改 `.env`:

```env
DB_HOST=your-mysql-host.com
DB_PORT=3306
DB_NAME=network_manager
DB_USER=your_db_user
DB_PASSWORD=your_db_password
```

然后移除 `docker-compose.yml` 中的 `db` 服务。

### 3. 配置 Nginx 反向代理

创建 `nginx.conf`:

```nginx
upstream django {
    server web:8000;
}

server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /app/staticfiles/;
    }

    location /media/ {
        alias /app/media/;
    }
}
```

在 `docker-compose.yml` 中添加 Nginx 服务：

```yaml
  nginx:
    image: nginx:alpine
    container_name: network_manager_nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    depends_on:
      - web
    networks:
      - network_manager_net
```

### 4. 持久化数据

确保数据卷正确配置：

```yaml
volumes:
  mysql_data:      # 数据库数据
  redis_data:      # Redis 数据
  static_volume:   # 静态文件
  media_volume:    # 用户上传文件
  logs_volume:     # 日志文件
```

### 5. 备份策略

#### 备份数据库

```bash
# 导出数据库
docker-compose exec db mysqldump -u root -p${DB_PASSWORD} ${DB_NAME} > backup_$(date +%Y%m%d_%H%M%S).sql

# 恢复数据库
docker-compose exec -T db mysql -u root -p${DB_PASSWORD} ${DB_NAME} < backup.sql
```

#### 备份 Redis

```bash
# 触发 Redis 保存
docker-compose exec redis redis-cli -a ${REDIS_PASSWORD} SAVE

# 复制 RDB 文件
docker cp network_manager_redis:/data/dump.rdb ./redis_backup_$(date +%Y%m%d_%H%M%S).rdb
```

## 故障排查

### 查看日志

```bash
# 所有服务日志
docker-compose logs -f

# Django 日志
docker-compose exec web tail -f /var/log/supervisor/django.log

# Celery Worker 日志
docker-compose exec web tail -f /var/log/supervisor/celery-worker.log

# Celery Beat 日志
docker-compose exec web tail -f /var/log/supervisor/celery-beat.log
```

### 常见问题

1. **数据库连接失败**
   - 检查 `.env` 中的数据库配置
   - 确认数据库服务已启动：`docker-compose ps`
   - 查看数据库日志：`docker-compose logs db`

2. **Redis 连接失败**
   - 检查 Redis 密码配置
   - 确认 Redis 服务已启动
   - 查看 Redis 日志：`docker-compose logs redis`

3. **Celery 任务不执行**
   - 检查 Celery Worker 状态：`docker-compose exec web supervisorctl status celery-worker`
   - 重启 Worker：`docker-compose exec web supervisorctl restart celery-worker`
   - 查看 Worker 日志

4. **静态文件不显示**
   - 运行 collectstatic：`docker-compose exec web python manage.py collectstatic --noinput`
   - 检查 Nginx 配置中的静态文件路径

## 性能优化

### 1. Celery Worker 并发数

修改 `supervisord.conf` 中的并发数：

```ini
[program:celery-worker]
command=celery -A config worker -l info --concurrency=8
```

### 2. 数据库连接池

在 Django settings 中配置：

```python
DATABASES = {
    'default': {
        # ...
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        },
        'CONN_MAX_AGE': 600,  # 连接池
    }
}
```

### 3. Redis 优化

修改 Redis 配置（`docker-compose.yml`）：

```yaml
redis:
  command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru --requirepass ${REDIS_PASSWORD}
```

## 监控和维护

### 1. 健康检查

所有服务都配置了 healthcheck，使用以下命令检查：

```bash
docker-compose ps
```

### 2. 资源监控

```bash
# 查看资源使用情况
docker stats

# 查看特定容器
docker stats network_manager_web
```

### 3. 定期维护

```bash
# 清理无用的 Docker 资源
docker system prune -a

# 清理无用的卷
docker volume prune
```

## 更新和升级

```bash
# 1. 拉取最新代码
git pull

# 2. 重新构建镜像
docker-compose build --no-cache

# 3. 停止旧服务
docker-compose down

# 4. 启动新服务
docker-compose up -d

# 5. 运行迁移
docker-compose exec web python manage.py migrate
```

## 扩展配置

### 使用 Docker Swarm 或 Kubernetes

对于更大规模的部署，可以考虑：

1. **Docker Swarm**: 将 `docker-compose.yml` 转换为 stack 文件
2. **Kubernetes**: 创建 Deployment、Service、ConfigMap 等资源

### CI/CD 集成

示例 GitHub Actions workflow:

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build and push Docker image
        run: |
          docker build -t myregistry/network_manager:latest .
          docker push myregistry/network_manager:latest
      - name: Deploy to server
        run: |
          ssh user@server 'cd /app && docker-compose pull && docker-compose up -d'
```

## 技术支持

如有问题，请查看：
- 项目文档：`docs/`
- 日志文件：`/var/log/supervisor/`
- GitHub Issues
