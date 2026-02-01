"""
MCP Context Adapter — Track 5.2 Implementation

HTTP adapter for calling Sentinel Cloud MCP and converting responses
into ContextSource objects for the Enforcement Kernel.

RESPONSIBILITIES:
- Call Sentinel MCP over HTTP
- Convert responses into ContextSource(type="tool:sentinel")
- Track failures explicitly as required_but_missing
- NEVER swallow errors
- NEVER downgrade failures to memory

INTEGRATION RULES:
- Adapter does NOT decide authority
- Adapter does NOT decide refusal
- Adapter only reports truth to EnforcementKernel

FAILURE BEHAVIOR:
- Timeout / 5xx → mark sentinel as required_but_missing
- Partial results → partial=True (still tool authority)
"""

import os
import logging
import httpx
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

SENTINEL_URL = os.environ.get(
    "SENTINEL_CLOUD_URL",
    "https://sentinel-cloud-8825.fly.dev"
)
SENTINEL_TIMEOUT = float(os.environ.get("SENTINEL_TIMEOUT", "10.0"))


# ─────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────

class SentinelError(Exception):
    """Base exception for Sentinel errors."""
    pass


class SentinelUnavailable(SentinelError):
    """Sentinel service is unavailable (503, timeout, etc.)."""
    pass


class SentinelQueryFailed(SentinelError):
    """Sentinel query failed (4xx, 5xx)."""
    pass


# ─────────────────────────────────────────────
# Context Source (matches enforcement_kernel.py)
# ─────────────────────────────────────────────

@dataclass
class ContextSource:
    """
    Represents a source of context for a response.
    Immutable record of where information came from.
    """
    type: str  # "tool:sentinel", "library", "memory", "system"
    excerpt: str
    confidence: float
    artifact_id: Optional[str] = None
    uri: Optional[str] = None
    timestamp: Optional[str] = None


# ─────────────────────────────────────────────
# Adapter Result
# ─────────────────────────────────────────────

@dataclass
class SentinelResult:
    """Result from Sentinel query."""
    success: bool
    sources: List[ContextSource]
    errors: List[str]
    partial: bool
    required_but_missing: bool = False
    raw_response: Optional[Dict] = None


# ─────────────────────────────────────────────
# MCP Context Adapter
# ─────────────────────────────────────────────

class MCPContextAdapter:
    """
    Adapter for calling Sentinel Cloud MCP.
    
    Reports facts to EnforcementKernel. Does NOT decide authority or refusal.
    """
    
    def __init__(self, base_url: str = None, timeout: float = None):
        self.base_url = base_url or SENTINEL_URL
        self.timeout = timeout or SENTINEL_TIMEOUT
        self._client = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy-initialize HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout
            )
        return self._client
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Sentinel health."""
        try:
            response = await self.client.get("/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Sentinel health check failed: {e}")
            return {
                "status": "unavailable",
                "db_available": False,
                "artifact_count": 0,
                "error": str(e)
            }
    
    async def is_available(self) -> bool:
        """Check if Sentinel is available."""
        health = await self.health_check()
        return health.get("status") == "healthy"
    
    async def query(
        self,
        query: str,
        max_results: int = 10,
        filters: Optional[Dict] = None,
        required: bool = False
    ) -> SentinelResult:
        """
        Query Sentinel for relevant artifacts.
        
        Args:
            query: The search query
            max_results: Maximum results to return
            filters: Optional filters
            required: If True, failure marks sentinel as required_but_missing
        
        Returns:
            SentinelResult with sources and error information
        """
        logger.info(f"Sentinel query: {query[:50]}... (required={required})")
        
        try:
            response = await self.client.post(
                "/query",
                json={
                    "query": query,
                    "max_results": max_results,
                    "filters": filters or {}
                }
            )
            
            # Handle HTTP errors
            if response.status_code >= 500:
                logger.error(f"Sentinel 5xx error: {response.status_code}")
                return SentinelResult(
                    success=False,
                    sources=[],
                    errors=[f"Sentinel error: HTTP {response.status_code}"],
                    partial=False,
                    required_but_missing=required,
                    raw_response=None
                )
            
            if response.status_code >= 400:
                logger.error(f"Sentinel 4xx error: {response.status_code}")
                return SentinelResult(
                    success=False,
                    sources=[],
                    errors=[f"Sentinel query failed: HTTP {response.status_code}"],
                    partial=False,
                    required_but_missing=required,
                    raw_response=None
                )
            
            # Parse response
            data = response.json()
            
            # Convert artifacts to ContextSource
            sources = []
            for artifact in data.get("artifacts", []):
                sources.append(ContextSource(
                    type="tool:sentinel",
                    excerpt=artifact.get("excerpt", ""),
                    confidence=artifact.get("confidence", 0.5),
                    artifact_id=artifact.get("id"),
                    uri=artifact.get("uri"),
                    timestamp=artifact.get("timestamp")
                ))
            
            logger.info(f"Sentinel returned {len(sources)} sources")
            
            return SentinelResult(
                success=True,
                sources=sources,
                errors=data.get("errors", []),
                partial=data.get("partial", False),
                required_but_missing=False,
                raw_response=data
            )
        
        except httpx.TimeoutException:
            logger.error("Sentinel timeout")
            return SentinelResult(
                success=False,
                sources=[],
                errors=["Sentinel timeout"],
                partial=False,
                required_but_missing=required,
                raw_response=None
            )
        
        except httpx.ConnectError as e:
            logger.error(f"Sentinel connection error: {e}")
            return SentinelResult(
                success=False,
                sources=[],
                errors=[f"Sentinel unavailable: {e}"],
                partial=False,
                required_but_missing=required,
                raw_response=None
            )
        
        except Exception as e:
            logger.error(f"Sentinel query failed: {e}")
            return SentinelResult(
                success=False,
                sources=[],
                errors=[f"Sentinel error: {e}"],
                partial=False,
                required_but_missing=required,
                raw_response=None
            )


# ─────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────

_adapter_instance: Optional[MCPContextAdapter] = None


def get_mcp_adapter() -> MCPContextAdapter:
    """Get singleton MCP adapter instance."""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = MCPContextAdapter()
    return _adapter_instance


# ─────────────────────────────────────────────
# Convenience Functions
# ─────────────────────────────────────────────

async def query_sentinel(
    query: str,
    required: bool = False,
    max_results: int = 10
) -> Tuple[List[ContextSource], List[str], bool]:
    """
    Convenience function to query Sentinel.
    
    Args:
        query: The search query
        required: If True, failure is critical
        max_results: Maximum results
    
    Returns:
        Tuple of (sources, errors, required_but_missing)
    """
    adapter = get_mcp_adapter()
    result = await adapter.query(query, max_results=max_results, required=required)
    return result.sources, result.errors, result.required_but_missing


async def check_sentinel_available() -> bool:
    """Check if Sentinel is available."""
    adapter = get_mcp_adapter()
    return await adapter.is_available()
