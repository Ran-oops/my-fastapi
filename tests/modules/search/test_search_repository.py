import pytest

from app.modules.search.repository import SearchRepository


@pytest.mark.asyncio
class TestSearchRepositorySaveHistory:
    async def test_save_search_history(self, session, test_user):
        repo = SearchRepository(session)
        history = await repo.save_search_history(
            user_id=test_user.id, query="test query", search_type="products", result_count=5
        )
        assert history.id is not None
        assert history.user_id == test_user.id
        assert history.query == "test query"
        assert history.search_type == "products"
        assert history.result_count == 5

    async def test_save_search_history_capped_at_100(self, session, test_user):
        repo = SearchRepository(session)
        for i in range(105):
            await repo.save_search_history(
                user_id=test_user.id, query=f"query_{i}", search_type="products", result_count=i
            )
        histories, total = await repo.get_search_history(test_user.id)
        assert total <= 100


@pytest.mark.asyncio
class TestSearchRepositoryGetHistory:
    async def test_get_search_history(self, session, test_user):
        repo = SearchRepository(session)
        for i in range(5):
            await repo.save_search_history(
                user_id=test_user.id, query=f"history_{i}", search_type="products", result_count=i
            )
        histories, total = await repo.get_search_history(test_user.id)
        assert len(histories) >= 5
        assert total >= 5

    async def test_get_search_history_empty(self, session, test_user):
        repo = SearchRepository(session)
        histories, total = await repo.get_search_history(test_user.id)
        assert len(histories) == 0
        assert total == 0


@pytest.mark.asyncio
class TestSearchRepositoryDeleteHistory:
    async def test_delete_search_history_success(self, session, test_user):
        repo = SearchRepository(session)
        history = await repo.save_search_history(
            user_id=test_user.id, query="to delete", search_type="products", result_count=1
        )
        result = await repo.delete_search_history(test_user.id, history.id)
        assert result is True

    async def test_delete_search_history_not_found(self, session, test_user):
        repo = SearchRepository(session)
        result = await repo.delete_search_history(test_user.id, 99999)
        assert result is False


@pytest.mark.asyncio
class TestSearchRepositoryClearHistory:
    async def test_clear_search_history(self, session, test_user):
        repo = SearchRepository(session)
        for i in range(5):
            await repo.save_search_history(
                user_id=test_user.id, query=f"clear_{i}", search_type="products", result_count=i
            )
        deleted = await repo.clear_search_history(test_user.id)
        assert deleted >= 5
        histories, total = await repo.get_search_history(test_user.id)
        assert total == 0
