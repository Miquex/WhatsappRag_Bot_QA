from cachetools import TTLCache
from typing import List, Dict
from loguru import logger

class MemoryManager:

    def __init__(self, maxsize: int=300, ttl_seconds: int=600):
        self.memory_store = TTLCache(maxsize=maxsize, ttl=ttl_seconds)
        self.max_history_length = 6

    def add_message(self, phone_number: str, role: str, content: str):
        if phone_number not in self.memory_store:
            self.memory_store[phone_number] = []
        history = self.memory_store[phone_number]
        history.append({'role': role, 'content': content})
        if len(history) > self.max_history_length:
            self.memory_store[phone_number] = history[-self.max_history_length:]

    def get_history(self, phone_number: str) -> List[Dict[str, str]]:
        return self.memory_store.get(phone_number, [])

    def clear_history(self, phone_number: str):
        if phone_number in self.memory_store:
            del self.memory_store[phone_number]
memory_manager = MemoryManager()
