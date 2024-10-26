from cachetools import TTLCache, LRUCache
from core.config import settings
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self):
        self.response_cache = TTLCache(
            maxsize=settings.CACHE_MAXSIZE, 
            ttl=settings.CACHE_TTL
        )
        self.embedding_cache = LRUCache(maxsize=settings.CACHE_MAXSIZE)
    
    def get_cached_response(self, query: str):
        return self.response_cache.get(query)
    
    def cache_response(self, query: str, response: dict):
        try:
            self.response_cache[query] = response
        except Exception as e:
            logger.error(f"Error caching response: {str(e)}")
    
    def get_cached_embedding(self, text: str):
        return self.embedding_cache.get(text)
    
    def cache_embedding(self, text: str, embedding: list):
        try:
            self.embedding_cache[text] = embedding
        except Exception as e:
            logger.error(f"Error caching embedding: {str(e)}")