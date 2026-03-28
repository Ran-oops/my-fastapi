import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.common.pagination import PaginationParams
from app.modules.search.service import SearchService
from app.modules.search.repository import SearchRepository
from app.modules.search.schemas import SearchResponse, SearchSuggestionResponse


@pytest.mark.asyncio
class TestSearchService:
    async def test_search_products_success(self, session, sample_products):
        service = SearchService(session)
        pagination = PaginationParams(page=1, page_size=10)

        response = await service.search(
            query="Product",
            search_type="products",
            user_id=1,
            pagination=pagination,
        )

        assert isinstance(response, SearchResponse)
        assert "products" in response.data
        assert len(response.data["products"]) >= 1
        assert response.meta.query == "Product"
        assert response.meta.search_type == "products"

    async def test_search_all_types(self, session, sample_products, sample_users, sample_order):
        service = SearchService(session)
        pagination = PaginationParams(page=1, page_size=10)

        response = await service.search(
            query="search",
            search_type="all",
            user_id=1,
            pagination=pagination,
        )

        assert isinstance(response, SearchResponse)
        assert "products" in response.data
        assert "users" in response.data
        assert "orders" in response.data
        assert response.meta.total >= 1

    async def test_search_with_filters(self, session, sample_products):
        service = SearchService(session)
        pagination = PaginationParams(page=1, page_size=10)
        filters = {"category": "electronics"}

        response = await service.search(
            query="Product",
            search_type="products",
            user_id=1,
            pagination=pagination,
            filters=filters,
        )

        assert isinstance(response, SearchResponse)
        for item in response.data["products"]:
            assert item.data.get("category") == "electronics"

    async def test_search_invalid_type(self, session):
        service = SearchService(session)
        pagination = PaginationParams(page=1, page_size=10)

        with pytest.raises(ValueError, match="无效的搜索类型"):
            await service.search(
                query="test",
                search_type="invalid",
                user_id=1,
                pagination=pagination,
            )

    async def test_search_empty_query(self, session):
        service = SearchService(session)
        pagination = PaginationParams(page=1, page_size=10)

        with pytest.raises(ValueError, match="搜索关键词不能为空"):
            await service.search(
                query="",
                search_type="products",
                user_id=1,
                pagination=pagination,
            )

    async def test_search_whitespace_query(self, session):
        service = SearchService(session)
        pagination = PaginationParams(page=1, page_size=10)

        with pytest.raises(ValueError, match="搜索关键词不能为空"):
            await service.search(
                query="   ",
                search_type="products",
                user_id=1,
                pagination=pagination,
            )

    async def test_highlight_text(self, session):
        service = SearchService(session)

        result = service._highlight_text("Test Product Name", "product")
        assert "<mark>product</mark>" in result
        assert "Test" in result

    async def test_highlight_text_case_insensitive(self, session):
        service = SearchService(session)

        result = service._highlight_text("Test Product Name", "PRODUCT")
        assert "<mark>PRODUCT</mark>" in result

    async def test_highlight_text_empty(self, session):
        service = SearchService(session)

        result = service._highlight_text("Test", "")
        assert result == "Test"

        result = service._highlight_text("", "test")
        assert result == ""

    async def test_calculate_score(self, session):
        service = SearchService(session)

        class MockItem:
            name = "Test Product"
            sku = "TEST-001"
            description = "A test product description"

        item = MockItem()
        weights = {"name": 1.0, "sku": 0.8, "description": 0.3}

        score = service._calculate_score(item, "Test", weights)
        assert 0 < score <= 1.0

    async def test_calculate_score_no_match(self, session):
        service = SearchService(session)

        class MockItem:
            name = "Different"
            sku = "OTHER-001"

        item = MockItem()
        weights = {"name": 1.0, "sku": 0.8}

        score = service._calculate_score(item, "xyz", weights)
        assert score == 0.0


@pytest.mark.asyncio
class TestSearchServiceSuggestions:
    async def test_suggest_returns_results(self, session, sample_products):
        service = SearchService(session)

        response = await service.suggest(
            query="Prod",
            search_type="products",
            limit=5,
        )

        assert isinstance(response, SearchSuggestionResponse)
        assert len(response.data) <= 5

    async def test_suggest_too_short_query(self, session):
        service = SearchService(session)

        response = await service.suggest(
            query="P",
            search_type="products",
            limit=5,
        )

        assert isinstance(response, SearchSuggestionResponse)
        assert len(response.data) == 0


@pytest.mark.asyncio
class TestSearchServiceHistory:
    async def test_get_history_empty(self, session, test_user):
        service = SearchService(session)
        pagination = PaginationParams(page=1, page_size=10)

        result = await service.get_history(test_user.id, pagination)

        assert "data" in result
        assert "total" in result
        assert isinstance(result["data"], list)

    async def test_get_history_with_records(self, session, test_user, sample_products):
        service = SearchService(session)
        pagination = PaginationParams(page=1, page_size=10)

        await service.search(
            query="Product",
            search_type="products",
            user_id=test_user.id,
            pagination=pagination,
        )

        result = await service.get_history(test_user.id, pagination)

        assert result["total"] >= 1
        assert len(result["data"]) >= 1

    async def test_delete_history(self, session, test_user, sample_products):
        service = SearchService(session)
        pagination = PaginationParams(page=1, page_size=10)

        await service.search(
            query="Product",
            search_type="products",
            user_id=test_user.id,
            pagination=pagination,
        )

        history_result = await service.get_history(test_user.id, pagination)
        if history_result["data"]:
            history_id = history_result["data"][0].id
            deleted = await service.delete_history(test_user.id, history_id)
            assert deleted is True

    async def test_delete_history_not_found(self, session, test_user):
        service = SearchService(session)

        deleted = await service.delete_history(test_user.id, 99999)
        assert deleted is False

    async def test_clear_history(self, session, test_user, sample_products):
        service = SearchService(session)
        pagination = PaginationParams(page=1, page_size=10)

        await service.search(
            query="Product",
            search_type="products",
            user_id=test_user.id,
            pagination=pagination,
        )

        count = await service.clear_history(test_user.id)
        assert count >= 0

        history_result = await service.get_history(test_user.id, pagination)
        assert history_result["total"] == 0
