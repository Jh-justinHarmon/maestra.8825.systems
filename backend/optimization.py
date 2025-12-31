"""
Maestra Backend - Optimization Layer

Implements caching, speculative execution, and performance optimization
to achieve <300ms end-to-end latency.

Strategies:
- Query result caching (LRU, TTL-based)
- Speculative prefetch (predict next queries)
- Parallel execution (fire requests in parallel)
- Response streaming (send results as they arrive)
- Index preloading (warm caches on startup)
"""

import logging
import asyncio
import hashlib
import time
from typing import Dict, Optional, Any, Callable, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from collections import OrderedDict

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Single cache entry with TTL."""
    key: str
    value: Any
    created_at: float
    ttl_seconds: int
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return time.time() - self.created_at > self.ttl_seconds
    
    def touch(self) -> None:
        """Update last access time."""
        self.last_accessed = time.time()
        self.access_count += 1

class LRUCache:
    """LRU cache with TTL support."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self.cache:
            self.misses += 1
            return None
        
        entry = self.cache[key]
        if entry.is_expired():
            del self.cache[key]
            self.misses += 1
            return None
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        entry.touch()
        self.hits += 1
        return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        ttl = ttl or self.default_ttl
        
        if key in self.cache:
            self.cache.move_to_end(key)
        
        self.cache[key] = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            ttl_seconds=ttl
        )
        
        # Evict oldest if over capacity
        if len(self.cache) > self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            logger.debug(f"Evicted cache entry: {oldest_key}")
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "total_requests": total
        }

class SpeculativeExecutor:
    """Predicts and pre-executes likely next queries."""
    
    def __init__(self):
        self.query_patterns: Dict[str, List[str]] = {}
        self.cache = LRUCache(max_size=500, default_ttl=600)
    
    def record_query_sequence(self, current_query: str, next_query: str) -> None:
        """Record a query sequence for pattern learning."""
        if current_query not in self.query_patterns:
            self.query_patterns[current_query] = []
        
        if next_query not in self.query_patterns[current_query]:
            self.query_patterns[current_query].append(next_query)
        
        logger.debug(f"Recorded pattern: {current_query} → {next_query}")
    
    def predict_next_queries(self, current_query: str, top_k: int = 3) -> List[str]:
        """Predict likely next queries."""
        if current_query not in self.query_patterns:
            return []
        
        return self.query_patterns[current_query][:top_k]
    
    async def speculative_prefetch(
        self,
        current_query: str,
        fetch_fn: Callable,
        top_k: int = 2
    ) -> Dict[str, Any]:
        """Prefetch results for predicted next queries."""
        predictions = self.predict_next_queries(current_query, top_k)
        
        if not predictions:
            return {}
        
        prefetch_results = {}
        
        # Fire prefetch requests in parallel (non-blocking)
        tasks = []
        for predicted_query in predictions:
            cache_key = self._make_cache_key(predicted_query)
            
            # Skip if already cached
            if self.cache.get(cache_key):
                continue
            
            task = asyncio.create_task(
                self._prefetch_one(predicted_query, fetch_fn, cache_key)
            )
            tasks.append((predicted_query, task))
        
        # Collect results (don't wait for all - return what we have)
        for predicted_query, task in tasks:
            try:
                result = await asyncio.wait_for(task, timeout=0.5)
                prefetch_results[predicted_query] = result
            except asyncio.TimeoutError:
                logger.debug(f"Prefetch timeout for: {predicted_query}")
            except Exception as e:
                logger.debug(f"Prefetch error for {predicted_query}: {e}")
        
        return prefetch_results
    
    async def _prefetch_one(
        self,
        query: str,
        fetch_fn: Callable,
        cache_key: str
    ) -> Any:
        """Prefetch a single query result."""
        try:
            result = await fetch_fn(query)
            self.cache.set(cache_key, result, ttl=600)
            logger.debug(f"Prefetched: {query}")
            return result
        except Exception as e:
            logger.debug(f"Prefetch failed for {query}: {e}")
            return None
    
    def _make_cache_key(self, query: str) -> str:
        """Generate cache key for query."""
        return f"query:{hashlib.md5(query.encode()).hexdigest()}"

class ResponseStreamer:
    """Streams response results as they arrive."""
    
    @staticmethod
    async def stream_results(
        result_generators: List[Callable],
        timeout_per_result: float = 0.1
    ) -> List[Any]:
        """Stream results from multiple generators."""
        results = []
        
        for gen in result_generators:
            try:
                result = await asyncio.wait_for(gen(), timeout=timeout_per_result)
                results.append(result)
            except asyncio.TimeoutError:
                logger.debug("Result streaming timeout")
                break
            except Exception as e:
                logger.debug(f"Result streaming error: {e}")
        
        return results

class PerformanceMonitor:
    """Monitors and tracks performance metrics."""
    
    def __init__(self):
        self.request_times: Dict[str, List[float]] = {}
        self.error_counts: Dict[str, int] = {}
    
    def record_request(self, endpoint: str, duration_ms: float) -> None:
        """Record request duration."""
        if endpoint not in self.request_times:
            self.request_times[endpoint] = []
        
        self.request_times[endpoint].append(duration_ms)
        
        # Keep only last 100 requests per endpoint
        if len(self.request_times[endpoint]) > 100:
            self.request_times[endpoint] = self.request_times[endpoint][-100:]
    
    def record_error(self, endpoint: str) -> None:
        """Record error."""
        if endpoint not in self.error_counts:
            self.error_counts[endpoint] = 0
        self.error_counts[endpoint] += 1
    
    def get_stats(self, endpoint: str) -> Dict[str, Any]:
        """Get performance stats for endpoint."""
        if endpoint not in self.request_times:
            return {"error": "No data"}
        
        times = self.request_times[endpoint]
        if not times:
            return {"error": "No data"}
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        p95_time = sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else times[0]
        
        errors = self.error_counts.get(endpoint, 0)
        error_rate = (errors / (len(times) + errors) * 100) if (len(times) + errors) > 0 else 0
        
        return {
            "endpoint": endpoint,
            "avg_ms": f"{avg_time:.1f}",
            "min_ms": f"{min_time:.1f}",
            "max_ms": f"{max_time:.1f}",
            "p95_ms": f"{p95_time:.1f}",
            "requests": len(times),
            "errors": errors,
            "error_rate": f"{error_rate:.1f}%",
            "target_met": avg_time < 300
        }

# Global instances
cache = LRUCache(max_size=1000, default_ttl=300)
speculative_executor = SpeculativeExecutor()
response_streamer = ResponseStreamer()
performance_monitor = PerformanceMonitor()

def cached_query(ttl: int = 300):
    """Decorator for caching query results."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Generate cache key from function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            cache_key = hashlib.md5(cache_key.encode()).hexdigest()
            
            # Check cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit: {func.__name__}")
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            cache.set(cache_key, result, ttl=ttl)
            return result
        
        return wrapper
    return decorator

def monitored_endpoint(endpoint_name: str):
    """Decorator for monitoring endpoint performance."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                performance_monitor.record_request(endpoint_name, duration_ms)
                logger.info(f"{endpoint_name}: {duration_ms:.1f}ms")
                return result
            except Exception as e:
                performance_monitor.record_error(endpoint_name)
                raise
        
        return wrapper
    return decorator

def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    return cache.get_stats()

def get_performance_stats(endpoint: str) -> Dict[str, Any]:
    """Get performance statistics for endpoint."""
    return performance_monitor.get_stats(endpoint)

def clear_cache() -> None:
    """Clear all caches."""
    cache.clear()
    logger.info("Cache cleared")
