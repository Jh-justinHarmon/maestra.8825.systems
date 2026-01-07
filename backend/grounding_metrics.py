"""
Grounding Metrics Collector

Real-time tracking of grounding rates for observability.
Provides dashboard data and alerting thresholds.
"""

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Literal
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class GroundingRecord:
    """A single grounding event."""
    epistemic_state: Literal["grounded", "ungrounded", "refused"]
    timestamp: datetime
    trace_id: Optional[str] = None
    sources: List[str] = field(default_factory=list)
    confidence: float = 0.0
    response_time_ms: float = 0.0


@dataclass
class GroundingRates:
    """Current grounding rates."""
    grounded: float
    ungrounded: float
    refused: float
    total_requests: int
    window_seconds: int
    avg_confidence: float
    avg_response_time_ms: float
    
    def to_dict(self) -> Dict:
        return {
            "grounded": round(self.grounded, 3),
            "ungrounded": round(self.ungrounded, 3),
            "refused": round(self.refused, 3),
            "total_requests": self.total_requests,
            "window_seconds": self.window_seconds,
            "avg_confidence": round(self.avg_confidence, 3),
            "avg_response_time_ms": round(self.avg_response_time_ms, 1),
        }


@dataclass
class HealthStatus:
    """System health based on grounding metrics."""
    status: Literal["healthy", "degraded", "unhealthy"]
    grounded_rate: float
    refused_rate: float
    alerts: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "status": self.status,
            "grounded_rate": round(self.grounded_rate, 3),
            "refused_rate": round(self.refused_rate, 3),
            "alerts": self.alerts,
        }


class GroundingMetrics:
    """
    Real-time grounding metrics collector.
    
    Tracks the last N requests and provides:
    - Current grounding rates
    - Health status determination
    - Alert generation
    """
    
    # Alert thresholds
    GROUNDED_RATE_HEALTHY = 0.80    # >80% grounded = healthy
    GROUNDED_RATE_DEGRADED = 0.50   # 50-80% = degraded
    REFUSED_RATE_WARNING = 0.10     # >10% refused = warning
    REFUSED_RATE_CRITICAL = 0.25   # >25% refused = critical
    RESPONSE_TIME_WARNING = 500     # >500ms = warning
    CONFIDENCE_WARNING = 0.6        # <0.6 avg confidence = warning
    
    def __init__(self, window_size: int = 100, window_seconds: int = 3600):
        """
        Initialize metrics collector.
        
        Args:
            window_size: Number of recent requests to track
            window_seconds: Time window for rate calculation (default: 1 hour)
        """
        self.window_size = window_size
        self.window_seconds = window_seconds
        self.records: deque = deque(maxlen=window_size)
        self.lock = Lock()
        
        # Counters for all-time stats
        self.total_grounded = 0
        self.total_ungrounded = 0
        self.total_refused = 0
    
    def record(
        self,
        epistemic_state: str,
        trace_id: Optional[str] = None,
        sources: Optional[List[str]] = None,
        confidence: float = 0.0,
        response_time_ms: float = 0.0,
    ) -> None:
        """
        Record a grounding event.
        
        Args:
            epistemic_state: One of "grounded", "ungrounded", "refused"
            trace_id: Optional trace ID for correlation
            sources: List of grounding sources used
            confidence: Confidence score (0-1)
            response_time_ms: Response time in milliseconds
        """
        state = epistemic_state.lower()
        if state not in ("grounded", "ungrounded", "refused"):
            logger.warning(f"Invalid epistemic state: {epistemic_state}")
            return
        
        record = GroundingRecord(
            epistemic_state=state,
            timestamp=datetime.utcnow(),
            trace_id=trace_id,
            sources=sources or [],
            confidence=confidence,
            response_time_ms=response_time_ms,
        )
        
        with self.lock:
            self.records.append(record)
            
            # Update counters
            if state == "grounded":
                self.total_grounded += 1
            elif state == "ungrounded":
                self.total_ungrounded += 1
            else:
                self.total_refused += 1
    
    def get_rates(self, window_seconds: Optional[int] = None) -> GroundingRates:
        """
        Get current grounding rates.
        
        Args:
            window_seconds: Optional override for time window
        
        Returns:
            GroundingRates with current statistics
        """
        window = window_seconds or self.window_seconds
        cutoff = datetime.utcnow() - timedelta(seconds=window)
        
        with self.lock:
            # Filter to time window
            recent = [r for r in self.records if r.timestamp >= cutoff]
            
            if not recent:
                return GroundingRates(
                    grounded=0.0,
                    ungrounded=0.0,
                    refused=0.0,
                    total_requests=0,
                    window_seconds=window,
                    avg_confidence=0.0,
                    avg_response_time_ms=0.0,
                )
            
            total = len(recent)
            grounded = sum(1 for r in recent if r.epistemic_state == "grounded")
            ungrounded = sum(1 for r in recent if r.epistemic_state == "ungrounded")
            refused = sum(1 for r in recent if r.epistemic_state == "refused")
            
            avg_confidence = sum(r.confidence for r in recent) / total
            avg_response_time = sum(r.response_time_ms for r in recent) / total
            
            return GroundingRates(
                grounded=grounded / total,
                ungrounded=ungrounded / total,
                refused=refused / total,
                total_requests=total,
                window_seconds=window,
                avg_confidence=avg_confidence,
                avg_response_time_ms=avg_response_time,
            )
    
    def get_health_status(self) -> HealthStatus:
        """
        Determine system health based on grounding metrics.
        
        Returns:
            HealthStatus with status and alerts
        """
        rates = self.get_rates()
        alerts = []
        
        # Check grounded rate
        if rates.grounded < self.GROUNDED_RATE_DEGRADED:
            alerts.append(f"Critical: Grounded rate {rates.grounded:.1%} below {self.GROUNDED_RATE_DEGRADED:.0%}")
        elif rates.grounded < self.GROUNDED_RATE_HEALTHY:
            alerts.append(f"Warning: Grounded rate {rates.grounded:.1%} below {self.GROUNDED_RATE_HEALTHY:.0%}")
        
        # Check refused rate
        if rates.refused > self.REFUSED_RATE_CRITICAL:
            alerts.append(f"Critical: Refused rate {rates.refused:.1%} above {self.REFUSED_RATE_CRITICAL:.0%}")
        elif rates.refused > self.REFUSED_RATE_WARNING:
            alerts.append(f"Warning: Refused rate {rates.refused:.1%} above {self.REFUSED_RATE_WARNING:.0%}")
        
        # Check response time
        if rates.avg_response_time_ms > self.RESPONSE_TIME_WARNING:
            alerts.append(f"Warning: Avg response time {rates.avg_response_time_ms:.0f}ms above {self.RESPONSE_TIME_WARNING}ms")
        
        # Check confidence
        if rates.avg_confidence < self.CONFIDENCE_WARNING and rates.total_requests > 0:
            alerts.append(f"Warning: Avg confidence {rates.avg_confidence:.2f} below {self.CONFIDENCE_WARNING}")
        
        # Determine status
        if rates.grounded < self.GROUNDED_RATE_DEGRADED or rates.refused > self.REFUSED_RATE_CRITICAL:
            status = "unhealthy"
        elif rates.grounded < self.GROUNDED_RATE_HEALTHY or rates.refused > self.REFUSED_RATE_WARNING:
            status = "degraded"
        else:
            status = "healthy"
        
        return HealthStatus(
            status=status,
            grounded_rate=rates.grounded,
            refused_rate=rates.refused,
            alerts=alerts,
        )
    
    def get_all_time_stats(self) -> Dict:
        """Get all-time statistics."""
        total = self.total_grounded + self.total_ungrounded + self.total_refused
        
        if total == 0:
            return {
                "total_requests": 0,
                "grounded": 0,
                "ungrounded": 0,
                "refused": 0,
                "grounded_rate": 0.0,
            }
        
        return {
            "total_requests": total,
            "grounded": self.total_grounded,
            "ungrounded": self.total_ungrounded,
            "refused": self.total_refused,
            "grounded_rate": self.total_grounded / total,
        }


# Global metrics instance
_metrics: Optional[GroundingMetrics] = None


def get_metrics() -> GroundingMetrics:
    """Get the global metrics instance."""
    global _metrics
    if _metrics is None:
        _metrics = GroundingMetrics()
    return _metrics


def record_grounding(
    epistemic_state: str,
    trace_id: Optional[str] = None,
    sources: Optional[List[str]] = None,
    confidence: float = 0.0,
    response_time_ms: float = 0.0,
) -> None:
    """Convenience function to record a grounding event."""
    get_metrics().record(
        epistemic_state=epistemic_state,
        trace_id=trace_id,
        sources=sources,
        confidence=confidence,
        response_time_ms=response_time_ms,
    )
