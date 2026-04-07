import time
import pytest
from unittest.mock import patch

from app.api.deduplication import WebhookDeduplicator


@pytest.fixture
def deduplicator():
    """Returns a fresh WebhookDeduplicator instance for each test."""
    return WebhookDeduplicator(maxsize=10, ttl_seconds=60)


def test_initial_is_not_duplicate(deduplicator):
    # Arrange
    message_id = "msg_123"
    
    # Act
    result = deduplicator.is_duplicate(message_id)
    
    # Assert
    assert result is False
    assert message_id in deduplicator.processed_messages


def test_subsequent_is_duplicate(deduplicator):
    # Arrange
    message_id = "msg_123"
    deduplicator.is_duplicate(message_id)  # first call caches it
    
    # Act
    result = deduplicator.is_duplicate(message_id)
    
    # Assert
    assert result is True


@patch("app.api.deduplication.logger")
def test_logs_on_duplicate(mock_logger, deduplicator):
    # Arrange
    message_id = "msg_123"
    deduplicator.is_duplicate(message_id)
    
    # Act
    deduplicator.is_duplicate(message_id)
    
    # Assert
    mock_logger.warning.assert_called_once()
    assert "Duplicate webhook detected" in mock_logger.warning.call_args[0][0]


def test_ttl_expiry():
    # Arrange
    # Use a very short TTL to avoid slow tests
    short_ttl_dedup = WebhookDeduplicator(maxsize=10, ttl_seconds=0.1)
    message_id = "msg_ttl"
    
    short_ttl_dedup.is_duplicate(message_id)
    
    # Verify it is initially treated as duplicate
    assert short_ttl_dedup.is_duplicate(message_id) is True
    
    # Act
    time.sleep(0.15)  # Wait for TTL to expire
    
    # Assert
    # After TTL expiry, it should no longer be a duplicate
    result = short_ttl_dedup.is_duplicate(message_id)
    assert result is False


def test_maxsize_eviction():
    # Arrange
    small_dedup = WebhookDeduplicator(maxsize=2, ttl_seconds=60)
    
    # Act
    # Insert 3 different items into a cache that only holds 2
    small_dedup.is_duplicate("msg_1")
    small_dedup.is_duplicate("msg_2")
    small_dedup.is_duplicate("msg_3")
    
    # Assert
    # msg_3 was most recently added
    assert small_dedup.is_duplicate("msg_3") is True
    # msg_2 was added just before, so it's kept
    assert small_dedup.is_duplicate("msg_2") is True
    # msg_1 should have been evicted due to maxsize=2
    assert small_dedup.is_duplicate("msg_1") is False
