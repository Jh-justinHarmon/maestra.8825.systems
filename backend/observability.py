"""
Observability Module

Provides dashboards, monitoring, and alert thresholds for epistemic integrity metrics.
Tracks system health and identifies issues before they impact users.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from epistemic_metrics import get_metrics_instance, EpistemicMetrics

logger = logging.getLogger(__name__)


class AlertThreshold:
    """Define alert thresholds for system health."""
    
    def __init__(
        self,
        name: str,
        metric_name: str,
        threshold: float,
        comparison: str = "greater_than",  # greater_than, less_than, equals
        severity: str = "warning",  # warning, critical
    ):
        self.name = name
        self.metric_name = metric_name
        self.threshold = threshold
        self.comparison = comparison
        self.severity = severity
    
    def check(self, value: float) -> bool:
        """Check if threshold is violated."""
        if self.comparison == "greater_than":
            return value > self.threshold
        elif self.comparison == "less_than":
            return value < self.threshold
        elif self.comparison == "equals":
            return value == self.threshold
        return False


class AlertManager:
    """Manages alerts based on metric thresholds."""
    
    def __init__(self):
        self.thresholds: List[AlertThreshold] = []
        self.active_alerts: List[Dict] = []
        self.alert_history: List[Dict] = []
        self.setup_default_thresholds()
    
    def setup_default_thresholds(self) -> None:
        """Setup default alert thresholds."""
        # Refused ratio too high
        self.add_threshold(AlertThreshold(
            name="High Refusal Rate",
            metric_name="refused_percentage",
            threshold=30,
            comparison="greater_than",
            severity="warning"
        ))
        
        # Confidence too low
        self.add_threshold(AlertThreshold(
            name="Low Confidence",
            metric_name="avg_confidence",
            threshold=0.6,
            comparison="less_than",
            severity="warning"
        ))
        
        # Response time too high
        self.add_threshold(AlertThreshold(
            name="High Response Time",
            metric_name="avg_response_time_ms",
            threshold=5000,
            comparison="greater_than",
            severity="warning"
        ))
        
        # Error rate too high
        self.add_threshold(AlertThreshold(
            name="High Error Rate",
            metric_name="error_count",
            threshold=10,
            comparison="greater_than",
            severity="critical"
        ))
    
    def add_threshold(self, threshold: AlertThreshold) -> None:
        """Add a threshold."""
        self.thresholds.append(threshold)
    
    def check_alerts(self, metrics: Dict) -> List[Dict]:
        """Check all thresholds against current metrics."""
        alerts = []
        
        for threshold in self.thresholds:
            # Extract metric value
            value = self._extract_metric(metrics, threshold.metric_name)
            
            if value is not None and threshold.check(value):
                alert = {
                    "name": threshold.name,
                    "severity": threshold.severity,
                    "metric": threshold.metric_name,
                    "threshold": threshold.threshold,
                    "actual_value": value,
                    "timestamp": datetime.now().isoformat(),
                }
                alerts.append(alert)
                self.alert_history.append(alert)
        
        self.active_alerts = alerts
        return alerts
    
    def _extract_metric(self, metrics: Dict, metric_name: str) -> Optional[float]:
        """Extract metric value from metrics dict."""
        parts = metric_name.split(".")
        value = metrics
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None
        
        return value if isinstance(value, (int, float)) else None
    
    def get_active_alerts(self) -> List[Dict]:
        """Get currently active alerts."""
        return self.active_alerts
    
    def get_alert_history(self, limit: int = 100) -> List[Dict]:
        """Get alert history."""
        return self.alert_history[-limit:]


class Dashboard:
    """Observability dashboard for epistemic metrics."""
    
    def __init__(self):
        self.metrics = get_metrics_instance()
        self.alert_manager = AlertManager()
    
    def get_dashboard_data(self) -> Dict:
        """Get complete dashboard data."""
        metrics = self.metrics.get_metrics()
        alerts = self.alert_manager.check_alerts(metrics)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "health_status": self.metrics.get_health_status(),
            "metrics": metrics,
            "alerts": {
                "active": alerts,
                "count": len(alerts),
            },
            "summary": self._build_summary(metrics, alerts),
        }
    
    def _build_summary(self, metrics: Dict, alerts: List[Dict]) -> Dict:
        """Build human-readable summary."""
        total = metrics["total_responses"]
        grounded_pct = metrics["grounded"]["percentage"]
        refused_pct = metrics["refused"]["percentage"]
        avg_confidence = metrics["confidence"]["average"]
        
        summary = []
        
        # Grounding summary
        if grounded_pct > 80:
            summary.append(f"✅ {grounded_pct:.0f}% of answers are grounded")
        elif grounded_pct > 50:
            summary.append(f"⚠️  {grounded_pct:.0f}% of answers are grounded (target: >80%)")
        else:
            summary.append(f"❌ Only {grounded_pct:.0f}% of answers are grounded")
        
        # Refusal summary
        if refused_pct < 10:
            summary.append(f"✅ {refused_pct:.0f}% refusal rate (acceptable)")
        elif refused_pct < 30:
            summary.append(f"⚠️  {refused_pct:.0f}% refusal rate (consider improving context)")
        else:
            summary.append(f"❌ {refused_pct:.0f}% refusal rate (too high)")
        
        # Confidence summary
        if avg_confidence > 0.8:
            summary.append(f"✅ High confidence ({avg_confidence:.0%})")
        elif avg_confidence > 0.6:
            summary.append(f"⚠️  Medium confidence ({avg_confidence:.0%})")
        else:
            summary.append(f"❌ Low confidence ({avg_confidence:.0%})")
        
        # Response time summary
        avg_time = metrics["response_time_ms"]["average"]
        if avg_time < 1000:
            summary.append(f"✅ Fast responses ({avg_time:.0f}ms)")
        elif avg_time < 5000:
            summary.append(f"⚠️  Moderate response time ({avg_time:.0f}ms)")
        else:
            summary.append(f"❌ Slow responses ({avg_time:.0f}ms)")
        
        # Alerts summary
        if alerts:
            summary.append(f"⚠️  {len(alerts)} active alerts")
        else:
            summary.append("✅ No active alerts")
        
        return {
            "text": "\n".join(summary),
            "lines": summary,
        }
    
    def get_health_status(self) -> str:
        """Get overall health status."""
        return self.metrics.get_health_status()
    
    def get_metrics(self) -> Dict:
        """Get raw metrics."""
        return self.metrics.get_metrics()
    
    def get_alerts(self) -> Dict:
        """Get alert information."""
        return {
            "active": self.alert_manager.get_active_alerts(),
            "history": self.alert_manager.get_alert_history(),
        }


# Global dashboard instance
_dashboard_instance = None


def get_dashboard() -> Dashboard:
    """Get or create global dashboard instance."""
    global _dashboard_instance
    if _dashboard_instance is None:
        _dashboard_instance = Dashboard()
    return _dashboard_instance
