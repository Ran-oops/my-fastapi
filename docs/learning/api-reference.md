# API 接口文档

> 本文档描述 Enterprise FastAPI 项目的所有 RESTful API 接口。

## 目录

1. [API 概述](#api-概述)
2. [认证接口](#认证接口-auth)
3. [用户接口](#用户接口-users)
4. [请求/响应格式](#请求响应格式)
5. [错误处理](#错误处理)
6. [分页查询](#分页查询)
7. [API 索引](#api-索引)

---

## API 概述

### Base URL

```
http://localhost:8000/api/v1
```

### API 文档入口

| 文档类型 | URL |
|---------|-----|
| Swagger UI | http://localhost:8000/api/v1/docs |
| ReDoc | http://localhost:8000/api/v1/redoc |
| OpenAPI JSON | http://localhost:8000/api/v1/openapi.json |

### 认证方式

所有需要认证的接口使用 Bearer Token：

```
Authorization: Bearer <access_token>
```

### 通用响应格式

**成功响应**:
```json
{
    "success": true,
    "message": "Operation successful",
    "data": { ... }
}
```

**分页响应**:
```json
{
    "success": true,
    "message": "Data retrieved successfully",
    "data": [ ... ],
    "total": 100,
    "page": 1,
    "page_size": 10,
    "total_pages": 10
}
```

**错误响应**:
```json
{
    "detail": "Error message",
    "status_code": 400,
    "error_type": "BadRequestException"
}
```

---

## 认证接口 (Auth)

### POST /auth/register

注册新用户。

**认证**: 不需要

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| email | string | 是 | 邮箱地址，必须有效 |
| username | string | 是 | 用户名 |
| password | string | 是 | 密码，至少8字符，包含字母和数字 |
| full_name | string | 否 | 全名 |
| is_active | boolean | 否 | 是否激活，默认 true |

**请求示例**:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "johndoe",
    "password": "SecurePass123",
    "full_name": "John Doe"
  }'
```

**成功响应**: `201 Created`

```json
{
    "success": true,
    "message": "User created successfully",
    "data": {
        "id": 1,
        "email": "user@example.com",
        "username": "johndoe",
        "full_name": "John Doe",
        "is_active": true,
        "is_superuser": false,
        "created_at": "2026-03-24T10:00:00Z",
        "updated_at": "2026-03-24T10:00:00Z"
    }
}
```

**错误响应**:

| 状态码 | 说明 | 示例 |
|--------|------|------|
| 409 | 邮箱已注册 | `{"detail": "Email user@example.com already registered"}` |
| 409 | 用户名已存在 | `{"detail": "Username johndoe already taken"}` |
| 422 | 验证失败 | `{"detail": [{"loc": ["body", "password"], "msg": "must be at least 8 characters"}]}` |

---

### POST /auth/login

用户登录，获取访问令牌。

**认证**: 不需要

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |

**请求示例**:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "password": "SecurePass123"
  }'
```

**成功响应**: `200 OK`

```json
{
    "success": true,
    "message": "Login successful",
    "data": {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer"
    }
}
```

**错误响应**:

| 状态码 | 说明 |
|--------|------|
| 404 | 用户不存在或密码错误 |
| 404 | 用户已禁用 |

---

## 用户接口 (Users)

### GET /users/me

获取当前登录用户信息。

**认证**: 需要

**请求示例**:

```bash
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer <access_token>"
```

**成功响应**: `200 OK`

```json
{
    "success": true,
    "message": "",
    "data": {
        "id": 1,
        "email": "user@example.com",
        "username": "johndoe",
        "full_name": "John Doe",
        "is_active": true,
        "is_superuser": false,
        "created_at": "2026-03-24T10:00:00Z",
        "updated_at": "2026-03-24T10:00:00Z"
    }
}
```

---

### GET /users/{user_id}

根据 ID 获取用户信息。

**认证**: 需要

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| user_id | integer | 用户 ID |

**请求示例**:

```bash
curl -X GET http://localhost:8000/api/v1/users/1 \
  -H "Authorization: Bearer <access_token>"
```

**成功响应**: `200 OK`

```json
{
    "success": true,
    "message": "",
    "data": {
        "id": 1,
        "email": "user@example.com",
        "username": "johndoe",
        "full_name": "John Doe",
        "is_active": true,
        "is_superuser": false,
        "created_at": "2026-03-24T10:00:00Z",
        "updated_at": "2026-03-24T10:00:00Z"
    }
}
```

**错误响应**:

| 状态码 | 说明 |
|--------|------|
| 404 | 用户不存在 |
| 401 | 未认证 |
| 403 | 无权限 |

---

### GET /users/

获取用户列表（分页）。

**认证**: 需要超级管理员权限

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | integer | 1 | 页码 |
| page_size | integer | 10 | 每页数量 |

**请求示例**:

```bash
curl -X GET "http://localhost:8000/api/v1/users/?page=1&page_size=10" \
  -H "Authorization: Bearer <admin_access_token>"
```

**成功响应**: `200 OK`

```json
{
    "success": true,
    "message": "Users retrieved successfully",
    "data": [
        {
            "id": 1,
            "email": "user1@example.com",
            "username": "user1",
            "full_name": "User One",
            "is_active": true,
            "is_superuser": false,
            "created_at": "2026-03-24T10:00:00Z",
            "updated_at": "2026-03-24T10:00:00Z"
        },
        {
            "id": 2,
            "email": "user2@example.com",
            "username": "user2",
            "full_name": "User Two",
            "is_active": true,
            "is_superuser": false,
            "created_at": "2026-03-24T11:00:00Z",
            "updated_at": "2026-03-24T11:00:00Z"
        }
    ],
    "total": 25,
    "page": 1,
    "page_size": 10,
    "total_pages": 3
}
```

**错误响应**:

| 状态码 | 说明 |
|--------|------|
| 401 | 未认证 |
| 403 | 需要超级管理员权限 |

---

### PUT /users/{user_id}

更新用户信息。

**认证**: 需要（普通用户只能更新自己的信息）

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| user_id | integer | 用户 ID |

**请求体** (所有字段可选):

| 字段 | 类型 | 说明 |
|------|------|------|
| email | string | 邮箱地址 |
| username | string | 用户名 |
| full_name | string | 全名 |
| password | string | 新密码 |
| is_active | boolean | 是否激活 |

**请求示例**:

```bash
curl -X PUT http://localhost:8000/api/v1/users/1 \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Updated"
  }'
```

**成功响应**: `200 OK`

```json
{
    "success": true,
    "message": "User updated successfully",
    "data": {
        "id": 1,
        "email": "user@example.com",
        "username": "johndoe",
        "full_name": "John Updated",
        "is_active": true,
        "is_superuser": false,
        "created_at": "2026-03-24T10:00:00Z",
        "updated_at": "2026-03-24T12:00:00Z"
    }
}
```

**错误响应**:

| 状态码 | 说明 |
|--------|------|
| 403 | 无权限（非管理员不能修改其他用户） |
| 404 | 用户不存在 |
| 409 | 邮箱或用户名已存在 |

---

### DELETE /users/{user_id}

删除用户。

**认证**: 需要超级管理员权限

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| user_id | integer | 用户 ID |

**请求示例**:

```bash
curl -X DELETE http://localhost:8000/api/v1/users/1 \
  -H "Authorization: Bearer <admin_access_token>"
```

**成功响应**: `204 No Content`

**错误响应**:

| 状态码 | 说明 |
|--------|------|
| 401 | 未认证 |
| 403 | 需要超级管理员权限 |
| 404 | 用户不存在 |

---

## 请求/响应格式

### 通用响应模型

**DataResponse[T]** - 单个资源响应:

```python
class DataResponse[T](ResponseBase):
    data: T
```

**PaginatedResponse[T]** - 分页列表响应:

```python
class PaginatedResponse[T](ListResponse[T]):
    total: int
    page: int
    page_size: int
    total_pages: int
```

### 请求头

| 头字段 | 说明 | 示例 |
|--------|------|------|
| Content-Type | 请求体格式 | `application/json` |
| Authorization | 认证令牌 | `Bearer eyJhbGci...` |

---

## 错误处理

### 错误状态码

| 状态码 | 说明 | 使用场景 |
|--------|------|----------|
| 400 | Bad Request | 请求格式错误 |
| 401 | Unauthorized | 未认证或令牌无效 |
| 403 | Forbidden | 无权限 |
| 404 | Not Found | 资源不存在 |
| 409 | Conflict | 资源冲突（重复） |
| 422 | Unprocessable Entity | 验证失败 |
| 500 | Internal Server Error | 服务器错误 |

### 错误响应格式

```json
{
    "detail": "Human readable error message",
    "status_code": 409,
    "error_type": "ConflictException"
}
```

### 常见错误示例

**401 未认证**:
```json
{
    "detail": "Could not validate credentials"
}
```

**403 权限不足**:
```json
{
    "detail": "The user doesn't have enough privileges"
}
```

**404 资源不存在**:
```json
{
    "detail": "User 999 not found"
}
```

**409 资源冲突**:
```json
{
    "detail": "Email user@example.com already registered"
}
```

---

## 分页查询

### 请求参数

| 参数 | 类型 | 默认值 | 最小值 | 最大值 |
|------|------|--------|--------|--------|
| page | integer | 1 | 1 | - |
| page_size | integer | 10 | 1 | 100 |

### 计算公式

```python
skip = (page - 1) * page_size
limit = page_size
total_pages = ceil(total / page_size)
```

### 响应字段

| 字段 | 类型 | 说明 |
|------|------|------|
| total | integer | 总记录数 |
| page | integer | 当前页码 |
| page_size | integer | 每页数量 |
| total_pages | integer | 总页数 |

---

## API 索引

### 认证相关

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | /auth/register | 用户注册 | 否 |
| POST | /auth/login | 用户登录 | 否 |

### 用户相关

| 方法 | 路径 | 说明 | 认证 | 权限 |
|------|------|------|------|------|
| GET | /users/me | 获取当前用户 | 是 | 用户本人 |
| GET | /users/{id} | 获取指定用户 | 是 | 用户本人/管理员 |
| GET | /users/ | 用户列表 | 是 | 管理员 |
| PUT | /users/{id} | 更新用户 | 是 | 用户本人/管理员 |
| DELETE | /users/{id} | 删除用户 | 是 | 管理员 |

---

## 测试接口

### 使用 cURL

```bash
# 1. 注册用户
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "username": "testuser", "password": "Test1234"}'

# 2. 登录获取令牌
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "Test1234"}' | jq -r '.data.access_token')

# 3. 使用令牌获取用户信息
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer $TOKEN"
```

### 使用 Python

```python
import httpx

BASE_URL = "http://localhost:8000/api/v1"

# 注册
response = httpx.post(f"{BASE_URL}/auth/register", json={
    "email": "test@example.com",
    "username": "testuser",
    "password": "Test1234"
})
print(response.json())

# 登录
response = httpx.post(f"{BASE_URL}/auth/login", json={
    "username": "testuser",
    "password": "Test1234"
})
token = response.json()["data"]["access_token"]

# 获取用户信息
headers = {"Authorization": f"Bearer {token}"}
response = httpx.get(f"{BASE_URL}/users/me", headers=headers)
print(response.json())
```

---

> 文档版本: 1.0.0
> 更新时间: 2026-03-24