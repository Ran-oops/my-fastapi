# 术语表

> 本文档定义项目中使用的专业术语和概念。

## 目录

1. [通用术语](#通用术语)
2. [架构术语](#架构术语)
3. [数据库术语](#数据库术语)
4. [API 术语](#api-术语)
5. [安全术语](#安全术语)
6. [Python/FastAPI 术语](#pythonfastapi-术语)
7. [项目特定术语](#项目特定术语)

---

## 通用术语

| 术语   | 英文         | 解释                                           |
| ------ | ------------ | ---------------------------------------------- |
| 异步   | Async        | 不阻塞程序执行的编程模式，允许同时处理多个任务 |
| 同步   | Sync         | 按顺序执行任务，一个完成后才能开始下一个       |
| 并发   | Concurrency  | 同时处理多个任务的能力                         |
| 并行   | Parallelism  | 同时执行多个任务(多核CPU)                      |
| 阻塞   | Blocking     | 操作等待完成期间程序无法继续执行               |
| 非阻塞 | Non-blocking | 操作立即返回，不等待完成                       |

---

## 架构术语

| 术语       | 英文                         | 解释                               |
| ---------- | ---------------------------- | ---------------------------------- |
| 分层架构   | Layered Architecture         | 将系统分为多个层次，每层有特定职责 |
| API 层     | API Layer                    | 处理 HTTP 请求/响应的最外层        |
| 服务层     | Service Layer                | 包含业务逻辑的核心层               |
| 数据访问层 | Data Access Layer (DAL)      | 封装数据库操作的层                 |
| 模型层     | Model Layer                  | 定义数据结构和数据库映射           |
| 依赖注入   | Dependency Injection (DI)    | 将依赖从外部传入而不是内部创建     |
| 控制反转   | Inversion of Control (IoC)   | 对象不创建依赖，而是由容器注入     |
| 单例模式   | Singleton                    | 确保类只有一个实例                 |
| 泛型       | Generic                      | 类型参数化的编程技术               |
| CRUD       | Create, Read, Update, Delete | 增删改查四个基本操作               |

---

## 数据库术语

| 术语   | 英文                                          | 解释                               |
| ------ | --------------------------------------------- | ---------------------------------- |
| ORM    | Object-Relational Mapping                     | 对象关系映射，将数据库表映射为类   |
| 迁移   | Migration                                     | 数据库结构变更的版本管理           |
| 会话   | Session                                       | 数据库连接的工作单元               |
| 连接池 | Connection Pool                               | 预创建的数据库连接集合             |
| 事务   | Transaction                                   | 一组要么全部成功要么全部失败的操作 |
| ACID   | Atomicity, Consistency, Isolation, Durability | 事务的四个特性                     |
| 索引   | Index                                         | 加速查询的数据结构                 |
| 外键   | Foreign Key                                   | 表之间的关联约束                   |
| 主键   | Primary Key                                   | 唯一标识记录的字段                 |
| 索引   | Index                                         | 用于加速查询的数据结构             |

### SQLAlchemy 特定术语

| 术语             | 英文 | 解释                      |
| ---------------- | ---- | ------------------------- |
| declarative_base | -    | SQLAlchemy 的模型基类     |
| Mapped           | -    | SQLAlchemy 2.0 类型注解   |
| mapped_column    | -    | SQLAlchemy 2.0 列定义方式 |
| relationship     | -    | 定义表之间的关系          |
| back_populates   | -    | 双向关系的反向引用        |
| secondary        | -    | 多对多关系的关联表        |

---

## API 术语

| 术语     | 英文                            | 解释                          |
| -------- | ------------------------------- | ----------------------------- |
| REST     | Representational State Transfer | 一种 API 设计风格             |
| 端点     | Endpoint                        | API 的一个具体 URL 路径       |
| 路由     | Route                           | URL 路径到处理函数的映射      |
| 中间件   | Middleware                      | 请求/响应处理管道中的组件     |
| 序列化   | Serialization                   | 将对象转换为可传输格式 (JSON) |
| 反序列化 | Deserialization                 | 将传输格式转换为对象          |
| Schema   | -                               | 数据结构的定义和验证规则      |
| 分页     | Pagination                      | 将大量数据分成多页返回        |
| 参数化   | Parameterized                   | 使用参数化查询防止 SQL 注入   |

### HTTP 术语

| 术语     | 英文                          | 解释                      |
| -------- | ----------------------------- | ------------------------- |
| 请求方法 | HTTP Method                   | GET, POST, PUT, DELETE 等 |
| 状态码   | Status Code                   | 200, 404, 500 等响应状态  |
| 头信息   | Headers                       | 请求/响应的元数据         |
| 负载     | Payload                       | 请求/响应的主体数据       |
| CORS     | Cross-Origin Resource Sharing | 跨域资源共享              |

---

## 安全术语

| 术语     | 英文                      | 解释                         |
| -------- | ------------------------- | ---------------------------- |
| JWT      | JSON Web Token            | 用于安全传输信息的令牌格式   |
| Token    | -                         | 用于身份验证的凭证           |
| 访问令牌 | Access Token              | 用于访问受保护资源的短期令牌 |
| 刷新令牌 | Refresh Token             | 用于获取新访问令牌的长期令牌 |
| 哈希     | Hash                      | 单向转换数据的方法           |
| 加密     | Encryption                | 双向转换数据需要密钥解密     |
| 加盐     | Salt                      | 随机数据添加到密码再哈希     |
| bcrypt   | -                         | 专用于密码哈希的算法         |
| OAuth2   | Open Authorization 2.0    | 授权框架标准                 |
| RBAC     | Role-Based Access Control | 基于角色的访问控制           |

---

## Python/FastAPI 术语

| 术语              | 英文            | 解释                     |
| ----------------- | --------------- | ------------------------ |
| 协程              | Coroutine       | 可以暂停和恢复的函数     |
| 事件循环          | Event Loop      | 管理异步任务的调度器     |
| 类型注解          | Type Annotation | 为变量和函数指定类型     |
| 泛型              | Generic         | 类型参数化的类或函数     |
| Pydantic          | -               | Python 数据验证库        |
| 路径操作          | Path Operation  | FastAPI 中的请求处理函数 |
| 依赖注入          | Depends         | FastAPI 的依赖注入系统   |
| Pydantic Settings | -               | 基于环境变量的配置管理   |

### Python 3.13 新特性

| 术语       | 英文 | 解释                  |
| ---------- | ---- | --------------------- |
| TypeVar    | -    | 泛型类型变量          |
| TypedDict  | -    | 类型化的字典          |
| Self       | -    | 返回自身类型的注解    |
| match      | -    | 模式匹配语句          |
| union type | -    | `X \| Y` 类型联合语法 |

---

## 项目特定术语

### 业务术语

| 术语      | 解释                           | 使用场景     |
| --------- | ------------------------------ | ------------ |
| FTE       | Full-Time Equivalent，全职当量 | 人力资源计算 |
| QC        | Quality Control，质量控制      | 报告生成     |
| SSU       | Sub-Site Unit，子站点单元      | 地理数据     |
| Subregion | 子区域                         | 地理分区     |

### 数据库术语

| 术语        | 解释                    | 使用场景     |
| ----------- | ----------------------- | ------------ |
| User DB     | 用户数据库 (PostgreSQL) | 认证授权相关 |
| Business DB | 业务数据库 (SQL Server) | 订单产品相关 |
| Config DB   | 配置数据库 (MySQL)      | 系统配置     |

---

## 常见缩写

| 缩写  | 全称                                         | 解释               |
| ----- | -------------------------------------------- | ------------------ |
| API   | Application Programming Interface            | 应用程序接口       |
| JWT   | JSON Web Token                               | JSON 网络令牌      |
| ORM   | Object-Relational Mapping                    | 对象关系映射       |
| RBAC  | Role-Based Access Control                    | 基于角色的访问控制 |
| CORS  | Cross-Origin Resource Sharing                | 跨域资源共享       |
| TLS   | Transport Layer Security                     | 传输层安全         |
| URL   | Uniform Resource Locator                     | 统一资源定位符     |
| HTTP  | HyperText Transfer Protocol                  | 超文本传输协议     |
| SQL   | Structured Query Language                    | 结构化查询语言     |
| CRUD  | Create Read Update Delete                    | 增删改查           |
| DI    | Dependency Injection                         | 依赖注入           |
| DTO   | Data Transfer Object                         | 数据传输对象       |
| CLI   | Command Line Interface                       | 命令行接口         |
| CI/CD | Continuous Integration/Continuous Deployment | 持续集成/持续部署  |
| IDE   | Integrated Development Environment           | 集成开发环境       |
| VCS   | Version Control System                       | 版本控制系统       |
| ENV   | Environment Variable                         | 环境变量           |

---

## 代码命名约定

### Python 命名规范

| 类型 | 规范                | 示例              |
| ---- | ------------------- | ----------------- |
| 模块 | snake_case          | `user_service.py` |
| 类   | PascalCase          | `UserService`     |
| 函数 | snake_case          | `get_user_by_id`  |
| 方法 | snake_case          | `create_item`     |
| 变量 | snake_case          | `user_count`      |
| 常量 | UPPER_SNAKE_CASE    | `MAX_RETRY_COUNT` |
| 私有 | _leading_underscore | `_cache`          |
| 特殊 | __dunder__          | `__init__`        |

### 数据库命名规范

| 类型     | 规范                   | 示例                      |
| -------- | ---------------------- | ------------------------- |
| 表名     | 复数 snake_case        | `users`, `orders`         |
| 字段     | snake_case             | `user_name`, `created_at` |
| 主键     | `id`                   | `id`                      |
| 外键     | `{table}_id`           | `user_id`                 |
| 索引     | `ix_{table}_{columns}` | `ix_users_email`          |
| 唯一约束 | `uq_{table}_{columns}` | `uq_users_email`          |

---

## 图例

### 关系符号

| 符号  | 含义      |
| ----- | --------- |
| `→`   | 调用/依赖 |
| `↔`   | 双向关系  |
| `1:N` | 一对多    |
| `M:N` | 多对多    |
| `1:1` | 一对一    |

### 状态符号

| 符号 | 含义      |
| ---- | --------- |
| `✓`  | 成功/通过 |
| `✗`  | 失败/错误 |
| `?`  | 待确认    |
| `→`  | 转换到    |

---

> 文档版本: 1.0.0
> 更新时间: 2026-03-24
