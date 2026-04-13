from cachetools import TTLCache
from typing import List, Dict
from loguru import logger
from app.core.config import settings
import re

INJECTION_PATTERN = re.compile(
    r'(?i)(ignore|forget|disregard|ignora|olvida)\s+'
    r'(all\s+|todo\s+)?'
    r'(previous|above|prior|anteriores|arriba)\s+'
    r'(instructions|context|rules|instrucciones|contexto|reglas)'
)

ROLE_OVERRIDE_PATTERN = re.compile(
    r'(?i)(you are now|act as|pretend to be|from now on|'
    r'ahora eres|actúa como|de ahora en adelante)'
)

ALLOWED_ROLES = {'user', 'assistant'}


class MemoryManager:
    """Manages per-user conversation history with built-in sanitization.

    Attributes:
        memory_store (TTLCache): TTL-based cache of conversation histories.
        max_history_length (int): Maximum number of messages kept per user.
    """

    def __init__(self, maxsize: int = 300, ttl_seconds: int = 600) -> None:
        self.memory_store: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl_seconds)
        self.max_history_length: int = 6

    def _sanitize_content(self, content: str) -> str:
        """Sanitizes message content before storing it in history.

        Args:
            content (str): The raw message content.

        Returns:
            str: The sanitized content, truncated and stripped of injection patterns.
        """
        content = content[:settings.MAX_USER_INPUT_LENGTH]
        content = INJECTION_PATTERN.sub('', content)
        content = ROLE_OVERRIDE_PATTERN.sub('', content)
        return content.strip()

    def add_message(self, phone_number: str, role: str, content: str) -> None:
        """Adds a sanitized message to the conversation history.

        Args:
            phone_number (str): The user's phone number.
            role (str): The message role ('user' or 'assistant').
            content (str): The message content to store.
        """
        if role not in ALLOWED_ROLES:
            logger.warning(f'Rejected invalid role: {role}')
            return
        if role == 'user':
            content = self._sanitize_content(content)
        if not content:
            return
        if phone_number not in self.memory_store:
            self.memory_store[phone_number] = []
        history = self.memory_store[phone_number]
        history.append({'role': role, 'content': content})
        if len(history) > self.max_history_length:
            self.memory_store[phone_number] = history[-self.max_history_length:]

    def get_history(self, phone_number: str) -> List[Dict[str, str]]:
        """Returns the conversation history for a user.

        Args:
            phone_number (str): The user's phone number.

        Returns:
            List[Dict[str, str]]: The list of stored messages.
        """
        return self.memory_store.get(phone_number, [])

    def clear_history(self, phone_number: str) -> None:
        """Clears the conversation history for a user.

        Args:
            phone_number (str): The user's phone number.
        """
        if phone_number in self.memory_store:
            del self.memory_store[phone_number]


memory_manager: MemoryManager = MemoryManager()

