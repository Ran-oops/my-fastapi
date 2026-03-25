from unittest.mock import MagicMock, patch


def test_cancel_timeout_skips_non_pending():
    """Test that cancel_timeout skips orders that are not PENDING."""
    from app.modules.orders.models import OrderStatus
    from app.modules.orders.tasks import cancel_timeout

    mock_order = MagicMock()
    mock_order.status = OrderStatus.CONFIRMED.value
    mock_order.id = 1

    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = mock_order

    with patch("app.modules.orders.tasks.get_sync_session", return_value=iter([mock_session])):
        result = cancel_timeout(1)
        assert result["skipped"] is True
        assert "CONFIRMED" in result["reason"]


def test_cancel_timeout_cancels_pending_order():
    """Test that cancel_timeout cancels PENDING orders."""
    from app.modules.orders.models import OrderStatus
    from app.modules.orders.tasks import cancel_timeout

    mock_order = MagicMock()
    mock_order.status = OrderStatus.PENDING.value
    mock_order.id = 1

    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = mock_order

    with patch("app.modules.orders.tasks.get_sync_session", return_value=iter([mock_session])):
        result = cancel_timeout(1)
        assert result["cancelled"] is True
        assert result["order_id"] == 1
        mock_session.commit.assert_called_once()
