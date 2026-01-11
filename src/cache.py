"""In-memory cache with TTL for fetched specs and namespace graphs."""

import time
from typing import Any, Optional


class InMemoryCache:
    """Simple TTL cache for fetched specs and namespace graphs."""

    def __init__(self, ttl: int = 86400):
        self._store: dict[str, tuple[float, Any]] = {}
        self.ttl = ttl

    def get(self, key: str) -> Optional[Any]:
        """Get value if exists and not expired."""
        if key not in self._store:
            return None
        timestamp, value = self._store[key]
        if time.time() - timestamp > self.ttl:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        """Store value with current timestamp."""
        self._store[key] = (time.time(), value)

    def clear(self) -> None:
        """Clear all cached entries."""
        self._store.clear()


cache = InMemoryCache()
