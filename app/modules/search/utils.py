from __future__ import annotations


def update_product_search_vector(product) -> None:
    """更新产品搜索向量(SQLite兼容)"""
    parts = []
    if product.name:
        parts.append(product.name)
    if product.sku:
        parts.append(product.sku)
    if product.category:
        parts.append(product.category)
    if product.description:
        parts.append(product.description)
    product.search_vector = " ".join(parts)


def update_order_search_vector(order) -> None:
    """更新订单搜索向量(SQLite兼容)"""
    parts = []
    if order.status:
        parts.append(order.status)
    if order.user_id:
        parts.append(str(order.user_id))
    order.search_vector = " ".join(parts)


def update_user_search_vector(user) -> None:
    """更新用户搜索向量(SQLite兼容)"""
    parts = []
    if user.username:
        parts.append(user.username)
    if user.email:
        parts.append(user.email)
    if user.full_name:
        parts.append(user.full_name)
    user.search_vector = " ".join(parts)
