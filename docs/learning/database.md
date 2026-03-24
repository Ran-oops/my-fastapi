# 数据库设计文档

> 本文档描述 Enterprise FastAPI 项目的多数据库架构、表结构设计和迁移管理。

## 目录

1. [数据库架构概览](#数据库架构概览)
2. [用户数据库 (PostgreSQL)](#用户数据库-postgresql)
3. [业务数据库 (SQL Server)](#业务数据库-sql-server)
4. [配置数据库 (MySQL)](#配置数据库-mysql)
5. [表关系图](#表关系图)
6. [数据库迁移](#数据库迁移)
7. [连接配置](#连接配置)
8. [最佳实践](#最佳实践)

---

## 数据库架构概览

### 数据库分区策略

本项目使用 **多数据库架构**，将不同业务域的数据存储在不同的数据库中：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           应用层 (FastAPI)                               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                 ┌──────────────────┼──────────────────┐
                 ▼                  ▼                  ▼
    ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐
    │   User Database    │  │ Business Database  │  │  Config Database   │
    │    PostgreSQL      │  │    SQL Server      │  │      MySQL         │
    ├────────────────────┤  ├────────────────────┤  ├────────────────────┤
    │  用户认证和权限    │  │   业务数据管理     │  │   系统配置数据     │
    │                    │  │                    │  │                    │
    │ • users            │  │ • orders           │  │ • (未来扩展)       │
    │ • roles            │  │ • order_items      │  │                    │
    │ • permissions      │  │ • products         │  │                    │
    │ • user_roles       │  │                    │  │                    │
    │ • role_permissions │  │                    │  │                    │
    ├────────────────────┤  ├────────────────────┤  ├────────────────────┤
    │   Read / Write     │  │   Read / Write     │  │     Read Only      │
    └────────────────────┘  └────────────────────┘  └────────────────────┘
```

### 分区原因

| 数据库 | 分区理由 |
|--------|----------|
| User DB | 用户数据敏感，需要独立的安全策略和备份方案 |
| Business DB | 业务数据量大，需要独立的性能优化 |
| Config DB | 配置数据只读，可被多个服务共享 |

---

## 用户数据库 (PostgreSQL)

### 连接配置

```
数据库类型: PostgreSQL 14+
驱动: asyncpg
访问模式: Read/Write
连接池: pool_size=5, max_overflow=10
```

### 表结构

#### users 表

存储用户基本信息。

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    full_name VARCHAR(200),
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    is_superuser BOOLEAN DEFAULT false NOT NULL,
    created_at TIMESTAMP DEFAULT now() NOT NULL,
    updated_at TIMESTAMP DEFAULT now() NOT NULL
);

CREATE INDEX ix_users_email ON users(email);
CREATE INDEX ix_users_username ON users(username);
```

**字段说明**:

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO | 主键，自增 |
| email | VARCHAR(255) | UNIQUE, NOT NULL | 邮箱，唯一 |
| username | VARCHAR(100) | UNIQUE, NOT NULL | 用户名，唯一 |
| full_name | VARCHAR(200) | NULL | 全名，可选 |
| hashed_password | VARCHAR(255) | NOT NULL | bcrypt 哈希密码 |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | 是否激活 |
| is_superuser | BOOLEAN | NOT NULL, DEFAULT false | 是否超级管理员 |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL | 更新时间 |

#### roles 表

存储角色信息。

```sql
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT now() NOT NULL,
    updated_at TIMESTAMP DEFAULT now() NOT NULL
);

CREATE INDEX ix_roles_name ON roles(name);
```

**字段说明**:

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO | 主键 |
| name | VARCHAR(100) | UNIQUE, NOT NULL | 角色名称 |
| description | VARCHAR(255) | NULL | 角色描述 |

#### permissions 表

存储权限信息。

```sql
CREATE TABLE permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    code VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT now() NOT NULL,
    updated_at TIMESTAMP DEFAULT now() NOT NULL
);

CREATE INDEX ix_permissions_name ON permissions(name);
CREATE INDEX ix_permissions_code ON permissions(code);
```

**字段说明**:

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO | 主键 |
| name | VARCHAR(100) | UNIQUE, NOT NULL | 权限名称 |
| code | VARCHAR(100) | UNIQUE, NOT NULL | 权限代码 |
| description | VARCHAR(255) | NULL | 权限描述 |

#### user_roles 关联表

用户和角色的多对多关联。

```sql
CREATE TABLE user_roles (
    user_id INTEGER REFERENCES users(id) PRIMARY KEY,
    role_id INTEGER REFERENCES roles(id) PRIMARY KEY
);
```

#### role_permissions 关联表

角色和权限的多对多关联。

```sql
CREATE TABLE role_permissions (
    role_id INTEGER REFERENCES roles(id) PRIMARY KEY,
    permission_id INTEGER REFERENCES permissions(id) PRIMARY KEY
);
```

---

## 业务数据库 (SQL Server)

### 连接配置

```
数据库类型: SQL Server 2019+
驱动: aioodbc (ODBC Driver 17 for SQL Server)
访问模式: Read/Write
连接池: pool_size=5, max_overflow=10
```

### 表结构

#### orders 表

存储订单信息。

```sql
CREATE TABLE orders (
    id INT IDENTITY(1,1) PRIMARY KEY,
    order_no VARCHAR(50) UNIQUE NOT NULL,
    user_id INT NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    remark NVARCHAR(MAX),
    created_at DATETIME2 DEFAULT GETUTCDATE() NOT NULL,
    updated_at DATETIME2 DEFAULT GETUTCDATE() NOT NULL
);

CREATE INDEX ix_orders_order_no ON orders(order_no);
CREATE INDEX ix_orders_user_id ON orders(user_id);
CREATE INDEX ix_orders_status ON orders(status);
```

**字段说明**:

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, IDENTITY | 主键，自增 |
| order_no | VARCHAR(50) | UNIQUE, NOT NULL | 订单编号 |
| user_id | INT | NOT NULL | 用户ID（外部引用） |
| total_amount | DECIMAL(10,2) | NOT NULL | 订单总金额 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'pending' | 订单状态 |
| remark | NVARCHAR(MAX) | NULL | 备注 |
| created_at | DATETIME2 | NOT NULL | 创建时间 |
| updated_at | DATETIME2 | NOT NULL | 更新时间 |

**订单状态枚举**:

| 状态 | 说明 |
|------|------|
| pending | 待处理 |
| processing | 处理中 |
| completed | 已完成 |
| cancelled | 已取消 |

#### order_items 表

存储订单项信息。

```sql
CREATE TABLE order_items (
    id INT IDENTITY(1,1) PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    total_price DECIMAL(10, 2) NOT NULL,
    created_at DATETIME2 DEFAULT GETUTCDATE() NOT NULL,
    updated_at DATETIME2 DEFAULT GETUTCDATE() NOT NULL
);

CREATE INDEX ix_order_items_order_id ON order_items(order_id);
CREATE INDEX ix_order_items_product_id ON order_items(product_id);
```

**字段说明**:

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, IDENTITY | 主键 |
| order_id | INT | NOT NULL | 订单ID |
| product_id | INT | NOT NULL | 产品ID |
| quantity | INT | NOT NULL | 数量 |
| unit_price | DECIMAL(10,2) | NOT NULL | 单价 |
| total_price | DECIMAL(10,2) | NOT NULL | 小计金额 |

#### products 表

存储产品信息。

```sql
CREATE TABLE products (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(200) NOT NULL,
    sku VARCHAR(50) UNIQUE NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    stock INT DEFAULT 0 NOT NULL,
    is_active BIT DEFAULT 1 NOT NULL,
    created_at DATETIME2 DEFAULT GETUTCDATE() NOT NULL,
    updated_at DATETIME2 DEFAULT GETUTCDATE() NOT NULL
);

CREATE INDEX ix_products_sku ON products(sku);
CREATE INDEX ix_products_name ON products(name);
```

**字段说明**:

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, IDENTITY | 主键 |
| name | NVARCHAR(200) | NOT NULL | 产品名称 |
| sku | VARCHAR(50) | UNIQUE, NOT NULL | SKU编码 |
| price | DECIMAL(10,2) | NOT NULL | 价格 |
| stock | INT | NOT NULL, DEFAULT 0 | 库存数量 |
| is_active | BIT | NOT NULL, DEFAULT 1 | 是否上架 |

---

## 配置数据库 (MySQL)

### 连接配置

```
数据库类型: MySQL 8.0+
驱动: aiomysql
访问模式: Read Only（只读）
连接池: pool_size=5, max_overflow=10
```

### 表结构

配置数据库目前为未来扩展预留，暂无具体表结构。

**预设计表**:

| 表名 | 用途 |
|------|------|
| system_config | 系统配置项 |
| data_dictionary | 数据字典 |
| enum_values | 枚举值表 |

---

## 表关系图

### 用户数据库关系图

```
┌─────────────────┐         ┌─────────────────┐
│      users      │         │      roles      │
├─────────────────┤         ├─────────────────┤
│ id (PK)         │         │ id (PK)         │
│ email (UQ)      │    ┌───>│ name (UQ)       │
│ username (UQ)   │    │    │ description     │
│ full_name       │    │    │ created_at      │
│ hashed_password │    │    │ updated_at      │
│ is_active       │    │    └─────────────────┘
│ is_superuser    │    │             │
│ created_at      │    │             │
│ updated_at      │    │    ┌─────────────────┐
└─────────────────┘    │    │  permissions    │
         │             │    ├─────────────────┤
         │             │    │ id (PK)         │
         │    ┌────────┴──┐ │ name (UQ)       │
         │    │user_roles │ │ code (UQ)       │
         │    ├───────────┤ │ description     │
         │    │user_id(FK)│ │ created_at      │
         │    │role_id(FK)│ │ updated_at      │
         │    └───────────┘ └─────────────────┘
         │             │             │
         │             │    ┌─────────────────┐
         │             │    │role_permissions │
         │             │    ├─────────────────┤
         │             │    │role_id(FK)      │
         └─────────────┴────│permission_id(FK)│
                            └─────────────────┘
```

### 业务数据库关系图

```
┌─────────────────┐         ┌─────────────────┐
│     orders      │         │   order_items   │
├─────────────────┤         ├─────────────────┤
│ id (PK)         │◄────────│ order_id (FK)   │
│ order_no (UQ)   │         │ product_id (FK) │──┐
│ user_id         │         │ quantity        │  │
│ total_amount    │         │ unit_price      │  │
│ status          │         │ total_price     │  │
│ remark          │         │ created_at      │  │
│ created_at      │         │ updated_at      │  │
│ updated_at      │         └─────────────────┘  │
└─────────────────┘                              │
         │                                       │
         │                              ┌─────────────────┐
         │                              │    products     │
         │                              ├─────────────────┤
         │                              │ id (PK)         │
         └─────────────────────────────>│ name            │
                                        │ sku (UQ)        │
                                        │ price           │
                                        │ stock           │
                                        │ is_active       │
                                        │ created_at      │
                                        │ updated_at      │
                                        └─────────────────┘
```

---

## 数据库迁移

### 迁移工具

使用 **Alembic** 进行数据库迁移管理。

### 迁移目录结构

```
alembic/
├── versions/                    # 迁移脚本
│   └── 001_initial.py          # 初始迁移
├── user_db/                     # 用户数据库迁移配置
│   └── env.py
├── business_db/                 # 业务数据库迁移配置
│   └── env.py
├── env.py                       # 主配置文件
├── script.py.mako               # 迁移脚本模板
└── __init__.py
```

### 迁移命令

```bash
# 生成迁移脚本
alembic revision --autogenerate -m "description"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1

# 查看迁移历史
alembic history

# 查看当前版本
alembic current
```

### 多数据库迁移

由于使用多个独立数据库，需要为每个数据库单独执行迁移：

```bash
# 用户数据库迁移
cd alembic/user_db
alembic upgrade head

# 业务数据库迁移
cd alembic/business_db
alembic upgrade head
```

---

## 连接配置

### 环境变量配置

```bash
# .env 文件

# 用户数据库 - PostgreSQL
USER_DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/user_db

# 业务数据库 - SQL Server
BUSINESS_DATABASE_URL=mssql+aioodbc://sa:password@localhost:1433/business_db?driver=ODBC+Driver+17+for+SQL+Server

# 配置数据库 - MySQL
CONFIG_DATABASE_URL=mysql+aiomysql://root:password@localhost:3306/config_db
```

### 连接字符串格式

| 数据库 | 格式 |
|--------|------|
| PostgreSQL | `postgresql+asyncpg://user:password@host:port/database` |
| SQL Server | `mssql+aioodbc://user:password@host:port/database?driver=ODBC+Driver+17+for+SQL+Server` |
| MySQL | `mysql+aiomysql://user:password@host:port/database` |

### 连接池配置

```python
# app/db/session.py
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,      # 开发环境显示SQL
    future=True,              # 使用 SQLAlchemy 2.0 模式
    pool_pre_ping=True,       # 连接前检测有效性
    pool_size=5,              # 连接池大小
    max_overflow=10,          # 最大溢出连接数
)
```

---

## 最佳实践

### 1. 索引优化

```sql
-- 为经常查询的字段创建索引
CREATE INDEX ix_users_email ON users(email);
CREATE INDEX ix_orders_user_id ON orders(user_id);

-- 复合索引用于多条件查询
CREATE INDEX ix_orders_user_status ON orders(user_id, status);

-- 唯一索引确保数据唯一性
CREATE UNIQUE INDEX ix_users_email_unique ON users(email);
```

### 2. 字段设计

```sql
-- 使用适当的字段类型
email VARCHAR(255)       -- 邮箱长度限制
password VARCHAR(255)    -- bcrypt 哈希长度
amount DECIMAL(10, 2)    -- 金额使用 DECIMAL
is_active BOOLEAN        -- 布尔值使用 BOOLEAN

-- 使用时间戳
created_at TIMESTAMP DEFAULT now()
updated_at TIMESTAMP DEFAULT now()
```

### 3. 数据完整性

```sql
-- 外键约束
ALTER TABLE order_items 
ADD CONSTRAINT fk_order_items_order 
FOREIGN KEY (order_id) REFERENCES orders(id);

-- 非空约束
ALTER TABLE users ALTER COLUMN email SET NOT NULL;

-- 唯一约束
ALTER TABLE users ADD CONSTRAINT uq_users_email UNIQUE (email);
```

### 4. 性能优化

```sql
-- 定期分析和优化
ANALYZE users;

-- 清理死数据
DELETE FROM logs WHERE created_at < NOW() - INTERVAL '90 days';

-- 分区大表（按时间）
CREATE TABLE orders_2026 PARTITION OF orders
FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');
```

### 5. 备份策略

| 数据库 | 备份频率 | 保留期限 |
|--------|----------|----------|
| PostgreSQL | 每日全量 + 实时WAL | 30天 |
| SQL Server | 每日全量 + 每小时差异 | 14天 |
| MySQL | 每日全量 | 7天 |

---

> 文档版本: 1.0.0
> 更新时间: 2026-03-24