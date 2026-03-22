# Enterprise FastAPI Project

企业级FastAPI项目模板，使用异步操作和分层架构。

## 项目结构

```
.
├── alembic/              # 数据库迁移
├── app/                  # 主应用目录
│   ├── api/              # API路由层
│   ├── core/             # 核心配置
│   ├── crud/             # CRUD操作层
│   ├── db/               # 数据库配置
│   ├── models/           # 数据库模型
│   ├── schemas/          # Pydantic模型
│   ├── services/         # 业务逻辑层
│   └── main.py           # 应用入口
├── tests/                # 测试目录
├── requirements.txt      # 依赖
└── README.md            # 项目文档
```

## 技术栈

- **FastAPI**: 高性能异步Web框架
- **SQLAlchemy 2.0**: ORM工具，支持异步操作
- **Pydantic V2**: 数据验证和序列化
- **Alembic**: 数据库迁移
- **Pytest**: 异步测试框架
- **SQL Server**: 企业级关系数据库

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

### 3. 配置SQL Server连接

编辑 `.env`:
```bash
DATABASE_URL=mssql+aioodbc://username:password@host:port/dbname?driver=ODBC+Driver+17+for+SQL+Server
```

### 4. 运行迁移

```bash
alembic upgrade head
```

### 5. 启动应用

```bash
python run.py
```

## API文档

- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## 运行测试

```bash
pytest
```
