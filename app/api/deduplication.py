from cachetools import TTLCache
from loguru import logger


class WebhookDeduplicator:
    """Manages the prevention of duplicate webhook processing.

    This class uses a TTL-based cache to store processed message IDs, ensuring
    that the same message is not processed multiple times within a short duration.

    Attributes:
        processed_messages (TTLCache): A cache storing IDs of previously
            processed messages.
    """

    processed_messages: TTLCache

    def __init__(self, maxsize: int = 5000, ttl_seconds: int = 300) -> None:
        """Initializes the deduplicator with cache constraints.

        Args:
            maxsize (int): The maximum number of message IDs to store.
                Defaults to 5000.
            ttl_seconds (int): The time-to-live for cached IDs in seconds.
                Defaults to 300.
        """
        self.processed_messages = TTLCache(maxsize=maxsize, ttl=ttl_seconds)

    def is_duplicate(self, message_id: str) -> bool:
        """Checks if a message ID has already been seen and caches it if not.

        Args:
            message_id (str): The unique identifier of the incoming message.

        Returns:
            bool: True if the message is a duplicate, False otherwise.
        """
        if message_id in self.processed_messages:
            logger.warning(f'♻️ Duplicate webhook detected and prevented: {message_id}')
            return True
        self.processed_messages[message_id] = True
        return False


deduplicator: WebhookDeduplicator = WebhookDeduplicator()
