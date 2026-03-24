# 故障排查指南

> 本文档提供常见错误的诊断和解决方案。

## 目录

1. [启动问题](#启动问题)
2. [数据库连接问题](#数据库连接问题)
3. [API 错误](#api-错误)
4. [认证问题](#认证问题)
5. [测试问题](#测试问题)
6. [性能问题](#性能问题)
7. [部署问题](#部署问题)

---

## 启动问题

### 错误: ModuleNotFoundError

```
ModuleNotFoundError: No module named 'app'
```

**原因**: Python 路径问题

**解决方案**:
```bash
# 1. 确保在项目根目录
cd /path/to/project

# 2. 使用 uv 运行
uv run python run.py

# 3. 或设置 PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:."
uv run python run.py
```

---

### 错误: ImportError: cannot import name

```
ImportError: cannot import name 'XXX' from partially initialized module
```

**原因**: 循环导入

**解决方案**:
1. 检查导入顺序
2. 使用延迟导入
3. 将导入移到函数内部

```python
# ❌ 可能导致循环导入
from app.module_a import something_a

# ✅ 延迟导入
def my_function():
    from app.module_a import something_a
    return something_a
```

---

### 错误: Address already in use

```
OSError: [Errno 98] Address already in use
```

**原因**: 端口被占用

**解决方案**:
```bash
# 查找占用端口的进程
lsof -i :8000
# 或
netstat -tlnp | grep 8000

# 杀掉进程
kill -9 <PID>

# 或使用其他端口
uvicorn app.main:app --port 8001
```

---

## 数据库连接问题

### 错误: Connection refused

```
sqlalchemy.exc.OperationalError: (Connection refused)
```

**解决方案**:

**PostgreSQL**:
```bash
# 检查服务状态
sudo systemctl status postgresql

# 启动服务
sudo systemctl start postgresql

# 检查端口
netstat -tlnp | grep 5432
```

**SQL Server**:
```bash
# Docker 检查
docker ps | grep mssql
docker logs mssql
```

**MySQL**:
```bash
# 检查服务
sudo systemctl status mysql
sudo systemctl start mysql
```

---

### 错误: Authentication failed

```
sqlalchemy.exc.OperationalError: password authentication failed
```

**解决方案**:
1. 检查 `.env` 中的数据库 URL
2. 验证用户名密码
3. 检查数据库用户权限

```bash
# 测试连接
psql -h localhost -U postgres -d user_db

# 修改密码
psql -c "ALTER USER postgres PASSWORD 'newpassword';"
```

---

### 错误: Database does not exist

```
FATAL: database "xxx" does not exist
```

**解决方案**:
```bash
# 创建数据库
psql -c "CREATE DATABASE user_db;"

# 或检查数据库名称
psql -c "\l"
```

---

### 错误: Connection pool exhausted

```
sqlalchemy.exc.TimeoutError: QueuePool limit exceeded
```

**解决方案**:
```python
# 增加连接池大小
engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,        # 默认 5
    max_overflow=20,     # 默认 10
    pool_recycle=3600,   # 回收连接
    pool_pre_ping=True,  # 连接前检查
)
```

---

## API 错误

### 错误: 422 Validation Error

```json
{
    "detail": [
        {
            "loc": ["body", "email"],
            "msg": "value is not a valid email address",
            "type": "value_error.email"
        }
    ]
}
```

**解决方案**:
1. 检查请求体格式
2. 确认必填字段
3. 验证数据类型

```python
# 检查 Schema 定义
class UserCreate(BaseModel):
    email: EmailStr  # 必须是有效邮箱
    username: str    # 必填
    password: str    # 必填

# 正确的请求体
{
    "email": "user@example.com",  # 有效邮箱
    "username": "testuser",
    "password": "Test1234"
}
```

---

### 错误: 401 Unauthorized

```json
{"detail": "Could not validate credentials"}
```

**解决方案**:
1. 检查 Token 是否过期
2. 验证 Authorization 头格式
3. 确认 SECRET_KEY 一致

```bash
# 检查 Token
echo "<token>" | cut -d'.' -f2 | base64 -d

# 验证请求头格式
Authorization: Bearer <token>  # ✅ 正确
Authorization: <token>         # ❌ 错误
```

---

### 错误: 403 Forbidden

```json
{"detail": "The user doesn't have enough privileges"}
```

**解决方案**:
1. 确认用户有正确权限
2. 检查用户是否是 superuser
3. 验证角色和权限配置

```python
# 检查用户权限
SELECT u.*, r.name as role 
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id
LEFT JOIN roles r ON ur.role_id = r.id
WHERE u.id = <user_id>;
```

---

### 错误: 404 Not Found

```json
{"detail": "User 999 not found"}
```

**解决方案**:
1. 检查资源 ID 是否正确
2. 确认资源存在
3. 验证 URL 路径

---

### 错误: 409 Conflict

```json
{"detail": "Email user@example.com already registered"}
```

**解决方案**:
1. 使用已存在的邮箱/用户名
2. 先查询再创建

```python
# 检查是否存在
existing = await user_crud.get_by_email(db, email)
if existing:
    raise ConflictException("Email already registered")
```

---

## 认证问题

### 问题: Token 生成失败

**症状**: 登录后没有返回 token

**排查**:
```python
# 检查 SECRET_KEY
from app.core.config import settings
print(settings.SECRET_KEY)

# 检查 Token 过期时间
print(settings.ACCESS_TOKEN_EXPIRE_MINUTES)
```

---

### 问题: Token 验证失败

**症状**: 所有需要认证的请求返回 401

**排查**:
1. 检查 SECRET_KEY 是否一致
2. 检查 Token 是否过期
3. 验证算法配置

```python
# token.py
from jose import jwt

ALGORITHM = "HS256"  # 必须一致

# 生成和验证使用相同算法
token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
```

---

### 问题: 密码验证失败

**症状**: 正确密码登录失败

**排查**:
```python
# 检查密码哈希
from app.core.security import verify_password, get_password_hash

password = "Test1234"
hashed = get_password_hash(password)
print(hashed)  # $2b$12$...

# 验证
is_valid = verify_password(password, hashed)
print(is_valid)  # True
```

---

## 测试问题

### 错误: pytest-asyncio 未配置

```
RuntimeError: This test is using an async function but...
```

**解决方案**:
```python
# conftest.py
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# 测试文件
@pytest.mark.asyncio
async def test_something():
    ...
```

---

### 错误: 数据库会话问题

```
sqlalchemy.exc.InvalidRequestError: ...
```

**解决方案**:
```python
# 确保使用独立的测试数据库
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

@pytest.fixture
async def db():
    async with TestSessionLocal() as session:
        yield session
```

---

## 性能问题

### 问题: 查询速度慢

**排查**:
```sql
-- 查看查询计划
EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'test@example.com';

-- 检查索引
\di users

-- 添加索引
CREATE INDEX ix_users_email ON users(email);
```

---

### 问题: N+1 查询

**症状**: 单个请求产生大量数据库查询

**排查**:
```python
# ❌ N+1 查询
users = await db.execute(select(User))
for user in users:
    print(user.roles)  # 每次都查询

# ✅ 使用 selectinload
users = await db.execute(
    select(User).options(selectinload(User.roles))
)
```

---

### 问题: 内存泄漏

**排查**:
```python
import tracemalloc

tracemalloc.start()

# ... 运行代码 ...

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

for stat in top_stats[:10]:
    print(stat)
```

---

## 部署问题

### 错误: Module not found in production

**解决方案**:
```dockerfile
# 确保正确复制文件
COPY . /app
WORKDIR /app

# 设置 PYTHONPATH
ENV PYTHONPATH=/app
```

---

### 错误: 环境变量未加载

**解决方案**:
```python
# 确保 .env 文件存在
ls -la .env

# 检查加载
from app.core.config import settings
print(settings.SECRET_KEY)
```

---

### 错误: 数据库连接超时

**解决方案**:
```python
# 增加超时时间
engine = create_async_engine(
    DATABASE_URL,
    connect_args={
        "connect_timeout": 30,
        "command_timeout": 60,
    }
)
```

---

## 调试技巧

### 启用 SQLAlchemy 日志

```python
import logging
logging.basicConfig()
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
```

### 使用调试器

```python
# 在代码中插入断点
breakpoint()

# 或使用 pdb
import pdb; pdb.set_trace()
```

### 检查请求/响应

```python
# 中间件打印请求
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    print(f"Response: {response.status_code}")
    return response
```

---

## 获取帮助

### 检查日志

```bash
# 查看应用日志
tail -f logs/app.log

# 查看 Docker 日志
docker-compose logs -f app
```

### 有用的命令

```bash
# 检查环境
uv run python -c "import sys; print(sys.version)"

# 检查依赖
uv pip list

# 测试数据库连接
uv run python -c "from app.db.session import user_engine; print('OK')"
```

---

## 常见错误速查表

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| ModuleNotFoundError | 路径问题 | 使用 uv run 或设置 PYTHONPATH |
| Connection refused | 数据库未启动 | 启动数据库服务 |
| 401 Unauthorized | Token 无效 | 检查 SECRET_KEY 和 Token |
| 403 Forbidden | 权限不足 | 检查用户角色和权限 |
| 404 Not Found | 资源不存在 | 检查 ID 和 URL |
| 409 Conflict | 资源重复 | 先查询再创建 |
| 422 Validation Error | 数据格式错误 | 检查请求体格式 |
| Pool exhausted | 连接池满 | 增加池大小或优化查询 |
| Timeout | 查询超时 | 优化查询或增加超时时间 |

---

> 文档版本: 1.0.0
> 更新时间: 2026-03-24