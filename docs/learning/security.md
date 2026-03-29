# 安全设计文档

> 本文档描述 Enterprise FastAPI 项目的安全机制、认证授权设计和安全最佳实践。

## 目录

1. [安全架构概览](#安全架构概览)
2. [认证机制](#认证机制)
3. [授权机制](#授权机制)
4. [密码安全](#密码安全)
5. [CORS 配置](#cors-配置)
6. [输入验证](#输入验证)
7. [安全检查清单](#安全检查清单)

---

## 安全架构概览

### 安全层次

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                           应用层安全                                     │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  HTTPS / TLS                                          网络层    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  CORS Policy                                         跨域控制    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  JWT Authentication                               认证层         │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  RBAC Authorization                               授权层         │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Input Validation                                  验证层         │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Password Hashing (bcrypt)                        密码安全       │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 安全配置

```python
# app/core/config.py
class Settings(BaseSettings):
    # 密钥配置
    SECRET_KEY: str = "change-this-secret-key-in-production"

    # Token 过期时间
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7天

    # CORS 配置
    BACKEND_CORS_ORIGINS: list[str] = ["*"]

    # 环境
    APP_ENV: str = "development"
    DEBUG: bool = True
```

---

## 认证机制

### JWT Token 认证

本项目使用 **JSON Web Token (JWT)** 进行用户认证。

#### Token 结构

```text
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.  <- Header
eyJzdWIiOiIxIiwiZXhwIjoxNjc5NTk2ODAwfQ. <- Payload
SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c  <- Signature
```

#### Header

```json
{
    "alg": "HS256",
    "typ": "JWT"
}
```

#### Payload

```json
{
    "sub": "1",           // 用户 ID
    "exp": 1679596800     // 过期时间 (Unix timestamp)
}
```

#### 签名

```text
HMACSHA256(
    base64UrlEncode(header) + "." + base64UrlEncode(payload),
    SECRET_KEY
)
```

### Token 生成

```python
# app/core/security.py
from datetime import UTC, datetime, timedelta
from jose import jwt

ALGORITHM = "HS256"

def create_access_token(
    subject: str | int, 
    expires_delta: timedelta | None = None
) -> str:
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

### Token 验证

```python
def verify_token(token: str) -> str | None:
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[ALGORITHM]
        )
        return payload.get("sub")
    except JWTError:
        return None
```

### 认证流程

```text
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Client    │         │   Server    │         │  Database   │
└──────┬──────┘         └──────┬──────┘         └──────┬──────┘
       │                       │                       │
       │  1. POST /auth/login  │                       │
       │  {username, password} │                       │
       │──────────────────────>│                       │
       │                       │                       │
       │                       │  2. Query user        │
       │                       │──────────────────────>│
       │                       │                       │
       │                       │  3. Return user       │
       │                       │<──────────────────────│
       │                       │                       │
       │                       │  4. Verify password   │
       │                       │     (bcrypt)          │
       │                       │                       │
       │                       │  5. Create JWT Token  │
       │                       │                       │
       │  6. Return Token      │                       │
       │<──────────────────────│                       │
       │                       │                       │
       │  7. Request with      │                       │
       │  Authorization header │                       │
       │──────────────────────>│                       │
       │                       │                       │
       │                       │  8. Verify Token      │
       │                       │  9. Get user          │
       │                       │──────────────────────>│
       │                       │                       │
       │  10. Return data      │                       │
       │<──────────────────────│                       │
```

### OAuth2 Password Flow

```python
# app/api/deps.py
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

async def get_current_user(
    db: AsyncSession = Depends(get_user_db),
    token: str = Depends(oauth2_scheme)  # 自动从 header 提取 token
) -> User:
    user_id = verify_token(token)
    if user_id is None:
        raise UnauthorizedException("Could not validate credentials")

    user = await user_crud.get(db, id=int(user_id))
    if user is None:
        raise UnauthorizedException("User not found")

    if user.is_active is False:
        raise UnauthorizedException("Inactive user")

    return user
```

---

## 授权机制

### RBAC (基于角色的访问控制)

```text
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│      Users      │────>│      Roles      │────>│   Permissions   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
    多对多                   多对多

示例:
- User: john@example.com
  └─ Roles: admin, editor
     └─ Permissions: user:read, user:write, article:manage
```

### 角色定义

| 角色   | 说明       | 典型权限     |
| ------ | ---------- | ------------ |
| admin  | 超级管理员 | 所有权限     |
| editor | 内容编辑   | 内容相关权限 |
| viewer | 只读用户   | 查看权限     |

### 权限定义

| 权限代码    | 说明     |
| ----------- | -------- |
| user:read   | 查看用户 |
| user:write  | 编辑用户 |
| user:delete | 删除用户 |
| order:read  | 查看订单 |
| order:write | 编辑订单 |

### 权限检查实现

```python
# app/api/deps.py
async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """检查是否为超级管理员"""
    if current_user.is_superuser is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user
```

### 权限装饰器模式

```python
# 在端点中使用权限检查
@router.get("/admin/users", response_model=List[UserResponse])
async def list_all_users(
    _current_user: User = Depends(get_current_active_superuser),  # 需要超级管理员
):
    """只有超级管理员可以访问"""
    return await user_service.get_all_users()

@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),  # 需要登录
):
    """用户只能更新自己的信息，管理员可以更新任何人"""
    if current_user.is_superuser is False and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return await user_service.update_user(user_id, user_in)
```

---

## 密码安全

### 密码哈希

使用 **bcrypt** 算法进行密码哈希：

```python
# app/core/security.py
import bcrypt

def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return bcrypt.hashpw(
        password.encode(), 
        bcrypt.gensalt()
    ).decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), 
        hashed_password.encode("utf-8")
    )
```

### 密码强度要求

```python
# app/schemas/user.py
from pydantic import field_validator
import re

class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        # 长度检查
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        # bcrypt 最大长度限制
        if len(v) > 72:
            v = v[:72]

        # 必须包含字母
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter")

        # 必须包含数字
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")

        return v
```

### 密码策略总结

| 策略     | 要求                      |
| -------- | ------------------------- |
| 最小长度 | 8 字符                    |
| 最大长度 | 72 字符 (bcrypt 限制)     |
| 复杂度   | 至少包含字母和数字        |
| 存储     | bcrypt 哈希 (自动加 salt) |
| 验证     | 哈希比较                  |

---

## CORS 配置

### 跨域资源共享 (CORS)

```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
```

### CORS 配置选项

| 配置项            | 说明           | 生产环境建议                      |
| ----------------- | -------------- | --------------------------------- |
| allow_origins     | 允许的源       | 具体域名，避免使用 "*"            |
| allow_credentials | 允许携带凭据   | true                              |
| allow_methods     | 允许的方法     | ["GET", "POST", "PUT", "DELETE"]  |
| allow_headers     | 允许的 headers | ["Authorization", "Content-Type"] |

### 环境配置

```bash
# 开发环境
BACKEND_CORS_ORIGINS=*

# 生产环境
BACKEND_CORS_ORIGINS=https://app.example.com,https://admin.example.com
```

---

## 输入验证

### Pydantic 验证

使用 Pydantic V2 进行请求数据验证：

```python
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict

class UserCreate(BaseModel):
    email: EmailStr           # 自动验证邮箱格式
    username: str             # 必填字符串
    password: str             # 必填字符串

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        # 用户名长度验证
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(v) > 50:
            raise ValueError("Username must be at most 50 characters")

        # 用户名字符验证
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Username can only contain letters, numbers, and underscores")

        return v
```

### SQL 注入防护

SQLAlchemy 自动处理参数化查询，防止 SQL 注入：

```python
# 安全 - SQLAlchemy 自动参数化
result = await db.execute(
    select(User).where(User.email == email)  # 自动参数化
)

# 不安全 - 直接拼接 SQL (绝对不要这样做)
# result = await db.execute(f"SELECT * FROM users WHERE email = '{email}'")
```

### XSS 防护

```python
# 使用 Pydantic 自动转义
class ArticleCreate(BaseModel):
    title: str
    content: str

    @field_validator("content")
    @classmethod
    def sanitize_content(cls, v: str) -> str:
        # 如果需要，可以添加 HTML 清理
        # from bleach import clean
        # return clean(v)
        return v
```

---

## 安全检查清单

### 开发阶段

- [ ] 使用强 SECRET_KEY (至少 32 字符随机字符串)
- [ ] 配置合适的密码策略
- [ ] 使用 HTTPS
- [ ] 配置 CORS 白名单
- [ ] 输入验证
- [ ] 错误处理不暴露敏感信息

### 部署前

- [ ] SECRET_KEY 不是默认值
- [ ] DEBUG = False
- [ ] CORS 不使用通配符 "*"
- [ ] 数据库密码不是默认值
- [ ] 配置防火墙规则
- [ ] 启用 HTTPS/TLS

### 定期检查

- [ ] 依赖更新 (检查安全漏洞)
- [ ] 审查访问日志
- [ ] 密钥轮换
- [ ] 权限审计

---

## 安全配置示例

### 生产环境配置

```bash
# .env.production

# 应用配置
APP_ENV=production
DEBUG=False

# 密钥 - 使用强随机密钥
SECRET_KEY=a3f8b2c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0

# CORS - 只允许特定域名
BACKEND_CORS_ORIGINS=https://app.example.com,https://admin.example.com

# Token 过期时间
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 数据库 - 使用强密码
USER_DATABASE_URL=postgresql+asyncpg://user:strong_password@localhost/db
```

### 安全响应头

推荐在反向代理 (Nginx) 层添加安全头：

```nginx
# nginx.conf
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'" always;
```

---

## 常见安全问题

### Q: Token 被盗怎么办？

A:

1. 实现 Token 黑名单机制
2. 缩短 Token 过期时间
3. 使用 Refresh Token 机制
4. 提供用户主动登出功能

### Q: 如何防止暴力破解？

A:

1. 实现登录尝试限制 (如 5次/分钟)
2. 使用 CAPTCHA
3. 账户锁定机制
4. 记录异常登录尝试

### Q: 敏感日志处理？

A:

```python
import logging

# 不要记录敏感信息
logger.info(f"User login: {username}")  # OK
# logger.info(f"Password: {password}")  # 绝对不要！

# 部分信息脱敏
def mask_email(email: str) -> str:
    username, domain = email.split("@")
    return f"{username[0]}***@{domain}"
```

---

> 文档版本: 1.0.0
> 更新时间: 2026-03-24
