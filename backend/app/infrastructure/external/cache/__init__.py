from app.infrastructure.external.cache.postgres_cache import PostgresCache
from functools import lru_cache

@lru_cache()
def get_cache():
    """Get cache implementation"""
    return PostgresCache()

__all__ = ['get_cache', 'PostgresCache']
