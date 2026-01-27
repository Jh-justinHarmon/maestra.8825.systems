"""
Stub agent telemetry for MAESTRA_MINIMAL_MODE.

Provides no-op telemetry functions without requiring full system infrastructure.
"""
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


def log_agent_event(
    event_type: str,
    agent_id: str,
    query: str,
    auto_selected: bool = False,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    No-op telemetry logging in minimal mode.
    
    In production, this would log to telemetry system.
    In minimal mode, we just log locally.
    """
    logger.info(
        f"[STUB_TELEMETRY] {event_type} | agent={agent_id} | "
        f"query={query[:50]} | session={session_id}"
    )
