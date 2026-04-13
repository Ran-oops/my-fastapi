"""Dependency Injection Container for the Enterprise FastAPI Application.

This module defines the DI container using the dependency-injector library.
It provides centralized configuration for all application dependencies including:
- Database sessions
- Repositories (Users, Roles, Orders, Products, etc.)
- Services (UserService, RoleService, OrderService, ProductService, etc.)
- External services (Redis, Cache, Search, etc.)

Example:
    from app.core.container import Container

    container = Container()
    container.wire(modules=["app.api.deps"])

    # Access dependencies
    user_service = container.user_service()
"""

from dependency_injector import containers, providers

from app.core.config import settings
from app.db.session import get_session
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.service import (
    create_user,
    update_user,
    delete_user,
    get_user_by_id,
    get_user_by_email,
    get_users,
    get_users_count,
    authenticate_user,
    login_user,
    refresh_access_token,
)
from app.modules.roles.models import Role, Permission
from app.modules.roles.repository import RoleRepository, PermissionRepository
from app.modules.roles.service import (
    create_role,
    update_role,
    delete_role,
    get_role_by_id,
    get_roles,
    get_roles_count,
    assign_role_to_user,
    remove_role_from_user,
    get_user_roles,
    check_user_permission,
    create_permission,
    update_permission,
    delete_permission,
    get_permission_by_id,
    get_permissions,
    get_permissions_count,
    get_role_permissions,
)
from app.modules.orders.models import Order
from app.modules.orders.repository import OrderRepository
from app.modules.orders.service import (
    get_order_by_id,
    get_order_with_items,
    get_orders,
    get_orders_by_user,
    get_orders_by_status,
    get_orders_count,
    get_orders_count_by_user,
    get_orders_count_by_status,
    create_order,
    update_order_status,
    delete_order,
)
from app.modules.products.models import Product
from app.modules.products.repository import ProductRepository
from app.modules.products.service import (
    get_product_by_id,
    get_product_by_sku,
    get_products,
    get_products_by_category,
    get_products_count,
    get_products_count_by_category,
    create_product,
    update_product,
    delete_product,
)
from app.modules.audit.models import AuditLog
from app.modules.audit.repository import AuditLogRepository
from app.modules.audit.service import (
    get_audit_log_by_id,
    get_audit_logs,
    get_audit_logs_by_user,
    get_audit_logs_by_action,
    get_audit_logs_count,
    create_audit_log,
)
from app.modules.config.models import SystemConfig
from app.modules.config.repository import ConfigRepository
from app.modules.config.service import (
    get_config_by_key,
    get_config_value,
    get_configs,
    set_config,
    delete_config,
)
from app.modules.notifications.models import Notification
from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.service import (
    get_notification_by_id,
    get_notifications,
    get_unread_notifications,
    get_notifications_count,
    create_notification,
    mark_notification_as_read,
    mark_all_notifications_as_read,
)
from app.modules.search.repository import SearchRepository
from app.modules.search.service import (
    search_users,
    search_products,
    search_orders,
    search_all,
)


class DatabaseProvider(providers.Provider):
    """Provider that yields async database sessions.

    This provider wraps the get_session async generator to provide
    database sessions through the dependency injection container.
    """

    def __init__(self, get_session_func):
        self._get_session_func = get_session_func
        super().__init__()

    async def __call__(self):
        async for session in self._get_session_func():
            yield session


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "app.api.deps",
            "app.modules.users.user_router",
            "app.modules.users.auth_router",
            "app.modules.roles.router",
            "app.modules.orders.router",
            "app.modules.products.router",
            "app.modules.audit.router",
            "app.modules.config.router",
            "app.modules.notifications.router",
            "app.modules.search.router",
        ]
    )
    """Main Dependency Injection Container.

    This container defines all application dependencies using declarative syntax.
    Dependencies are organized into categories:
    - config: Application configuration
    - db: Database-related providers
    - repositories: Data access layer
    - services: Business logic layer
    - external: External services (Redis, cache, etc.)

    Usage:
        container = Container()
        container.wire(modules=["app.api.deps", "app.api.v1.router"])

        # In your code:
        from dependency_injector.wiring import Provide, inject

        @inject
        async def my_function(
            user_service=Provide[Container.user_service],
        ):
            pass
    """

    # ==========================================================================
    # Configuration
    # ==========================================================================
    config = providers.Configuration()

    # Initialize configuration from settings
    config.APP_ENV.from_env("APP_ENV", default="development")
    config.DEBUG.from_env("DEBUG", default=True)
    config.SECRET_KEY.from_env("SECRET_KEY", default="")
    config.DATABASE_URL.from_env("DATABASE_URL", default="sqlite+aiosqlite:///./app.db")
    config.CELERY_BROKER_URL.from_env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
    config.CELERY_RESULT_BACKEND.from_env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")

    # ==========================================================================
    # Database Providers
    # ==========================================================================

    # Database session factory - yields AsyncSession
    # Using Factory provider for session-per-request pattern
    db_session = providers.Factory(get_session)

    # ==========================================================================
    # Repository Providers (Singleton - shared across application)
    # ==========================================================================

    # User Repository
    user_repository = providers.Singleton(
        UserRepository,
        model=User,
    )

    # Role Repository
    role_repository = providers.Singleton(
        RoleRepository,
        model=Role,
    )

    # Permission Repository
    permission_repository = providers.Singleton(
        PermissionRepository,
        model=Permission,
    )

    # Order Repository
    order_repository = providers.Singleton(
        OrderRepository,
        model=Order,
    )

    # Product Repository
    product_repository = providers.Singleton(
        ProductRepository,
        model=Product,
    )

    # Audit Log Repository
    audit_log_repository = providers.Singleton(
        AuditLogRepository,
        model=AuditLog,
    )

    # Config Repository
    config_repository = providers.Singleton(
        ConfigRepository,
        model=SystemConfig,
    )

    # Notification Repository
    notification_repository = providers.Singleton(
        NotificationRepository,
        model=Notification,
    )

    # Search Repository - Note: SearchRepository requires a session in constructor
    # This is handled specially in SearchService which creates the repository instance
    # For direct repository access, use the factory with session
    search_repository_factory = providers.Factory(SearchRepository)

    # ==========================================================================
    # Service Providers (Factory - new instance per injection)
    # ==========================================================================

    # User Service functions are stateless, but we can group them
    # For services with dependencies, we use Factory or Singleton
    # Here we provide the functions that can be called directly

    # ==========================================================================
    # External Service Providers
    # ==========================================================================

    # Redis Client (optional - can be enabled/disabled based on config)
    redis_client = providers.Resource(
        # AsyncResource for Redis connection
        # This would be implemented with aioredis or similar
        # For now, it's a placeholder
        None,
    )

    # Cache Manager
    cache_manager = providers.Singleton(
        # Would implement a CacheManager class
        # For now, it's a placeholder
        None,
    )


# Create global container instance
container = Container()


def init_container() -> Container:
    """Initialize and configure the DI container.

    This function wires the container to the specified modules,
    enabling dependency injection throughout the application.

    Returns:
        The configured Container instance

    Example:
        from app.core.container import init_container
        container = init_container()
    """
    # Wire the container to modules that use dependency injection
    container.wire(
        modules=[
            "app.api.deps",
            "app.modules.users.user_router",
            "app.modules.users.auth_router",
            "app.modules.roles.router",
            "app.modules.orders.router",
            "app.modules.products.router",
            "app.modules.audit.router",
            "app.modules.config.router",
            "app.modules.notifications.router",
            "app.modules.search.router",
        ]
    )
    return container


def get_container() -> Container:
    """Get the global container instance.

    Returns:
        The global Container instance
    """
    return container
