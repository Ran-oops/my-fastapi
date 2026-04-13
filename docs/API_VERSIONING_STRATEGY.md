# API 版本管理策略

## 概述

本项目使用 [fastapi-versionizer](https://github.com/alexschimpf/fastapi-versionizer) 实现自动化的 API 版本管理。该方案支持：

- **语义化版本控制**: 主版本.次版本.修订版本 (`major.minor.patch`)
- **自动文档分离**: 每个版本拥有独立的文档端点 (`/api/v1/docs`, `/api/v2/docs`)
- **最新版本别名**: `/api/latest` 自动指向当前最新版本
- **弃用警告机制**: 自动为旧版本 API 添加弃用警告

---

## 版本结构

```
app/api/
├── __init__.py           # API 包初始化
├── versioning.py         # 版本管理配置和工具
├── v1/                   # v1 版本（已弃用）
│   ├── __init__.py       # v1 路由聚合
│   └── ...               # v1 模块路由
└── v2/                   # v2 版本（当前稳定版）
    ├── __init__.py       # v2 路由聚合
    └── ...               # v2 模块路由
```

---

## 版本端点

### 可用端点

| 端点 | 描述 | 状态 |
|------|------|------|
| `/api/v1` | v1 API 基础路径 | 已弃用 |
| `/api/v2` | v2 API 基础路径 | 当前稳定版 |
| `/api/latest` | 最新版本别名 | 指向 v2 |

### 文档端点

| 端点 | 描述 |
|------|------|
| `/api/v1/docs` | v1 Swagger UI 文档 |
| `/api/v1/redoc` | v1 ReDoc 文档 |
| `/api/v2/docs` | v2 Swagger UI 文档 |
| `/api/v2/redoc` | v2 ReDoc 文档 |
| `/api/latest/docs` | 最新版本 Swagger UI |
| `/docs` | 主文档（指向最新版本）|

---

## 配置说明

### Versionizer 配置 (`app/api/versioning.py`)

```python
versionizer = Versionizer(
    app=app,
    prefix_format="/api/v{major}",           # 版本前缀格式
    semantic_version_format="{major}.{minor}.{patch}",  # 语义化版本格式
    latest_prefix="/api/latest",                # 最新版本别名前缀
    include_versions_route=True,                # 包含版本列表端点
    include_main_docs=True,                     # 包含主文档
    sort_routes=True,                           # 自动排序路由
)
```

### 版本注册

```python
# v1 路由（已弃用）
versionizer.register_versioned_routers(
    routers=[v1_router],
    version=(1, 0, 0),
    prefix="/api/v1",
)

# v2 路由（当前）
versionizer.register_versioned_routers(
    routers=[v2_router],
    version=(2, 0, 0),
    prefix="/api/v2",
)
```

---

## 弃用策略

### v1 弃用状态

v1 API 已被标记为**已弃用**，计划在 **2025年12月31日** 正式停止支持（Sunset）。

### 弃用警告机制

1. **Python 警告**: 导入 v1 模块时触发 `DeprecationWarning`
2. **HTTP 响应头**: 访问 v1 端点时自动添加以下响应头：
   - `Deprecation: true`
   - `Sunset: Wed, 31 Dec 2025 23:59:59 GMT`
   - `Link: </api/v2/docs>; rel="successor-version"`

### 代码示例

```python
# v1/__init__.py
import warnings

warnings.warn(
    "API v1 is deprecated and will be removed in a future version. "
    "Please migrate to API v2. See: https://docs.example.com/migration/v1-to-v2",
    DeprecationWarning,
    stacklevel=2,
)

api_router = APIRouter(deprecated=True)
```

---

## 迁移指南

### 从 v1 迁移到 v2

#### 1. 基础 URL 变更

| v1 | v2 |
|---|---|
| `/api/v1/users` | `/api/v2/users` |
| `/api/v1/products` | `/api/v2/products` |
| `/api/v1/orders` | `/api/v2/orders` |

#### 2. 响应格式改进

v2 引入了统一的响应封装格式：

```json
{
  "data": { ... },
  "message": "Success",
  "timestamp": "2025-01-15T10:30:00Z",
  "request_id": "req_1234567890"
}
```

#### 3. 分页改进

v2 使用更标准的分页格式：

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

#### 4. 错误处理改进

v2 采用 RFC 7807 标准的问题详情（Problem Details）格式：

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

#### 5. 批量操作支持

v2 新增批量操作端点：

- `POST /api/v2/products/batch` - 批量创建产品
- `PUT /api/v2/products/batch` - 批量更新产品
- `DELETE /api/v2/products/batch` - 批量删除产品

---

## 版本控制最佳实践

### 何时创建新版本

1. **破坏性变更（Breaking Changes）**
   - 修改现有端点 URL
   - 改变请求/响应格式
   - 删除或重命名字段
   - 改变认证方式

2. **重大功能更新**
   - 引入新的业务逻辑
   - 改变资源关系模型

### 何时不创建新版本

1. **向后兼容的添加**
   - 新增可选参数
   - 新增响应字段
   - 新增端点

2. **Bug 修复**
   - 修复错误行为
   - 性能优化

### 版本生命周期

```
Development → Beta → Current → Deprecated → Sunset → Removed
   ↓            ↓         ↓           ↓         ↓        ↓
  3个月       1个月      6-12月      3-6月      1月      N/A
```

---

## HTTP 头信息

### 请求头

| 头信息 | 说明 |
|--------|------|
| `Accept-Version` | 客户端请求的版本（可选）|

### 响应头

| 头信息 | 说明 |
|--------|------|
| `X-API-Version` | 当前 API 版本 |
| `X-API-Latest-Version` | 最新可用版本 |
| `Deprecation` | 是否已弃用 (`true`/`false`) |
| `Sunset` | 停用日期（如果适用）|
| `Link` | 相关资源链接 |

---

## 测试策略

### 多版本测试

```python
# tests/api/test_versioning.py
async def test_v1_deprecated_headers(client):
    """Test v1 returns deprecation headers."""
    response = await client.get("/api/v1/users")
    assert response.headers.get("Deprecation") == "true"
    assert "Sunset" in response.headers

async def test_v2_current(client):
    """Test v2 does not return deprecation headers."""
    response = await client.get("/api/v2/users")
    assert "Deprecation" not in response.headers

async def test_latest_redirects_to_v2(client):
    """Test /api/latest uses v2."""
    response = await client.get("/api/latest/users")
    assert response.status_code == 200
```

---

## 监控与告警

### 版本使用监控

监控各版本 API 的使用情况，及时发现：

- v1 使用率下降趋势
- v2 采纳率增长趋势
- 错误率变化

### 弃用告警

在 Sunset Date 前设置告警：

- **T-90天**: 警告，通知仍在使用 v1 的客户端
- **T-30天**: 严重警告，升级通知
- **T-7天**: 最终通知，准备停用

---

## 相关文档

- [fastapi-versionizer 文档](https://github.com/alexschimpf/fastapi-versionizer)
- [Semantic Versioning](https://semver.org/)
- [RFC 7807 - Problem Details](https://tools.ietf.org/html/rfc7807)
- [Sunset HTTP Header](https://tools.ietf.org/html/draft-wilde-sunset-header-03)

---

## 更新日志

### 2025-01-15
- 集成 fastapi-versionizer
- 创建 v2 版本结构
- 标记 v1 为已弃用
- 添加自动文档分离

### 计划更新
- [ ] 2025-06-01: 向 v1 用户发送迁移通知
- [ ] 2025-09-01: v1 限制新功能开发
- [ ] 2025-12-31: v1 正式停用（Sunset）
