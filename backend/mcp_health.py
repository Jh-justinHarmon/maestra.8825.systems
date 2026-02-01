"""
MCP Health Check — Track 5.6 Implementation

Startup validation for MCP availability.

REQUIREMENTS:
- On boot, log MCP availability
- Do NOT crash if unavailable
- Enforcement must still block required usage
"""

import os
import logging
import asyncio
from typing import Dict, Any

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

SENTINEL_URL = os.environ.get(
    "SENTINEL_CLOUD_URL",
    "https://sentinel-cloud-8825.fly.dev"
)


# ─────────────────────────────────────────────
# Health Check Results
# ─────────────────────────────────────────────

_mcp_health_cache: Dict[str, Any] = {
    "sentinel": {
        "available": False,
        "last_check": None,
        "artifact_count": 0,
        "error": None
    }
}


def get_mcp_health() -> Dict[str, Any]:
    """Get cached MCP health status."""
    return _mcp_health_cache.copy()


def is_sentinel_available() -> bool:
    """Check if Sentinel is available (from cache)."""
    return _mcp_health_cache.get("sentinel", {}).get("available", False)


# ─────────────────────────────────────────────
# Startup Health Check
# ─────────────────────────────────────────────

async def check_sentinel_health() -> Dict[str, Any]:
    """
    Check Sentinel health via HTTP.
    
    Returns health status dict. Does NOT raise on failure.
    """
    import httpx
    from datetime import datetime
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{SENTINEL_URL}/health")
            
            if response.status_code == 200:
                data = response.json()
                result = {
                    "available": data.get("status") == "healthy",
                    "last_check": datetime.utcnow().isoformat() + "Z",
                    "artifact_count": data.get("artifact_count", 0),
                    "error": None
                }
            else:
                result = {
                    "available": False,
                    "last_check": datetime.utcnow().isoformat() + "Z",
                    "artifact_count": 0,
                    "error": f"HTTP {response.status_code}"
                }
    except Exception as e:
        from datetime import datetime
        result = {
            "available": False,
            "last_check": datetime.utcnow().isoformat() + "Z",
            "artifact_count": 0,
            "error": str(e)
        }
    
    # Update cache
    _mcp_health_cache["sentinel"] = result
    return result


async def run_startup_health_checks() -> Dict[str, Any]:
    """
    Run all MCP health checks on startup.
    
    Logs results but does NOT crash if unavailable.
    """
    logger.info("🔍 Running MCP health checks...")
    
    results = {}
    
    # Check Sentinel
    sentinel_health = await check_sentinel_health()
    results["sentinel"] = sentinel_health
    
    if sentinel_health["available"]:
        logger.info(
            f"✅ Sentinel: AVAILABLE "
            f"(artifacts: {sentinel_health['artifact_count']})"
        )
    else:
        logger.warning(
            f"⚠️ Sentinel: UNAVAILABLE "
            f"(error: {sentinel_health.get('error', 'unknown')})"
        )
    
    # Summary
    available_count = sum(1 for v in results.values() if v.get("available"))
    total_count = len(results)
    
    logger.info(
        f"📊 MCP Health Summary: {available_count}/{total_count} services available"
    )
    
    if available_count == 0:
        logger.warning(
            "⚠️ No MCP services available. "
            "Tool-required queries will be refused."
        )
    
    return results


def log_mcp_status():
    """Log current MCP status (sync version for startup)."""
    health = get_mcp_health()
    
    sentinel = health.get("sentinel", {})
    if sentinel.get("available"):
        logger.info(
            f"Sentinel: available ({sentinel.get('artifact_count', 0)} artifacts)"
        )
    else:
        logger.warning(
            f"Sentinel: unavailable ({sentinel.get('error', 'not checked')})"
        )


# ─────────────────────────────────────────────
# Retry Guidance
# ─────────────────────────────────────────────

def get_retry_guidance(tool_name: str) -> str:
    """
    Get retry guidance for a specific tool.
    
    Used when a tool is unavailable to help the user.
    """
    guidance = {
        "sentinel": (
            "Sentinel is currently unavailable. "
            "Try again later or ask a question that doesn't require internal documents."
        ),
        "deep_research": (
            "Deep research is currently unavailable. "
            "Try using quick mode or ask a simpler question."
        ),
    }
    
    return guidance.get(tool_name, f"{tool_name} is currently unavailable.")
