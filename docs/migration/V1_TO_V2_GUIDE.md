# v1 到 v2 迁移指南

本文档提供从 API v1 迁移到 v2 的详细指导。

## 快速开始

### 1. 更新基础 URL

将所有 API 调用从 `/api/v1` 改为 `/api/v2`：

```python
# Before
BASE_URL = "https://api.example.com/api/v1"

# After
BASE_URL = "https://api.example.com/api/v2"
```

### 2. 更新文档链接

| v1 | v2 |
|---|---|
| `https://api.example.com/api/v1/docs` | `https://api.example.com/api/v2/docs` |

---

## 端点变更

### 认证模块

#### 登录

**v1:**
```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=user&password=pass
```

**v2:**
```http
POST /api/v2/auth/login
Content-Type: application/json

{
  "username": "user",
  "password": "pass"
}
```

**变更说明：**
- 请求格式从 form-data 改为 JSON
- 响应包含 `request_id` 和 `timestamp`

### 用户模块

#### 获取用户列表

**v1 响应：**
```json
{
  "data": [...],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "total_pages": 5,
  "message": "Users retrieved successfully"
}
```

**v2 响应：**
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "total_pages": 5,
    "has_next": true,
    "has_prev": false
  },
  "message": "Users retrieved successfully",
  "timestamp": "2025-01-15T10:30:00Z",
  "request_id": "req_1234567890"
}
```

**变更说明：**
- 分页字段移至 `pagination` 对象
- 新增 `has_next` 和 `has_prev` 字段
- 添加 `timestamp` 和 `request_id`

### 产品模块

#### 批量创建产品（新增）

**v2 新增：**

```http
POST /api/v2/products/batch
Content-Type: application/json

{
  "items": [
    {"name": "Product 1", "sku": "SKU001", "price": 29.99},
    {"name": "Product 2", "sku": "SKU002", "price": 39.99}
  ]
}
```

**响应：**
```json
{
  "data": {
    "created": 2,
    "failed": 0,
    "results": [...]
  },
  "message": "Batch creation completed",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### 订单模块

#### 高级筛选

**v1:**
```http
GET /api/v1/orders?status=pending
```

**v2:**
```http
GET /api/v2/orders?filter[status]=pending&filter[created_after]=2025-01-01
```

**变更说明：**
- 引入过滤器前缀 `filter[...]`
- 支持复杂筛选条件

---

## 响应格式变更

### 统一响应结构

v2 使用统一的响应结构：

```json
{
  "data": <any>,
  "message": "string",
  "timestamp": "ISO8601",
  "request_id": "string"
}
```

### 分页响应

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "total_pages": 5,
    "has_next": true,
    "has_prev": false
  }
}
```

---

## 错误处理

### 错误响应格式

**v1:**
```json
{
  "detail": "User not found"
}
```

**v2 (RFC 7807):**
```json
{
  "type": "https://api.example.com/errors/not-found",
  "title": "Resource Not Found",
  "status": 404,
  "detail": "User with ID 123 not found",
  "instance": "/api/v2/users/123",
  "timestamp": "2025-01-15T10:30:00Z",
  "request_id": "req_1234567890"
}
```

### 错误代码

| v1 HTTP 状态 | v2 类型 | 说明 |
|-------------|---------|------|
| 400 | `validation-error` | 请求验证失败 |
| 401 | `authentication-error` | 认证失败 |
| 403 | `authorization-error` | 权限不足 |
| 404 | `not-found` | 资源不存在 |
| 409 | `conflict` | 资源冲突 |
| 422 | `unprocessable-entity` | 业务规则验证失败 |
| 429 | `rate-limit` | 请求频率超限 |
| 500 | `internal-error` | 服务器内部错误 |

---

## HTTP 头信息

### 请求头

**v2 新增：**

| 头信息 | 值 | 说明 |
|--------|---|------|
| `X-Request-ID` | UUID | 客户端生成的请求 ID |
| `Accept-Version` | `v2` | 显式指定 API 版本 |

### 响应头

**v2 新增：**

| 头信息 | 值 | 说明 |
|--------|---|------|
| `X-Request-ID` | UUID | 服务器返回的请求 ID |
| `X-RateLimit-Limit` | Number | 请求限制 |
| `X-RateLimit-Remaining` | Number | 剩余请求数 |
| `X-RateLimit-Reset` | Timestamp | 限制重置时间 |

---

## SDK/客户端更新

### Python 示例

**v1:**
```python
import requests

class APIClient:
    def __init__(self, base_url="https://api.example.com/api/v1"):
        self.base_url = base_url
    
    def get_users(self, page=1):
        response = requests.get(f"{self.base_url}/users", params={"page": page})
        return response.json()
```

**v2:**
```python
import requests
from typing import Optional

class APIClient:
    def __init__(self, base_url="https://api.example.com/api/v2"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def get_users(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[dict] = None
    ) -> dict:
        params = {"page": page, "page_size": page_size}
        if filters:
            params.update({f"filter[{k}]": v for k, v in filters.items()})
        
        response = self.session.get(f"{self.base_url}/users", params=params)
        response.raise_for_status()
        
        data = response.json()
        # v2 使用 pagination 对象
        pagination = data.get("pagination", {})
        return {
            "users": data["data"],
            "pagination": pagination,
            "has_more": pagination.get("has_next", False)
        }
    
    def create_products_batch(self, products: list) -> dict:
        """v2 新增批量创建功能"""
        response = self.session.post(
            f"{self.base_url}/products/batch",
            json={"items": products}
        )
        response.raise_for_status()
        return response.json()
```

### JavaScript/TypeScript 示例

**v2:**
```typescript
interface APIResponse<T> {
  data: T;
  message: string;
  timestamp: string;
  request_id: string;
}

interface PaginationInfo {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

class APIClient {
  private baseURL: string = "https://api.example.com/api/v2";
  
  async getUsers(page: number = 1, filters?: Record<string, string>) {
    const params = new URLSearchParams();
    params.append("page", page.toString());
    
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        params.append(`filter[${key}]`, value);
      });
    }
    
    const response = await fetch(`${this.baseURL}/users?${params}`, {
      headers: {
        "Content-Type": "application/json",
        "X-Request-ID": crypto.randomUUID()
      }
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new APIError(error);
    }
    
    const result: APIResponse<User[]> & { pagination: PaginationInfo } = 
      await response.json();
    
    return {
      users: result.data,
      pagination: result.pagination,
      hasMore: result.pagination.has_next
    };
  }
}

class APIError extends Error {
  constructor(public error: any) {
    super(error.detail || error.title || "API Error");
    this.name = "APIError";
  }
}
```

---

## 迁移检查清单

### 准备阶段

- [ ] 审查当前 v1 API 使用情况
- [ ] 识别使用的端点和功能
- [ ] 评估迁移工作量
- [ ] 制定迁移时间表

### 开发阶段

- [ ] 更新基础 URL
- [ ] 修改响应解析逻辑
- [ ] 更新错误处理代码
- [ ] 添加批量操作支持
- [ ] 更新分页逻辑

### 测试阶段

- [ ] 编写 v2 集成测试
- [ ] 验证所有端点功能
- [ ] 测试错误处理
- [ ] 性能测试

### 部署阶段

- [ ] 配置 v2 环境
- [ ] 更新监控和告警
- [ ] 灰度发布
- [ ] 全面切换

---

## 常见问题

### Q: v1 何时停止服务？

A: v1 计划在 **2025年12月31日** 停止服务（Sunset Date）。

### Q: 可以同时使用 v1 和 v2 吗？

A: 可以。在迁移期间，可以同时调用两个版本，但建议尽快完成迁移。

### Q: v2 有哪些新功能？

A: v2 主要新增功能包括：
- 批量操作支持
- 高级筛选
- 改进的分页
- 标准错误格式
- 请求追踪

### Q: 如何报告迁移问题？

A: 请联系 support@example.com 或在 GitHub Issues 中报告。

---

## 获取帮助

- 文档：https://docs.example.com/api/v2
- 支持邮箱：support@example.com
- GitHub Issues：https://github.com/example/enterprise-fastapi/issues
- 迁移支持通道：Slack #api-migration
