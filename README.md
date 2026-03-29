# Enterprise FastAPI Project

企业级FastAPI项目模板，使用异步操作、多数据库架构和领域驱动设计(DDD)。

## 项目结构

```text
app/
├── modules/                    # 业务领域模块
│   ├── users/                  # 用户领域
│   │   ├── models.py           # SQLAlchemy 模型
│   │   ├── schemas.py          # Pydantic schemas
│   │   ├── repository.py       # 数据访问层
│   │   ├── service.py          # 业务逻辑层
│   │   └── router.py           # API 路由
│   ├── roles/                  # 角色权限领域
│   │   ├── models.py           # Role, Permission 模型
│   │   ├── schemas.py          # 数据验证
│   │   ├── repository.py       # 数据访问
│   │   ├── service.py          # 业务逻辑
│   │   └── router.py           # API 路由
│   └── shared/                 # 共享基础设施
│       ├── db.py               # SQLAlchemy Base, CRUDBase, Sessions
│       └── schemas.py          # 通用响应模型
├── api/                        # API 基础设施
│   ├── deps.py                 # 依赖注入
│   └── v1/                     # API v1 路由注册
├── cli/                        # CLI 命令
│   └── commands/               # 命令实现
│       ├── roles.py            # 角色管理命令
│       └── permissions.py      # 权限管理命令
├── core/                       # 核心配置
│   ├── config.py               # 应用配置
│   ├── security.py             # 安全工具 (JWT, 密码)
│   └── exceptions.py           # 自定义异常
└── main.py                     # 应用入口
```

## 技术栈

### 核心框架

- **FastAPI**: 高性能异步Web框架
- **SQLAlchemy 2.0**: ORM工具，支持异步操作
- **Pydantic V2**: 数据验证和序列化
- **Alembic**: 数据库迁移
- **Typer**: CLI命令管理框架

### 开发工具

- **uv**: 极速Python包管理器
- **just**: 命令运行器(替代 Makefile)
- **ruff**: 极速Python linter和formatter
- **ty**: Astral出品的类型检查器
- **rumdl**: Markdown linter
- **pre-commit**: Git hooks自动化

### 测试工具

- **pytest**: 异步测试框架
- **pytest-asyncio**: 异步测试支持
- **pytest-cov**: 测试覆盖率

## 多数据库架构

项目支持三个独立数据库：

| 数据库     | 类型       | 用途                 | 访问模式 |
| ---------- | ---------- | -------------------- | -------- |
| 用户数据库 | PostgreSQL | 用户认证、角色、权限 | 读写     |
| 业务数据库 | SQL Server | 订单、产品、业务数据 | 读写     |
| 配置数据库 | MySQL      | 系统配置、字典数据   | 只读     |

## 快速开始

### 前置要求

- Python 3.13+
- uv (推荐) 或 pip
- just (命令运行器)

### 1. 安装依赖

```bash
# 安装uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装just
cargo install just

# 安装依赖
uv sync

# 安装开发依赖
uv sync --dev
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 配置数据库连接：

```bash
# 用户数据库 - PostgreSQL
USER_DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/user_db

# 业务数据库 - SQL Server
BUSINESS_DATABASE_URL=mssql+aioodbc://sa:password@localhost:1433/business_db?driver=ODBC+Driver+17+for+SQL+Server

# 配置数据库 - MySQL (只读)
CONFIG_DATABASE_URL=mysql+aiomysql://root:password@localhost:3306/config_db
```

### 3. 运行数据库迁移

```bash
# 使用just
just db-upgrade

# 或手动执行
alembic upgrade head
```

### 4. 启动应用

```bash
# 使用just
just run

# 或手动执行
uv run python run.py
```

## API文档

- Swagger UI: <http://localhost:8000/api/v1/docs>
- ReDoc: <http://localhost:8000/api/v1/redoc>

## CLI管理命令

### 角色管理

```bash
# 列出所有角色
just cli roles list

# 创建角色
just cli roles create --name admin --description "Administrator"

# 为用户分配角色
just cli roles assign --user-id 1 --role-id 1
```

### 权限管理

```bash
# 列出所有权限
just cli permissions list

# 创建权限
just cli permissions create --name "Read Users" --code users:read

# 检查用户权限
just cli permissions check --user-id 1 --code users:read
```

### 其他命令

```bash
# FTE计算(占位)
just cli calculate-fte

# 数据导入(占位)
just cli import-data --source <source>

# QC报告(占位)
just cli qc-report --type daily
```

## 开发工具

### 使用 Just

```bash
just                  # 显示所有可用命令
just sync             # 同步依赖
just dev              # 安装开发依赖
just test             # 运行测试
just lint             # 运行linting
just fmt              # 格式化代码
just ruff             # 运行所有检查
just clean            # 清理缓存文件
just run              # 启动应用
just cli              # 显示CLI帮助
```

### 代码质量检查

```bash
# 运行所有检查 (lint + test)
just lint
just test

# 仅运行linting
just lint

# 格式化代码
just fmt

# 运行测试
just test
```

### Pre-commit Hooks

```bash
# 安装pre-commit hooks
just init

# 手动运行所有hooks
just pre-commit
```

### UV常用命令

```bash
uv sync              # 安装所有依赖
uv sync --dev        # 安装开发依赖
uv add <package>     # 添加依赖
uv add --dev <pkg>   # 添加开发依赖
uv remove <package>  # 移除依赖
uv lock              # 更新锁文件
uv run <command>     # 在虚拟环境中运行命令
uv pip list          # 列出已安装包
```

### Ruff命令

```bash
# 检查代码问题
uvx ruff check app tests

# 自动修复问题
uvx ruff check --fix app tests

# 格式化代码
uvx ruff format app tests
```

### Ty类型检查

```bash
# 运行类型检查
uvx ty check app
```

### Markdown检查

```bash
# 检查Markdown文件
uvx rumdl README.md

# 自动修复
uvx rumdl --fix README.md
```

## 运行测试

```bash
# 使用just
just test

# 或手动执行
uv run pytest tests -v --cov=app --cov-report=term-missing
```

## CI/CD

项目配置了GitHub Actions工作流，自动运行：

- Ruff linting和格式化
- Ty类型检查
- Pytest测试
- Markdown lint

## 安全说明

- JWT Token 默认30分钟过期
- 密码使用bcrypt加密(限制72字节)
- 密码强度要求：至少8字符，包含字母和数字
- 生产环境请更换 `SECRET_KEY`

## 开发说明

### 添加新的领域模块

1. 在 `app/modules/` 创建新目录(如 `orders/`)
2. 创建以下文件：
    - `models.py` - SQLAlchemy 模型
    - `schemas.py` - Pydantic schemas
    - `repository.py` - 数据访问层
    - `service.py` - 业务逻辑层
    - `router.py` - API 路由
3. 在 `app/api/v1/__init__.py` 注册路由

### 添加新的依赖

```bash
# 添加运行时依赖
uv add <package>

# 添加开发依赖
uv add --dev <package>
```

## 项目配置文件

| 文件                      | 用途                                 |
| ------------------------- | ------------------------------------ |
| `pyproject.toml`          | 项目元数据、依赖、工具配置 (PEP 621) |
| `ruff.toml`               | Ruff linter和formatter配置           |
| `ty.toml`                 | Ty类型检查器配置                     |
| `.rumdl.toml`             | Markdown lint配置                    |
| `.pre-commit-config.yaml` | Pre-commit hooks配置                 |
| `justfile`                | 常用命令快捷方式                     |
| `uv.toml`                 | UV包管理器配置                       |

## License

MIT
