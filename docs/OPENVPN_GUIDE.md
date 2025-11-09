# OpenVPN 账号管理系统

## 功能概述

这是一个基于 Django 的 OpenVPN 账号管理系统，与 iKuai 路由器集成，实现了：

- **自动化账号管理**：用户可以自助申请、续期和管理 OpenVPN 账号
- **异步任务处理**：使用 Celery 异步创建账号，避免阻塞用户操作
- **状态同步**：定期同步 iKuai 系统的账号状态
- **配置文件生成**：自动生成 .ovpn 配置文件供用户下载
- **美观的 UI**：绿色主题的现代化界面，响应式设计

## 系统架构

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   用户界面   │ ───> │  Django 后端  │ ───> │  iKuai API  │
│  (前端页面)  │      │  (Views/API) │      │  (路由器)   │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │ Celery 任务   │
                     │  (异步处理)   │
                     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   Redis      │
                     │ (消息队列)    │
                     └──────────────┘
```

## 数据库模型

### OpenVPNAccount 模型

核心字段：
- `user`: OneToOne 关系到 Django User
- `username`: VPN 账号用户名
- `password`: VPN 账号密码
- `status`: 账号状态（creating/active/expired/disabled/failed）
- `ikuai_id`: iKuai 系统中的账号 ID
- `expires`: 账号过期时间
- `ip_addr`: 分配的 VPN IP 地址

## 安装和配置

### 1. 安装依赖

项目需要 `requests` 库来调用 iKuai API：

```bash
pip install requests
```

或者使用 uv（如果项目使用 uv 管理依赖）：

```bash
uv pip install requests
```

### 2. 配置环境变量

复制配置示例：

```bash
cp .env.openvpn.example .env
```

编辑 `.env` 文件，填入实际配置：

```env
# iKuai 路由器配置
IKUAI_BASE_URL=http://192.168.1.1
IKUAI_USERNAME=admin
IKUAI_PASSWORD=your_password

# OpenVPN 服务器配置
OPENVPN_SERVER_HOST=vpn.yourdomain.com
OPENVPN_SERVER_PORT=1194
OPENVPN_PROTOCOL=udp
```

### 3. 运行数据库迁移

```bash
python manage.py makemigrations sync_manager
python manage.py migrate
```

### 4. 启动服务

启动 Django 服务：

```bash
python manage.py runserver
```

启动 Celery Worker（另开终端）：

```bash
celery -A config worker -l info
```

启动 Celery Beat（定时任务，另开终端）：

```bash
celery -A config beat -l info
```

或者使用项目提供的启动脚本：

```bash
# Windows
start_dev.bat

# Linux/Mac
./start_dev.sh
```

## 使用说明

### 用户端操作

1. **登录系统**
   - 使用系统账号登录
   - 访问 `/openvpn/` 进入 OpenVPN 管理页面

2. **申请账号**
   - 点击"申请账号"按钮
   - 选择账号有效期（30/60/90/180/365 天）
   - 提交申请，系统将异步创建账号

3. **查看账号状态**
   - 创建中：显示进度，自动轮询状态
   - 创建成功：显示账号信息和操作按钮
   - 创建失败：显示错误信息，可重试

4. **下载配置文件**
   - 账号激活后，点击"下载配置文件"
   - 获得 `.ovpn` 配置文件
   - 在 OpenVPN 客户端导入使用

5. **续期账号**
   - 账号即将过期时会有提醒
   - 点击"续期账号"延长有效期

6. **删除账号**
   - 不再使用时可删除账号
   - 同时会从 iKuai 系统中移除

### 管理员操作

访问 Django Admin (`/admin/`)：

1. **查看所有账号**
   - 列表显示所有用户的 OpenVPN 账号
   - 可按状态、过期时间筛选
   - 支持搜索用户名、IP 等

2. **批量操作**
   - 同步账号状态
   - 批量启用/禁用账号

3. **查看详细信息**
   - 连接历史
   - 流量使用情况
   - 错误日志

## 界面展示

### 主要功能页面

1. **首页仪表盘**
   - 绿色主题设计
   - 账号状态卡片
   - 使用指南

2. **账号信息展示**
   - 状态徽章（正常/创建中/已过期）
   - 网格布局显示账号详情
   - 进度条显示剩余时效

3. **操作按钮**
   - 大按钮设计，易于点击
   - 图标 + 文字说明
   - 悬停动画效果

4. **模态对话框**
   - 申请账号表单
   - 续期账号表单
   - 现代化设计

## API 接口

### 账号状态 API

```
GET /openvpn/status/
```

返回当前用户的账号状态（用于前端轮询）。

响应示例：

```json
{
    "success": true,
    "status": "active",
    "username": "vpn_john",
    "password": "abc12345",
    "expires": "2024-12-31T23:59:59Z",
    "days_until_expiry": 45,
    "is_active": true,
    "ip_addr": "10.100.250.5"
}
```

### 创建账号 API

```
POST /openvpn/create/
```

参数：
- `expires_days`: 有效期天数（可选，默认 30）
- `password`: 自定义密码（可选，不提供则自动生成）

### 续期账号 API

```
POST /openvpn/renew/
```

参数：
- `extends_days`: 延长天数（可选，默认 30）

### 下载配置文件

```
GET /openvpn/download/
```

返回 `.ovpn` 配置文件。

### 删除账号 API

```
POST /openvpn/delete/
```

删除当前用户的账号。

## Celery 任务

### 创建账号任务

```python
create_openvpn_account(user_id, username, password, expires_days=30)
```

- 异步创建 iKuai 账号
- 自动重试（最多 3 次）
- 失败时更新状态和错误信息

### 同步账号状态任务

```python
sync_openvpn_accounts()
```

- 定时任务，每 10 分钟执行
- 从 iKuai 同步所有账号的最新状态
- 更新连接时间、IP 地址等信息

### 检查过期账号任务

```python
check_expired_accounts()
```

- 定时任务，每天 0 点执行
- 标记已过期的账号
- 发送过期通知（可扩展）

## 定制化

### 修改主题颜色

编辑 `templates/sync_manager/openvpn_dashboard.html`，修改 CSS 变量：

```css
:root {
    --primary-green: #10b981;  /* 主色调 */
    --primary-green-dark: #059669;  /* 深色 */
    --primary-green-light: #34d399;  /* 浅色 */
    /* ... */
}
```

### 自定义 OVPN 模板

编辑 `templates/sync_manager/openvpn_config.ovpn`：

- 修改服务器地址、端口
- 添加证书信息
- 调整连接参数

### 扩展账号创建流程

在 `sync_manager/tasks.py` 的 `create_openvpn_account` 任务中：

- 添加额外的验证逻辑
- 集成其他系统（如计费、审批）
- 发送通知（邮件、短信）

## iKuai API 说明

本系统使用 iKuai 路由器的 PPTP/L2TP 用户管理 API：

### API 端点

- **登录**: `POST /Action/login`
- **操作**: `POST /Action/call`

### 支持的操作

- `add`: 添加账号
- `edit`: 编辑账号
- `del`: 删除账号
- `show`: 查询账号列表

### 返回格式

```json
{
    "Result": 30000,  // 30000 表示成功
    "ErrMsg": "Success",
    "Data": { /* 数据 */ }
}
```

## 故障排查

### 账号创建失败

1. 检查 iKuai API 配置是否正确
2. 查看 Celery Worker 日志
3. 确认 iKuai 路由器网络连通性
4. 检查 Redis 是否正常运行

### 配置文件无法下载

1. 确认账号状态为 active
2. 检查 OPENVPN_CONFIG 配置
3. 确认模板文件存在

### 定时任务不执行

1. 确认 Celery Beat 进程正在运行
2. 检查 Django Admin 的定时任务配置
3. 查看 Celery Beat 日志

## 安全建议

1. **密码安全**
   - 使用强密码策略
   - 定期更新账号密码
   - 在生产环境加密存储密码

2. **网络安全**
   - iKuai API 应在内网访问
   - 使用 HTTPS 访问管理界面
   - 限制 API 访问 IP

3. **权限控制**
   - 普通用户只能管理自己的账号
   - 管理员可查看所有账号
   - 审计账号操作日志

## 技术栈

- **后端**: Django 4.2+
- **任务队列**: Celery + Redis
- **数据库**: MySQL / PostgreSQL / SQLite
- **前端**: HTML5 + CSS3 + JavaScript (原生)
- **API 调用**: requests 库

## 未来扩展

- [ ] 账号申请审批流程
- [ ] 邮件/短信通知
- [ ] 流量统计和报表
- [ ] 多租户支持
- [ ] API 接口文档（Swagger）
- [ ] 移动端适配
- [ ] 二次认证（2FA）

## 许可证

[项目许可证信息]

## 联系方式

如有问题或建议，请联系系统管理员。
