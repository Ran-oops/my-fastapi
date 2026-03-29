# 部署运维文档

> 本文档描述 Enterprise FastAPI 项目的部署配置、运维流程和监控方案。

## 目录

1. [部署架构](#部署架构)
2. [环境准备](#环境准备)
3. [本地部署](#本地部署)
4. [Docker 部署](#docker-部署)
5. [生产环境部署](#生产环境部署)
6. [配置管理](#配置管理)
7. [监控与日志](#监控与日志)
8. [常见运维任务](#常见运维任务)

---

## 部署架构

### 开发环境架构

```text
┌─────────────────────────────────────────────────────────────────┐
│                      Development Environment                    │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐                                        │
│  │   FastAPI App       │                                        │
│  │   (uvicorn :8000)   │                                        │
│  └──────────┬──────────┘                                        │
│             │                                                    │
│  ┌──────────┴──────────┬──────────────────┬──────────────────┐  │
│  │      PostgreSQL     │    SQL Server    │      MySQL       │  │
│  │      (localhost)    │    (localhost)   │    (localhost)   │  │
│  └─────────────────────┴──────────────────┴──────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 生产环境架构

```text
┌─────────────────────────────────────────────────────────────────┐
│                      Production Environment                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐                                            │
│  │   Load Balancer │  (Nginx / ALB)                            │
│  │      (HTTPS)    │                                            │
│  └────────┬────────┘                                            │
│           │                                                     │
│  ┌────────┴────────┬─────────────────┐                         │
│  │                 │                 │                          │
│  ▼                 ▼                 ▼                          │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│ │   App #1    │ │   App #2    │ │   App #3    │  (Gunicorn +  │
│ │  (uvicorn)  │ │  (uvicorn)  │ │  (uvicorn)  │   Uvicorn)    │
│ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘               │
│        │               │               │                       │
│        └───────────────┼───────────────┘                       │
│                        │                                        │
│  ┌─────────────────────┼─────────────────────────────────────┐ │
│  │                     │                                     │ │
│  ▼                     ▼                                     │ ▼
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│ │  PostgreSQL │ │  SQL Server │ │    MySQL    │            │
│ │  (Primary)  │ │  (Primary)  │ │  (Read Only)│            │
│ └─────────────┘ └─────────────┘ └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 环境准备

### 系统要求

| 组件   | 最低要求 | 推荐配置 |
| ------ | -------- | -------- |
| Python | 3.13+    | 3.13     |
| 内存   | 512MB    | 2GB+     |
| 磁盘   | 1GB      | 10GB+    |
| CPU    | 1核      | 2核+     |

### 数据库要求

| 数据库     | 版本要求 |
| ---------- | -------- |
| PostgreSQL | 14+      |
| SQL Server | 2019+    |
| MySQL      | 8.0+     |

### 安装 Python

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.13 python3.13-venv

# macOS (Homebrew)
brew install python@3.13

# Windows
# 从 python.org 下载安装
```

### 安装 UV (推荐)

```bash
# Unix/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## 本地部署

### 1. 克隆项目

```bash
git clone https://github.com/example/enterprise-fastapi.git
cd enterprise-fastapi
```

### 2. 安装依赖

```bash
# 使用 UV (推荐)
uv sync
uv sync --dev  # 包含开发依赖

# 或使用 pip
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑配置
# Linux/macOS
vim .env

# Windows
notepad .env
```

### 4. 启动数据库

```bash
# PostgreSQL (Docker)
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=user_db \
  -p 5432:5432 \
  postgres:14

# SQL Server (Docker)
docker run -d \
  --name mssql \
  -e ACCEPT_EULA=Y \
  -e SA_PASSWORD=YourStrong@Password \
  -p 1433:1433 \
  mcr.microsoft.com/mssql/server:2019-latest

# MySQL (Docker)
docker run -d \
  --name mysql \
  -e MYSQL_ROOT_PASSWORD=password \
  -e MYSQL_DATABASE=config_db \
  -p 3306:3306 \
  mysql:8.0
```

### 5. 运行数据库迁移

```bash
# 用户数据库
alembic upgrade head

# 或使用 Makefile
make db-upgrade
```

### 6. 启动应用

```bash
# 使用 just
just run

# 或直接运行
uv run python run.py

# 或使用 uvicorn
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. 验证部署

```bash
# 访问健康检查
curl http://localhost:8000/health

# 访问 API 文档
# http://localhost:8000/api/v1/docs
```

---

## Docker 部署

### Dockerfile

```dockerfile
# Dockerfile
FROM python:3.13-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 安装 Python 依赖
RUN pip install uv && uv sync --no-dev

# 复制应用代码
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# 设置环境变量
ENV PYTHONPATH=/app
ENV APP_ENV=production

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
# docker-compose.yml
version: '3.8'

services:
  # 应用服务
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - APP_ENV=production
      - USER_DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/user_db
      - BUSINESS_DATABASE_URL=mssql+aioodbc://sa:YourStrong@Password@mssql:1433/business_db
      - CONFIG_DATABASE_URL=mysql+aiomysql://root:password@mysql:3306/config_db
    depends_on:
      - postgres
      - mssql
      - mysql
    restart: unless-stopped

  # PostgreSQL
  postgres:
    image: postgres:14
    environment:
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=user_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  # SQL Server
  mssql:
    image: mcr.microsoft.com/mssql/server:2019-latest
    environment:
      - ACCEPT_EULA=Y
      - SA_PASSWORD=YourStrong@Password
    volumes:
      - mssql_data:/var/opt/mssql
    ports:
      - "1433:1433"

  # MySQL
  mysql:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=password
      - MYSQL_DATABASE=config_db
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "3306:3306"

volumes:
  postgres_data:
  mssql_data:
  mysql_data:
```

### Docker 命令

```bash
# 构建镜像
docker build -t enterprise-fastapi .

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f app

# 停止服务
docker-compose down

# 重建并启动
docker-compose up -d --build
```

---

## 生产环境部署

### 使用 Gunicorn + Uvicorn

```bash
# 安装
uv add gunicorn

# 启动命令
gunicorn app.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 4 \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### Systemd 服务配置

```ini
# /etc/systemd/system/enterprise-fastapi.service
[Unit]
Description=Enterprise FastAPI Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/enterprise-fastapi
Environment="PATH=/opt/enterprise-fastapi/.venv/bin"
ExecStart=/opt/enterprise-fastapi/.venv/bin/gunicorn \
    app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 4 \
    --bind 127.0.0.1:8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
# 启用服务
sudo systemctl daemon-reload
sudo systemctl enable enterprise-fastapi
sudo systemctl start enterprise-fastapi

# 查看状态
sudo systemctl status enterprise-fastapi
```

### Nginx 反向代理

```nginx
# /etc/nginx/sites-available/enterprise-fastapi
server {
    listen 80;
    server_name api.example.com;

    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    # SSL 配置
    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
```

---

## 配置管理

### 环境变量

| 变量名                      | 说明           | 默认值      | 必填 |
| --------------------------- | -------------- | ----------- | ---- |
| APP_ENV                     | 运行环境       | development | 否   |
| DEBUG                       | 调试模式       | true        | 否   |
| SECRET_KEY                  | 密钥           | -           | 是   |
| API_V1_STR                  | API 前缀       | /api/v1     | 否   |
| USER_DATABASE_URL           | 用户数据库连接 | -           | 是   |
| BUSINESS_DATABASE_URL       | 业务数据库连接 | -           | 是   |
| CONFIG_DATABASE_URL         | 配置数据库连接 | -           | 是   |
| ACCESS_TOKEN_EXPIRE_MINUTES | Token 过期时间 | 30          | 否   |
| BACKEND_CORS_ORIGINS        | CORS 允许源    | ["*"]       | 否   |

### 配置文件位置

```text
项目根目录/
├── .env                    # 本地开发配置 (不提交)
├── .env.example            # 配置示例
├── .env.production         # 生产环境配置模板
└── pyproject.toml          # 项目配置
```

### 敏感信息管理

```bash
# 生产环境建议使用密钥管理服务
# AWS Secrets Manager
aws secretsmanager get-secret-value --secret-id enterprise-fastapi/prod

# HashiCorp Vault
vault kv get secret/enterprise-fastapi

# Kubernetes Secrets
kubectl get secret enterprise-fastapi-secrets -o yaml
```

---

## 监控与日志

### 健康检查端点

```bash
# 基本健康检查
GET /health
# 响应: {"status": "healthy", "timestamp": "...", "version": "1.0.0"}

# 就绪检查
GET /health/ready
# 响应: {"status": "ready", "timestamp": "..."}
```

### 日志配置

```python
# app/core/logging.py
import logging
import sys
from logging.handlers import RotatingFileHandler

def setup_logging():
    # 格式
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # 文件输出
    file_handler = RotatingFileHandler(
        "logs/app.log",
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)

    # 配置根日志
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
```

### 日志级别

| 级别     | 使用场景     |
| -------- | ------------ |
| DEBUG    | 开发调试信息 |
| INFO     | 正常操作日志 |
| WARNING  | 警告信息     |
| ERROR    | 错误信息     |
| CRITICAL | 严重错误     |

### 监控指标

```python
# 建议添加的监控指标
# 1. 请求计数
# 2. 请求延迟
# 3. 错误率
# 4. 数据库连接数
# 5. 内存使用
# 6. CPU 使用
```

---

## 常见运维任务

### 数据库备份

```bash
# PostgreSQL 备份
pg_dump -h localhost -U postgres user_db > backup_user_$(date +%Y%m%d).sql

# PostgreSQL 恢复
psql -h localhost -U postgres user_db < backup_user_20260324.sql

# SQL Server 备份
sqlcmd -S localhost -U sa -Q "BACKUP DATABASE business_db TO DISK = '/backup/business.bak'"

# MySQL 备份
mysqldump -h localhost -u root -p config_db > backup_config_$(date +%Y%m%d).sql
```

### 数据库迁移

```bash
# 生成迁移脚本
alembic revision --autogenerate -m "add new column"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1

# 查看迁移历史
alembic history --verbose
```

### 应用更新

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 更新依赖
uv sync

# 3. 执行数据库迁移
alembic upgrade head

# 4. 重启应用
sudo systemctl restart enterprise-fastapi

# 5. 验证
curl http://localhost:8000/health
```

### 扩容

```bash
# Docker Compose 扩容
docker-compose up -d --scale app=3

# Kubernetes 扩容
kubectl scale deployment enterprise-fastapi --replicas=3
```

### SSL 证书更新

```bash
# Let's Encrypt 自动更新
certbot renew

# 手动更新
certbot certonly --standalone -d api.example.com
```

---

## CI/CD 配置

### GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install UV
        uses: astral-sh/setup-uv@v4

      - name: Install dependencies
        run: uv sync --dev

      - name: Run linter
        run: uv run ruff check app tests

      - name: Run type checker
        run: uv run ty check app

      - name: Run tests
        run: uv run pytest tests -v --cov=app

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to production
        run: |
          # 部署脚本
          echo "Deploying to production..."
```

---

> 文档版本: 1.0.0
> 更新时间: 2026-03-24
