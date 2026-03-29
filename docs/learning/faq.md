# FAQ 常见问题

> 本文档收集了项目开发和使用中的常见问题及解答。

## 目录

1. [项目基础](#项目基础)
2. [环境配置](#环境配置)
3. [数据库相关](#数据库相关)
4. [API 开发](#api-开发)
5. [认证授权](#认证授权)
6. [测试相关](#测试相关)
7. [部署运维](#部署运维)
8. [性能优化](#性能优化)

---

## 项目基础

### Q: 这个项目是做什么的?

**A:** 这是一个企业级 FastAPI 项目模板，展示了如何构建生产级的 Python Web API。主要特点包括：

- 异步架构 (async/await)
- 多数据库支持 (PostgreSQL, SQL Server, MySQL)
- 分层架构设计 (API → Service → CRUD → Model)
- JWT 认证和 RBAC 权限控制
- 完整的开发工具链

### Q: 为什么选择 FastAPI 而不是 Django/Flask?

**A:**

| 特性          | FastAPI  | Django | Flask    |
| ------------- | -------- | ------ | -------- |
| 异步支持      | 原生支持 | 有限   | 需要扩展 |
| 性能          | 高       | 中     | 中       |
| 自动 API 文档 | 是       | 否     | 需要扩展 |
| 类型检查      | Pydantic | 无     | 无       |
| 学习曲线      | 中       | 高     | 低       |

FastAPI 特别适合：

- 高性能 API 服务
- 微服务架构
- 需要自动文档的项目
- 异步 I/O 密集型应用

### Q: 为什么使用多个数据库而不是一个?

**A:** 多数据库架构的原因：

1. **关注点分离**：用户数据和业务数据独立管理
2. **独立扩展**：不同数据库可以独立扩容
3. **技术选型**：不同场景使用最适合的数据库
4. **安全隔离**：敏感数据与其他数据隔离

### Q: Service 层为什么使用静态方法?

**A:** 静态方法模式的优势：

1. **无状态**：Service 层不依赖外部状态
2. **可复用**：可在 CLI 和 API 中使用
3. **简化调用**：无需依赖注入
4. **易于测试**：可以轻松 mock

---

## 环境配置

### Q: 如何切换开发/测试/生产环境?

**A:** 通过 `APP_ENV` 环境变量控制：

```bash
# 开发环境
APP_ENV=development
DEBUG=True

# 测试环境
APP_ENV=testing
DEBUG=True

# 生产环境
APP_ENV=production
DEBUG=False
```

创建对应的环境文件：

```text
.env.development
.env.testing
.env.production
```

### Q: SECRET_KEY 如何生成?

**A:** 使用以下方法生成强密钥：

```bash
# Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# OpenSSL
openssl rand -base64 32

# 生成示例
# a3f8b2c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0
```

**警告**：生产环境必须更换默认密钥！

### Q: UV 和 pip 有什么区别?

**A:**

| 特性     | UV               | pip            |
| -------- | ---------------- | -------------- |
| 速度     | 极快 (Rust 编写) | 较慢           |
| 锁文件   | 自动生成         | 需要 pip-tools |
| 虚拟环境 | 自动管理         | 手动创建       |
| 依赖解析 | 更智能           | 基本           |

推荐使用 UV，但项目也支持 pip：

```bash
# UV (推荐)
uv sync
uv add package

# pip
pip install -r requirements.txt
pip install package
```

---

## 数据库相关

### Q: 如何添加新的数据库表?

**A:** 三步完成：

1. **创建模型**

```python
# app/models/user_db/models.py
class NewTable(UserDBBase):
    __tablename__ = "new_table"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
```

2. **生成迁移**

```bash
alembic revision --autogenerate -m "add new_table"
```

3. **执行迁移**

```bash
alembic upgrade head
```

### Q: 为什么要使用多个 declarative_base?

**A:** 因为每个数据库有独立的表结构和连接：

```python
# 不同基类对应不同数据库
UserDBBase = declarative_base(cls=UserBase)      # PostgreSQL
BusinessDBBase = declarative_base(cls=BusinessBase)  # SQL Server
ConfigDBBase = declarative_base(cls=ConfigBase)      # MySQL
```

这样可以：

- 避免表名冲突
- 独立管理迁移
- 分离关注点

### Q: 如何处理跨数据库的关联?

**A:** 不同数据库的表不能建立外键关联。解决方案：

1. **应用层维护一致性**

```python
# 创建订单时，同时更新用户统计
async def create_order(order_data, user_id):
    # 在业务库创建订单
    order = await business_crud.create_order(order_data)
    # 在用户库更新统计
    await user_crud.increment_order_count(user_id)
```

2. **使用最终一致性**
3. **记录关联 ID 但不使用外键**

### Q: 为什么使用异步数据库驱动?

**A:** 异步驱动的优势：

| 驱动     | 类型       | 特点                   |
| -------- | ---------- | ---------------------- |
| asyncpg  | PostgreSQL | 最快的 PostgreSQL 驱动 |
| aiomysql | MySQL      | MySQL 异步支持         |
| aioodbc  | SQL Server | 通过 ODBC 连接         |

好处：

- 不阻塞事件循环
- 更高的并发能力
- 更好的资源利用

---

## API 开发

### Q: 如何添加新的 API 端点?

**A:** 标准流程：

1. **创建 Schema** (`app/schemas/`)
2. **创建 Model** (`app/models/`)
3. **创建 CRUD** (`app/crud/`)
4. **创建 Service** (`app/services/`)
5. **创建 Endpoint** (`app/api/v1/endpoints/`)
6. **注册路由** (`app/api/v1/__init__.py`)

### Q: 响应模型为什么要分层?

**A:** 不同 Schema 的用途：

| Schema      | 用途       | 示例         |
| ----------- | ---------- | ------------ |
| `*Create`   | 创建请求   | UserCreate   |
| `*Update`   | 更新请求   | UserUpdate   |
| `*Response` | API 响应   | UserResponse |
| `*InDB`     | 数据库操作 | UserInDB     |

好处：

- 隐藏敏感字段 (如 hashed_password)
- 灵活控制输入/输出
- 清晰的 API 契约

### Q: 为什么使用 DataResponse 包装响应?

**A:** 统一响应格式的好处：

```json
{
    "success": true,
    "message": "操作成功",
    "data": { ... }
}
```

优点：

- 前端处理统一
- 便于添加元数据
- 方便错误处理

### Q: 如何实现文件上传?

**A:** 使用 `UploadFile`:

```python
from fastapi import UploadFile, File

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    # 验证文件类型
    # 保存文件
    # 返回文件信息
```

---

## 认证授权

### Q: JWT Token 为什么有过期时间?

**A:** 过期时间的原因：

1. **安全性**：减少 Token 泄露的风险
2. **控制力**：可以强制用户重新认证
3. **状态管理**：无需服务端存储 Token

推荐配置：

```python
ACCESS_TOKEN_EXPIRE_MINUTES = 30      # 访问令牌 30 分钟
REFRESH_TOKEN_EXPIRE_MINUTES = 10080  # 刷新令牌 7 天
```

### Q: 如何实现 Refresh Token?

**A:** 扩展认证流程：

```python
# 1. 生成两个 Token
def create_tokens(user_id: int):
    access_token = create_access_token(
        subject=user_id,
        expires_delta=timedelta(minutes=30)
    )
    refresh_token = create_refresh_token(
        subject=user_id,
        expires_delta=timedelta(days=7)
    )
    return access_token, refresh_token

# 2. 刷新端点
@router.post("/refresh")
async def refresh_token(token: str):
    user_id = verify_refresh_token(token)
    if not user_id:
        raise UnauthorizedException("Invalid refresh token")
    return create_tokens(user_id)
```

### Q: 如何实现权限控制?

**A:** RBAC 实现方式：

```python
# 1. 定义权限依赖
async def require_permission(permission: str):
    async def checker(current_user: User = Depends(get_current_user)):
        if not has_permission(current_user, permission):
            raise ForbiddenException("Permission denied")
        return current_user
    return Depends(checker)

# 2. 使用
@router.get("/admin")
async def admin_endpoint(
    _user: User = require_permission("admin:access")
):
    ...
```

### Q: Token 被盗怎么办?

**A:** 应对措施：

1. **缩短过期时间**
2. **实现 Token 黑名单**

```python
# Redis 中存储黑名单
await redis.setex(f"blacklist:{token}", expire_time, "1")
```

3. **提供用户登出功能**
4. **敏感操作需要二次验证**

---

## 测试相关

### Q: 如何运行测试?

**A:** 多种运行方式：

```bash
# 运行所有测试
just test

# 运行特定文件
uv run pytest tests/test_api/test_users.py -v

# 运行特定测试
uv run pytest tests/test_api/test_users.py::test_register -v

# 带覆盖率报告
uv run pytest --cov=app --cov-report=html

# 并行运行
uv run pytest -n auto
```

### Q: 如何 mock 数据库?

**A:** 使用 `unittest.mock`:

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_service():
    mock_db = AsyncMock()

    with patch("app.services.user.user_crud") as mock_crud:
        mock_crud.get.return_value = User(id=1, email="test@example.com")

        result = await user_service.get_user_by_id(mock_db, 1)

        assert result.email == "test@example.com"
```

### Q: 为什么使用 pytest 而不是 unittest?

**A:** pytest 的优势：

| 特性     | pytest         | unittest     |
| -------- | -------------- | ------------ |
| 语法简洁 | 是             | 否           |
| Fixtures | 强大           | 基本         |
| 参数化   | 简单           | 复杂         |
| 插件生态 | 丰富           | 有限         |
| 异步支持 | pytest-asyncio | 需要额外配置 |

---

## 部署运维

### Q: 如何部署到生产环境?

**A:** 推荐方案：

1. **Gunicorn + Uvicorn**

```bash
gunicorn app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 4 \
    --bind 0.0.0.0:8000
```

2. **Docker + Nginx**
3. **Kubernetes**

### Q: 如何配置 HTTPS?

**A:** 推荐在反向代理层配置：

```nginx
server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

或使用 Let's Encrypt：

```bash
certbot --nginx -d api.example.com
```

### Q: 如何监控应用?

**A:** 推荐监控方案：

| 类型 | 工具                 | 用途     |
| ---- | -------------------- | -------- |
| 指标 | Prometheus + Grafana | 性能监控 |
| 日志 | ELK / Loki           | 日志分析 |
| 错误 | Sentry               | 错误追踪 |
| 追踪 | Jaeger / Zipkin      | 请求追踪 |

### Q: 数据库如何备份?

**A:** 各数据库备份方式：

```bash
# PostgreSQL
pg_dump -h localhost -U postgres db_name > backup.sql

# SQL Server
sqlcmd -S server -Q "BACKUP DATABASE db_name TO DISK = 'backup.bak'"

# MySQL
mysqldump -h localhost -u root db_name > backup.sql
```

建议：

- 每日自动备份
- 异地存储
- 定期恢复测试

---

## 性能优化

### Q: 如何优化数据库查询?

**A:** 常见优化方法：

1. **添加索引**

```python
email: Mapped[str] = mapped_column(index=True)
```

2. **预加载关系**

```python
result = await db.execute(
    select(User).options(selectinload(User.roles))
)
```

3. **避免 N+1 查询**
4. **使用分页**
5. **查询字段优化**

### Q: 如何提高并发能力?

**A:** 优化建议：

1. **使用异步驱动**
2. **增加 Worker 数量**
3. **数据库连接池优化**
4. **使用缓存 (Redis)**
5. **CDN 加速静态资源**

### Q: 如何处理大文件上传?

**A:** 流式处理方案：

```python
import aiofiles

@router.post("/upload-large")
async def upload_large_file(file: UploadFile = File(...)):
    async with aiofiles.open(f"uploads/{file.filename}", "wb") as f:
        while chunk := await file.read(8192):
            await f.write(chunk)
    return {"status": "uploaded"}
```

---

## 其他问题

### Q: 如何贡献代码?

**A:** 参考 [开发指南](development-guide.md) 中的贡献指南部分。

### Q: 遇到问题如何获取帮助?

**A:**

1. 查看本文档和项目文档
2. 搜索 GitHub Issues
3. 提交新的 Issue
4. 联系开发团队

### Q: 项目有什么限制?

**A:** 当前限制：

- 不支持跨数据库事务
- 配置数据库为只读
- 无实时功能 (WebSocket)
- 无文件存储服务 (需自行集成)

---

> 文档版本: 1.0.0
> 更新时间: 2026-03-24
