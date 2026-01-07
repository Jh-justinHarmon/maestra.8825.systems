"""
Epistemic Metrics Collector

Tracks system health metrics related to epistemic integrity:
- Grounded/ungrounded/refused ratios
- Source success rates
- Confidence distribution
- Query classification patterns
"""

import logging
from typing import Dict, List, Optional
from collections import defaultdict
from datetime import datetime
from epistemic import EpistemicState, GroundingSourceType

logger = logging.getLogger(__name__)


class EpistemicMetrics:
    """Collects and reports epistemic integrity metrics."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.grounded_total = 0
        self.ungrounded_total = 0
        self.refused_total = 0
        self.source_success_rates = defaultdict(list)
        self.confidence_distribution = []
        self.query_types = defaultdict(int)
        self.response_times = []
        self.errors = []
        self.start_time = datetime.now()
    
    def record_response(
        self,
        epistemic_state: EpistemicState,
        confidence: float,
        sources: List[Dict],
        query_type: Optional[str] = None,
        response_time_ms: Optional[float] = None
    ) -> None:
        """
        Record a response for metrics.
        
        Args:
            epistemic_state: GROUNDED, UNGROUNDED, or REFUSED
            confidence: Confidence score (0.0-1.0)
            sources: List of grounding sources used
            query_type: Type of query (memory_based, generative, etc.)
            response_time_ms: Response time in milliseconds
        """
        # Record epistemic state
        if epistemic_state == EpistemicState.GROUNDED:
            self.grounded_total += 1
        elif epistemic_state == EpistemicState.UNGROUNDED:
            self.ungrounded_total += 1
        elif epistemic_state == EpistemicState.REFUSED:
            self.refused_total += 1
        
        # Record confidence
        self.confidence_distribution.append(confidence)
        
        # Record source success rates
        for source in sources:
            source_type = source.get("type", "unknown")
            source_confidence = source.get("confidence", 0)
            self.source_success_rates[source_type].append(source_confidence)
        
        # Record query type
        if query_type:
            self.query_types[query_type] += 1
        
        # Record response time
        if response_time_ms:
            self.response_times.append(response_time_ms)
        
        logger.debug(f"Recorded response: state={epistemic_state.value}, confidence={confidence}, sources={len(sources)}")
    
    def record_error(self, error_type: str, message: str) -> None:
        """
        Record an error for metrics.
        
        Args:
            error_type: Type of error (grounding_failed, mcp_error, etc.)
            message: Error message
        """
        self.errors.append({
            "type": error_type,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        logger.warning(f"Recorded error: {error_type} - {message}")
    
    def get_metrics(self) -> Dict:
        """
        Get current metrics snapshot.
        
        Returns:
            Dictionary with all metrics
        """
        total = self.grounded_total + self.ungrounded_total + self.refused_total
        
        # Calculate averages
        avg_confidence = (
            sum(self.confidence_distribution) / len(self.confidence_distribution)
            if self.confidence_distribution
            else 0
        )
        
        avg_response_time = (
            sum(self.response_times) / len(self.response_times)
            if self.response_times
            else 0
        )
        
        # Calculate source success rates
        source_rates = {}
        for source_type, confidences in self.source_success_rates.items():
            source_rates[source_type] = {
                "avg_confidence": sum(confidences) / len(confidences) if confidences else 0,
                "count": len(confidences)
            }
        
        # Calculate uptime
        uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": uptime_seconds,
            "total_responses": total,
            "grounded": {
                "count": self.grounded_total,
                "percentage": (self.grounded_total / total * 100) if total > 0 else 0
            },
            "ungrounded": {
                "count": self.ungrounded_total,
                "percentage": (self.ungrounded_total / total * 100) if total > 0 else 0
            },
            "refused": {
                "count": self.refused_total,
                "percentage": (self.refused_total / total * 100) if total > 0 else 0
            },
            "confidence": {
                "average": avg_confidence,
                "min": min(self.confidence_distribution) if self.confidence_distribution else 0,
                "max": max(self.confidence_distribution) if self.confidence_distribution else 0
            },
            "response_time_ms": {
                "average": avg_response_time,
                "min": min(self.response_times) if self.response_times else 0,
                "max": max(self.response_times) if self.response_times else 0
            },
            "source_success_rates": source_rates,
            "query_types": dict(self.query_types),
            "error_count": len(self.errors),
            "recent_errors": self.errors[-10:] if self.errors else []
        }
    
    def get_health_status(self) -> str:
        """
        Get overall health status based on metrics.
        
        Returns:
            "healthy", "degraded", or "unhealthy"
        """
        metrics = self.get_metrics()
        
        # Unhealthy: > 50% refused
        if metrics["refused"]["percentage"] > 50:
            return "unhealthy"
        
        # Degraded: > 30% refused or avg confidence < 0.6
        if metrics["refused"]["percentage"] > 30 or metrics["confidence"]["average"] < 0.6:
            return "degraded"
        
        # Healthy: < 30% refused and avg confidence >= 0.6
        return "healthy"
    
    def reset(self) -> None:
        """Reset all metrics."""
        self.grounded_total = 0
        self.ungrounded_total = 0
        self.refused_total = 0
        self.source_success_rates = defaultdict(list)
        self.confidence_distribution = []
        self.query_types = defaultdict(int)
        self.response_times = []
        self.errors = []
        self.start_time = datetime.now()
        logger.info("Metrics reset")


# Global metrics instance
_metrics_instance = None


def get_metrics_instance() -> EpistemicMetrics:
    """Get or create global metrics instance."""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = EpistemicMetrics()
    return _metrics_instance
