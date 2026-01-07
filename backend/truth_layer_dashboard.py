"""
Truth Layer Dashboard - Always-On Monitoring

Displays real-time epistemic metrics on dedicated dashboard.
Auto-refreshes every 30 seconds.
Provides live status of truth layer enforcement.
"""

import logging
from typing import Dict
from datetime import datetime
from observability import get_dashboard
from epistemic_metrics import get_metrics_instance

logger = logging.getLogger(__name__)


class TruthLayerDashboard:
    """Always-on dashboard for truth layer monitoring."""
    
    def __init__(self):
        self.dashboard = get_dashboard()
        self.metrics = get_metrics_instance()
    
    def get_live_status(self) -> Dict:
        """
        Get current truth layer status.
        
        Returns:
            Dictionary with live status metrics
        """
        metrics = self.metrics.get_metrics()
        alerts = self.dashboard.get_alerts()
        health = self.metrics.get_health_status()
        
        grounded_pct = metrics["grounded"]["percentage"]
        refused_pct = metrics["refused"]["percentage"]
        avg_confidence = metrics["confidence"]["average"]
        
        # Determine overall status
        if grounded_pct > 80 and refused_pct < 10 and avg_confidence > 0.75:
            status = "TRUTH_LAYER_ACTIVE"
            status_emoji = "🟢"
        elif grounded_pct > 60 and refused_pct < 30:
            status = "DEGRADED"
            status_emoji = "🟡"
        else:
            status = "CRITICAL"
            status_emoji = "🔴"
        
        return {
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "status_emoji": status_emoji,
            "health": health,
            "metrics": {
                "grounded_pct": round(grounded_pct, 1),
                "refused_pct": round(refused_pct, 1),
                "ungrounded_pct": round(metrics["ungrounded"]["percentage"], 1),
                "avg_confidence": round(avg_confidence, 2),
                "total_responses": metrics["total_responses"],
                "avg_response_time_ms": round(metrics["response_time_ms"]["average"], 0),
                "error_count": metrics["error_count"]
            },
            "alerts": {
                "active_count": len(alerts["active"]),
                "active_alerts": alerts["active"]
            },
            "thresholds": {
                "grounded_target": 80,
                "refused_target": 10,
                "confidence_target": 0.75,
                "response_time_target": 500
            }
        }
    
    def get_summary_text(self) -> str:
        """Get human-readable summary."""
        status = self.get_live_status()
        
        summary = f"""
{status['status_emoji']} Truth Layer Status: {status['status']}

📊 Metrics:
  • Grounded: {status['metrics']['grounded_pct']}% (target: >80%)
  • Refused: {status['metrics']['refused_pct']}% (target: <10%)
  • Confidence: {status['metrics']['avg_confidence']} (target: >0.75)
  • Response Time: {status['metrics']['avg_response_time_ms']}ms (target: <500ms)

🚨 Alerts: {status['alerts']['active_count']} active

Health: {status['health'].upper()}
"""
        return summary.strip()


# Global instance
_truth_layer_dashboard = None


def get_truth_layer_dashboard() -> TruthLayerDashboard:
    """Get or create global truth layer dashboard instance."""
    global _truth_layer_dashboard
    if _truth_layer_dashboard is None:
        _truth_layer_dashboard = TruthLayerDashboard()
    return _truth_layer_dashboard
