"""OpenTelemetry 分布式追踪配置模块。

该模块提供了完整的可观测性配置，支持:
- OTLP 导出器 (支持 Jaeger/Zipkin/控制台)
- FastAPI/SQLAlchemy/Redis/Celery 自动插桩
- 手动业务追踪
- 日志与追踪关联
"""

import logging
import os
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, TypeVar

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION, DEPLOYMENT_ENVIRONMENT
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.core.config import settings

logger = logging.getLogger(__name__)

# 全局 tracer 实例
_tracer: trace.Tracer | None = None


def get_tracer() -> trace.Tracer:
    """获取全局 tracer 实例。"""
    global _tracer
    if _tracer is None:
        _tracer = trace.get_tracer(__name__)
    return _tracer


def create_resource() -> Resource:
    """创建资源属性，用于标识服务。

    Returns:
        Resource: 包含服务元数据的 OpenTelemetry 资源
    """
    return Resource.create(
        {
            SERVICE_NAME: os.getenv("OTEL_SERVICE_NAME", settings.PROJECT_NAME.replace(" ", "_").lower()),
            SERVICE_VERSION: os.getenv("OTEL_SERVICE_VERSION", "1.0.0"),
            DEPLOYMENT_ENVIRONMENT: os.getenv("OTEL_ENVIRONMENT", settings.APP_ENV),
            "service.namespace": os.getenv("OTEL_SERVICE_NAMESPACE", "enterprise-fastapi"),
            "host.name": os.getenv("HOSTNAME", "unknown"),
        }
    )


def create_otlp_exporter() -> OTLPSpanExporter | None:
    """创建 OTLP gRPC 导出器。

    从环境变量读取端点配置:
    - OTEL_EXPORTER_OTLP_ENDPOINT: OTLP 端点 (默认: http://localhost:4317)
    - OTEL_EXPORTER_OTLP_INSECURE: 是否使用不安全连接

    Returns:
        OTLPSpanExporter 实例，如果配置无效则返回 None
    """
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    insecure = os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "true").lower() == "true"

    try:
        exporter = OTLPSpanExporter(
            endpoint=endpoint,
            insecure=insecure,
        )
        logger.info(f"OTLP exporter configured: endpoint={endpoint}, insecure={insecure}")
        return exporter
    except Exception as e:
        logger.warning(f"Failed to create OTLP exporter: {e}")
        return None


def setup_tracer_provider() -> TracerProvider:
    """配置并初始化 TracerProvider。

    支持多种导出器:
    - OTLP (默认)
    - Jaeger (通过 OTLP)
    - Zipkin (通过 OTLP)
    - Console (用于调试)
    - In-Memory (用于测试)

    Returns:
        TracerProvider: 配置好的 tracer provider
    """
    resource = create_resource()
    provider = TracerProvider(resource=resource)

    # 配置导出器类型
    exporter_type = os.getenv("OTEL_TRACES_EXPORTER", "otlp").lower()

    if exporter_type == "otlp":
        exporter = create_otlp_exporter()
        if exporter:
            processor = BatchSpanProcessor(
                exporter,
                max_queue_size=2048,
                max_export_batch_size=512,
                schedule_delay_millis=5000,
            )
            provider.add_span_processor(processor)
            logger.info("OTLP exporter configured")

    elif exporter_type == "console":
        # 控制台导出器，用于本地调试
        exporter = ConsoleSpanExporter()
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        logger.info("Console exporter configured")

    elif exporter_type == "none" or exporter_type == "":
        # No-op exporter，禁用追踪
        logger.info("Tracing disabled (exporter=none)")

    else:
        logger.warning(f"Unknown exporter type: {exporter_type}, using default")

    # 设置全局 provider
    trace.set_tracer_provider(provider)

    return provider


def instrument_fastapi(app) -> None:
    """为 FastAPI 应用启用自动插桩。

    Args:
        app: FastAPI 应用实例
    """
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls=os.getenv("OTEL_EXCLUDED_URLS", "/health,/health/ready"),
    )
    logger.info("FastAPI instrumented")


def instrument_sqlalchemy(engine) -> None:
    """为 SQLAlchemy 启用自动插桩。

    Args:
        engine: SQLAlchemy 引擎实例
    """
    SQLAlchemyInstrumentor().instrument(
        engine=engine.sync_engine if hasattr(engine, "sync_engine") else engine,
    )
    logger.info("SQLAlchemy instrumented")


def instrument_redis() -> None:
    """为 Redis 启用自动插桩。"""
    RedisInstrumentor().instrument()
    logger.info("Redis instrumented")


def instrument_celery() -> None:
    """为 Celery 启用自动插桩。"""
    CeleryInstrumentor().instrument()
    logger.info("Celery instrumented")


def instrument_logging() -> None:
    """为日志启用追踪关联。

    自动将 trace_id, span_id 注入到日志记录中。
    """
    LoggingInstrumentor().instrument(
        set_logging_format=True,
        log_level=logging.INFO,
    )
    logger.info("Logging instrumented with trace correlation")


def setup_telemetry(app=None, db_engine=None) -> TracerProvider:
    """完整的遥测配置入口。

    Args:
        app: FastAPI 应用实例
        db_engine: SQLAlchemy 数据库引擎

    Returns:
        TracerProvider: 配置好的 tracer provider
    """
    provider = setup_tracer_provider()

    # 启用各组件自动插桩
    if app is not None:
        instrument_fastapi(app)

    if db_engine is not None:
        instrument_sqlalchemy(db_engine)

    instrument_redis()
    instrument_celery()
    instrument_logging()

    # 初始化全局 tracer
    global _tracer
    _tracer = trace.get_tracer(__name__)

    logger.info("Telemetry setup complete")
    return provider


# ============================================================================
# 手动追踪工具函数
# ============================================================================

F = TypeVar("F", bound=Callable[..., Any])


def traced(span_name: str | None = None, attributes: dict[str, Any] | None = None):
    """装饰器：为函数自动创建 span。

    Args:
        span_name: Span 名称，默认为函数名
        attributes: 附加到 span 的属性

    Example:
        @traced(span_name="process_order", attributes={"service": "orders"})
        async def process_order(order_id: int):
            ...
    """

    def decorator(func: F) -> F:
        name = span_name or func.__name__

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(name) as span:
                # 添加属性
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                # 添加函数参数信息（敏感信息除外）
                if args and hasattr(args[0], "__class__"):
                    # 如果是方法调用，添加类名
                    span.set_attribute("class", args[0].__class__.__name__)

                # 记录异常
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                if args and hasattr(args[0], "__class__"):
                    span.set_attribute("class", args[0].__class__.__name__)

                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper  # type: ignore

    return decorator


@contextmanager
def span_context(span_name: str, attributes: dict[str, Any] | None = None):
    """上下文管理器：手动创建 span。

    Args:
        span_name: Span 名称
        attributes: 附加属性

    Example:
        with span_context("database_operation", {"operation": "select"}) as span:
            result = await db.query(...)
            span.set_attribute("row_count", len(result))
    """
    tracer = get_tracer()
    with tracer.start_as_current_span(span_name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        yield span


def add_span_attributes(**kwargs) -> None:
    """为当前 span 添加属性。

    Example:
        add_span_attributes(user_id="123", action="create_order")
    """
    span = trace.get_current_span()
    if span and span.is_recording():
        for key, value in kwargs.items():
            span.set_attribute(key, value)


def add_event(name: str, attributes: dict[str, Any] | None = None) -> None:
    """为当前 span 添加事件。

    Example:
        add_event("cache_miss", {"cache_key": "user:123"})
    """
    span = trace.get_current_span()
    if span and span.is_recording():
        span.add_event(name, attributes or {})


def set_span_error(exception: Exception) -> None:
    """将当前 span 标记为错误状态。

    Args:
        exception: 异常实例
    """
    span = trace.get_current_span()
    if span and span.is_recording():
        span.record_exception(exception)
        span.set_status(trace.Status(trace.StatusCode.ERROR, str(exception)))


# 导入 asyncio 用于检测异步函数
import asyncio
