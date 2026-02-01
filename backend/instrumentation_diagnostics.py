"""
Instrumentation Diagnostics - Developer-only observability

This module provides diagnostic views of instrumentation data for developers.
NOT exposed to users - CLI/log-based output only.

CRITICAL: Read-only, no side effects. For observation and debugging only.
"""

import logging
from typing import Dict, Any, List, Optional
from collections import Counter
from datetime import datetime

logger = logging.getLogger(__name__)


class InstrumentationDiagnostics:
    """
    Developer-only diagnostic view of instrumentation data.
    
    Aggregates signals from session turns and provides summary statistics.
    """
    
    def __init__(self):
        self.session_stats: Dict[str, Dict[str, Any]] = {}
    
    def analyze_session(
        self,
        session_id: str,
        turns: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze a session's instrumentation data.
        
        Args:
            session_id: Session identifier
            turns: List of conversation turns with metadata
        
        Returns:
            Diagnostic summary dict
        """
        if not turns:
            return {
                "session_id": session_id,
                "error": "No turns to analyze"
            }
        
        # Separate user and assistant turns
        user_turns = [t for t in turns if t.get("type") == "user_query"]
        assistant_turns = [t for t in turns if t.get("type") == "assistant_response"]
        
        # Extract metadata
        user_metadata = [t.get("metadata", {}) for t in user_turns]
        assistant_metadata = [t.get("metadata", {}) for t in assistant_turns]
        
        # Compute statistics
        stats = {
            "session_id": session_id,
            "total_turns": len(turns),
            "user_turns": len(user_turns),
            "assistant_turns": len(assistant_turns),
            "timestamp": datetime.utcnow().isoformat(),
            
            # Query type distribution
            "query_type_distribution": self._compute_distribution(
                [m.get("query_type") for m in user_metadata]
            ),
            
            # Epistemic query type distribution
            "epistemic_query_type_distribution": self._compute_distribution(
                [m.get("epistemic_query_type") for m in user_metadata]
            ),
            
            # Signal frequencies
            "depth_requested_frequency": self._compute_frequency(
                [m.get("depth_requested") for m in user_metadata]
            ),
            "alignment_signal_frequency": self._compute_frequency(
                [m.get("alignment_signal") for m in user_metadata]
            ),
            "tools_requested_frequency": self._compute_frequency(
                [m.get("tools_requested") for m in user_metadata]
            ),
            "tool_required_frequency": self._compute_frequency(
                [m.get("tool_required") for m in user_metadata]
            ),
            
            # Tool usage
            "tool_usage_rate": self._compute_tool_usage_rate(assistant_metadata),
            
            # Response metrics
            "avg_response_length": self._compute_avg(
                [m.get("response_length") for m in assistant_metadata]
            ),
            "avg_latency_ms": self._compute_avg(
                [m.get("latency_ms") for m in assistant_metadata]
            ),
            
            # Shadow mediator decisions (aggregated)
            "mediator_decisions": self._aggregate_mediator_decisions(assistant_metadata),
        }
        
        # Store for later retrieval
        self.session_stats[session_id] = stats
        
        return stats
    
    def _compute_distribution(self, values: List[Optional[str]]) -> Dict[str, float]:
        """Compute distribution of categorical values."""
        filtered = [v for v in values if v is not None]
        if not filtered:
            return {}
        
        counts = Counter(filtered)
        total = len(filtered)
        
        return {
            value: count / total
            for value, count in counts.items()
        }
    
    def _compute_frequency(self, values: List[Optional[bool]]) -> float:
        """Compute frequency of True values."""
        filtered = [v for v in values if v is not None]
        if not filtered:
            return 0.0
        
        return sum(1 for v in filtered if v) / len(filtered)
    
    def _compute_tool_usage_rate(self, metadata_list: List[Dict[str, Any]]) -> float:
        """Compute rate of tool usage in responses."""
        if not metadata_list:
            return 0.0
        
        tools_used_count = sum(
            1 for m in metadata_list
            if m.get("tools_used")
        )
        
        return tools_used_count / len(metadata_list)
    
    def _compute_avg(self, values: List[Optional[float]]) -> Optional[float]:
        """Compute average of numeric values."""
        filtered = [v for v in values if v is not None]
        if not filtered:
            return None
        
        return sum(filtered) / len(filtered)
    
    def _aggregate_mediator_decisions(
        self,
        metadata_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate shadow mediator decisions."""
        decisions = [
            m.get("shadow_mediator_decision")
            for m in metadata_list
            if m.get("shadow_mediator_decision")
        ]
        
        if not decisions:
            return {}
        
        # Extract decision fields
        verbosity_values = [d.get("verbosity") for d in decisions]
        structure_values = [d.get("structure") for d in decisions]
        show_reasoning_values = [d.get("show_reasoning") for d in decisions]
        ask_clarifying_values = [d.get("ask_clarifying_question") for d in decisions]
        confidence_values = [d.get("confidence") for d in decisions]
        
        return {
            "total_decisions": len(decisions),
            "verbosity_distribution": self._compute_distribution(verbosity_values),
            "structure_distribution": self._compute_distribution(structure_values),
            "show_reasoning_rate": self._compute_frequency(show_reasoning_values),
            "ask_clarifying_rate": self._compute_frequency(ask_clarifying_values),
            "avg_confidence": self._compute_avg(confidence_values),
        }
    
    def get_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get diagnostic stats for a session."""
        return self.session_stats.get(session_id)
    
    def get_all_sessions(self) -> List[str]:
        """Get list of all analyzed session IDs."""
        return list(self.session_stats.keys())
    
    def format_summary(self, session_id: str) -> str:
        """
        Format session stats as human-readable summary.
        
        Returns:
            Formatted string for CLI/log output
        """
        stats = self.session_stats.get(session_id)
        if not stats:
            return f"No stats available for session {session_id}"
        
        lines = [
            f"\n{'='*60}",
            f"INSTRUMENTATION DIAGNOSTICS - Session {session_id}",
            f"{'='*60}",
            f"",
            f"Total Turns: {stats['total_turns']} ({stats['user_turns']} user, {stats['assistant_turns']} assistant)",
            f"",
            f"--- Query Type Distribution ---",
        ]
        
        # Query types
        for qtype, freq in stats.get("query_type_distribution", {}).items():
            lines.append(f"  {qtype}: {freq:.1%}")
        
        lines.append(f"")
        lines.append(f"--- Epistemic Query Type Distribution ---")
        
        for qtype, freq in stats.get("epistemic_query_type_distribution", {}).items():
            lines.append(f"  {qtype}: {freq:.1%}")
        
        lines.append(f"")
        lines.append(f"--- Signal Frequencies ---")
        lines.append(f"  depth_requested: {stats.get('depth_requested_frequency', 0):.1%}")
        lines.append(f"  alignment_signal: {stats.get('alignment_signal_frequency', 0):.1%}")
        lines.append(f"  tools_requested: {stats.get('tools_requested_frequency', 0):.1%}")
        lines.append(f"  tool_required: {stats.get('tool_required_frequency', 0):.1%}")
        
        lines.append(f"")
        lines.append(f"--- Response Metrics ---")
        lines.append(f"  tool_usage_rate: {stats.get('tool_usage_rate', 0):.1%}")
        
        avg_response = stats.get('avg_response_length')
        if avg_response:
            lines.append(f"  avg_response_length: {avg_response:.0f} chars")
        
        avg_latency = stats.get('avg_latency_ms')
        if avg_latency:
            lines.append(f"  avg_latency: {avg_latency:.0f} ms")
        
        # Mediator decisions
        mediator = stats.get("mediator_decisions", {})
        if mediator:
            lines.append(f"")
            lines.append(f"--- Shadow Mediator Decisions (Aggregated) ---")
            lines.append(f"  total_decisions: {mediator.get('total_decisions', 0)}")
            
            for verb, freq in mediator.get("verbosity_distribution", {}).items():
                lines.append(f"  verbosity.{verb}: {freq:.1%}")
            
            for struct, freq in mediator.get("structure_distribution", {}).items():
                lines.append(f"  structure.{struct}: {freq:.1%}")
            
            lines.append(f"  show_reasoning_rate: {mediator.get('show_reasoning_rate', 0):.1%}")
            lines.append(f"  ask_clarifying_rate: {mediator.get('ask_clarifying_rate', 0):.1%}")
            
            avg_conf = mediator.get('avg_confidence')
            if avg_conf:
                lines.append(f"  avg_confidence: {avg_conf:.2f}")
        
        lines.append(f"")
        lines.append(f"{'='*60}")
        
        return "\n".join(lines)


# Global diagnostics instance
_diagnostics = InstrumentationDiagnostics()


def get_diagnostics() -> InstrumentationDiagnostics:
    """Get the global diagnostics instance."""
    return _diagnostics


def analyze_session(session_id: str, turns: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze a session's instrumentation data.
    
    Developer-only function for diagnostics.
    """
    return _diagnostics.analyze_session(session_id, turns)


def print_session_summary(session_id: str):
    """
    Print session diagnostic summary to console.
    
    Developer-only function for CLI output.
    """
    summary = _diagnostics.format_summary(session_id)
    print(summary)
    logger.info(f"Printed diagnostics for session {session_id}")


def get_session_stats(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get diagnostic stats for a session.
    
    Developer-only function for programmatic access.
    """
    return _diagnostics.get_session_stats(session_id)
