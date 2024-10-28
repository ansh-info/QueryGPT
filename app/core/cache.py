from cachetools import TTLCache, LRUCache
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self):
        # Cache for query responses (1 hour TTL)
        self.response_cache = TTLCache(maxsize=1000, ttl=3600)
        # Cache for embeddings
        self.embedding_cache = LRUCache(maxsize=10000)
        # Cache for knowledge base summary (5 minutes TTL)
        self.summary_cache = TTLCache(maxsize=1, ttl=300)
        # Cache stats
        self.stats = {
            'hits': 0,
            'misses': 0,
            'start_time': datetime.now()
        }

    def get_cached_response(self, query: str) -> Optional[Dict[str, Any]]:
        """Get cached response for a query"""
        cached = self.response_cache.get(query)
        if cached:
            self.stats['hits'] += 1
            logger.debug(f"Cache hit for query: {query}")
            return cached
        self.stats['misses'] += 1
        logger.debug(f"Cache miss for query: {query}")
        return None

    def cache_response(self, query: str, response: Dict[str, Any]):
        """Cache a query response"""
        try:
            self.response_cache[query] = response
            logger.debug(f"Cached response for query: {query}")
        except Exception as e:
            logger.error(f"Error caching response: {str(e)}")

    def get_cached_embedding(self, text: str) -> Optional[list]:
        """Get cached embedding for text"""
        return self.embedding_cache.get(text)

    def cache_embedding(self, text: str, embedding: list):
        """Cache an embedding"""
        try:
            self.embedding_cache[text] = embedding
        except Exception as e:
            logger.error(f"Error caching embedding: {str(e)}")

    def get_cached_summary(self) -> Optional[Dict[str, Any]]:
        """Get cached knowledge base summary"""
        return self.summary_cache.get('summary')

    def cache_summary(self, summary: Dict[str, Any]):
        """Cache knowledge base summary"""
        try:
            self.summary_cache['summary'] = summary
        except Exception as e:
            logger.error(f"Error caching summary: {str(e)}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.stats['hits'] + self.stats['misses']
        return {
            'response_cache_size': len(self.response_cache),
            'embedding_cache_size': len(self.embedding_cache),
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'hit_rate': self.stats['hits'] / total if total > 0 else 0,
            'uptime': (datetime.now() - self.stats['start_time']).total_seconds()
        }

    def clear_caches(self):
        """Clear all caches"""
        self.response_cache.clear()
        self.embedding_cache.clear()
        self.summary_cache.clear()
        logger.info("All caches cleared")