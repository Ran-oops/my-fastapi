# Enterprise FastAPI Project

企业级FastAPI项目模板，使用异步操作、多数据库架构和分层架构。

## 项目结构

```text
.
├── .github/                    # GitHub配置
│   └── workflows/              # CI/CD工作流
├── alembic/                    # 数据库迁移
│   ├── user_db/                # 用户数据库迁移
│   ├── business_db/            # 业务数据库迁移
│   └── env.py                  # 主迁移配置
├── app/                        # 主应用目录
│   ├── api/                    # API路由层
│   │   ├── deps.py             # 依赖注入
│   │   └── v1/
│   │       ├── endpoints/      # API端点
│   │       │   ├── auth.py     # 认证端点
│   │       │   └── users.py    # 用户端点
│   │       └── __init__.py     # 路由注册
│   ├── cli/                    # CLI管理命令
│   │   └── commands/           # 命令实现
│   │       ├── fte.py          # FTE计算命令
│   │       ├── data_import.py  # 数据导入命令
│   │       └── qc_report.py    # QC报告命令
│   ├── core/                   # 核心配置
│   │   ├── commands/           # 命令编排器
│   │   ├── config.py           # 应用配置
│   │   ├── exceptions.py       # 自定义异常
│   │   └── security.py         # 安全工具
│   ├── crud/                   # CRUD操作层
│   ├── db/                     # 数据库配置
│   │   ├── base.py             # 多数据库基类
│   │   └── session.py          # 数据库会话
│   ├── models/                 # 数据库模型
│   │   ├── user_db/            # 用户数据库模型
│   │   ├── business_db/        # 业务数据库模型
│   │   └── config_db/          # 配置数据库模型
│   ├── schemas/                # Pydantic模型
│   ├── services/               # 业务逻辑层
│   │   ├── fte.py              # FTE计算服务
│   │   ├── data_import.py      # 数据导入服务
│   │   └── qc_report.py        # QC报告服务
│   └── main.py                 # 应用入口
├── tests/                      # 测试目录
├── manage.py                   # CLI管理入口
├── run.py                      # 应用启动脚本
├── pyproject.toml              # 项目配置 (PEP 621)
├── ruff.toml                   # Ruff配置
├── ty.json                     # Ty类型检查配置
├── .rumdlrc                    # Markdown lint配置
├── .pre-commit-config.yaml     # Pre-commit hooks
├── Makefile                    # 常用命令
└── README.md                   # 项目文档
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

| 数据库 | 类型 | 用途 | 访问模式 |
|--------|------|------|----------|
| 用户数据库 | PostgreSQL | 用户认证、角色、权限 | 读写 |
| 业务数据库 | SQL Server | 订单、产品、业务数据 | 读写 |
| 配置数据库 | MySQL | 系统配置、字典数据 | 只读 |

## 快速开始

### 前置要求

- Python 3.13+
- uv (推荐) 或 pip

### 1. 安装依赖

使用 uv (推荐):

```bash
# 安装uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装依赖
uv sync

# 安装开发依赖
uv sync --dev
```

使用 pip:

```bash
pip install -r requirements.txt
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
# 使用Makefile
make db-upgrade

# 或手动执行
alembic upgrade head
```

### 4. 启动应用

```bash
# 使用Makefile
make run

# 或手动执行
uv run python run.py
```

## API文档

- Swagger UI: <http://localhost:8000/api/v1/docs>
- ReDoc: <http://localhost:8000/api/v1/redoc>

## CLI管理命令

### FTE计算命令

```bash
# 执行完整FTE计算流程（编排命令）
uv run python manage.py fte calculate --force

# 单独执行子命令
uv run python manage.py fte import-task-listing --dry-run
uv run python manage.py fte import-geographic-ssu
uv run python manage.py fte calculate-country
uv run python manage.py fte calculate-site
uv run python manage.py fte calculate-subregion
uv run python manage.py fte final-forecast
```

### 数据导入命令

```bash
uv run python manage.py import all-data --source <source_id>
uv run python manage.py import validate --source <source_id>
```

### QC报告命令

```bash
uv run python manage.py qc generate --type daily --start 2024-01-01 --end 2024-01-31
uv run python manage.py qc list --type daily --limit 10
```

### 查看帮助

```bash
uv run python manage.py --help
uv run python manage.py fte --help
uv run python manage.py qc --help
```

## 开发工具

### 代码质量检查

```bash
# 运行所有检查 (lint + test)
make check

# 仅运行linting
make lint

# 格式化代码
make format

# 运行测试
make test
```

### Pre-commit Hooks

```bash
# 安装pre-commit hooks
uvx prek install

# 手动运行所有hooks
uvx prek run --all-files
```

### 使用Makefile

```bash
make help       # 显示所有可用命令
make install    # 安装生产依赖
make dev        # 安装开发依赖
make test       # 运行测试
make lint       # 运行linting
make format     # 格式化代码
make check      # 运行所有检查
make clean      # 清理缓存文件
make run        # 启动应用
make cli        # 显示CLI帮助
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
# 使用Makefile
make test

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
- 密码使用bcrypt加密（限制72字节）
- 密码强度要求：至少8字符，包含字母和数字
- 生产环境请更换 `SECRET_KEY`

## 开发说明

### 添加新的CLI命令

1. 在 `app/services/` 创建服务方法
2. 在 `app/cli/commands/` 创建命令文件
3. 在 `app/cli/__init__.py` 注册命令

### 添加新的数据库模型

1. 在 `app/models/<db_name>/` 创建模型
2. 在 `app/db/session.py` 添加会话工厂
3. 创建对应的Alembic迁移

### 添加新的依赖

```bash
# 添加运行时依赖
uv add <package>

# 添加开发依赖
uv add --dev <package>
```

## 项目配置文件

| 文件 | 用途 |
|------|------|
| `pyproject.toml` | 项目元数据、依赖、工具配置 (PEP 621) |
| `ruff.toml` | Ruff linter和formatter配置 |
| `ty.toml` | Ty类型检查器配置 |
| `.rumdl.toml` | Markdown lint配置 |
| `.pre-commit-config.yaml` | Pre-commit hooks配置 |
| `Makefile` | 常用命令快捷方式 |
| `uv.toml` | UV包管理器配置 |

## License

MIT
