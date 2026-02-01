"""
Shadow Conversation Mediator - Observes signals, computes decisions, does NOT apply them

This module computes response-shaping decisions based on conversation signals
WITHOUT influencing actual responses. It's a "shadow" system for observation only.

CRITICAL: Mediator output is LOGGED ONLY. Response generation MUST ignore it.
"""

import logging
from typing import Dict, Any, List, Optional, Literal
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class MediatorDecision:
    """
    Shadow decision about how to shape a response.
    
    IMPORTANT: This is observation-only. No code should branch on these values.
    """
    verbosity: Literal["low", "medium", "high"]
    structure: Literal["conversational", "structured"]
    show_reasoning: bool
    ask_clarifying_question: bool
    
    # Metadata about the decision
    confidence: float  # 0.0-1.0
    signals_used: List[str]  # Which signals influenced this decision
    reasoning: str  # Why this decision was made
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ShadowConversationMediator:
    """
    Computes response-shaping decisions without applying them.
    
    This is a "shadow" system - it observes and decides, but does NOT affect behavior.
    All decisions are logged for future analysis.
    """
    
    def __init__(self):
        self.decisions_log: List[Dict[str, Any]] = []
    
    def compute_decision(
        self,
        query: str,
        recent_turns: List[Dict[str, Any]],
        query_metadata: Dict[str, Any],
        session_context: Optional[Dict[str, Any]] = None
    ) -> MediatorDecision:
        """
        Compute a shadow decision about how to shape the response.
        
        Args:
            query: User query text
            recent_turns: Recent conversation turns with metadata
            query_metadata: Metadata from current user turn
            session_context: Optional session context
        
        Returns:
            MediatorDecision (logged only, not applied)
        """
        signals_used = []
        reasoning_parts = []
        
        # Default decision
        verbosity = "medium"
        structure = "conversational"
        show_reasoning = False
        ask_clarifying_question = False
        confidence = 0.5
        
        # Signal 1: depth_requested → show_reasoning
        if query_metadata.get("depth_requested"):
            show_reasoning = True
            signals_used.append("depth_requested")
            reasoning_parts.append("User asked for depth (why/how/explain)")
            confidence += 0.2
        
        # Signal 2: alignment_signal → ask_clarifying_question
        if query_metadata.get("alignment_signal"):
            ask_clarifying_question = True
            signals_used.append("alignment_signal")
            reasoning_parts.append("User expressed uncertainty")
            confidence += 0.15
        
        # Signal 3: tools_requested → structured
        if query_metadata.get("tools_requested"):
            structure = "structured"
            signals_used.append("tools_requested")
            reasoning_parts.append("User asked for artifacts/tools")
            confidence += 0.1
        
        # Signal 4: query_type → verbosity
        query_type = query_metadata.get("query_type")
        if query_type == "execute":
            verbosity = "low"
            signals_used.append("query_type=execute")
            reasoning_parts.append("Execute queries prefer terse responses")
            confidence += 0.1
        elif query_type == "explore":
            verbosity = "medium"
            signals_used.append("query_type=explore")
            reasoning_parts.append("Explore queries prefer balanced detail")
        elif query_type == "reflect":
            verbosity = "high"
            ask_clarifying_question = True
            signals_used.append("query_type=reflect")
            reasoning_parts.append("Reflect queries benefit from dialogue")
            confidence += 0.15
        
        # Signal 5: Recent turn patterns → verbosity adjustment
        if recent_turns and len(recent_turns) >= 3:
            avg_user_length = sum(
                len(t.get("content", "")) 
                for t in recent_turns 
                if t.get("type") == "user_query"
            ) / max(1, sum(1 for t in recent_turns if t.get("type") == "user_query"))
            
            if avg_user_length < 50:
                # User writes short messages → prefer terse responses
                if verbosity == "high":
                    verbosity = "medium"
                elif verbosity == "medium":
                    verbosity = "low"
                signals_used.append("short_user_messages")
                reasoning_parts.append(f"User avg message length: {int(avg_user_length)} chars")
                confidence += 0.1
            elif avg_user_length > 200:
                # User writes long messages → can be more verbose
                if verbosity == "low":
                    verbosity = "medium"
                elif verbosity == "medium":
                    verbosity = "high"
                signals_used.append("long_user_messages")
                reasoning_parts.append(f"User avg message length: {int(avg_user_length)} chars")
                confidence += 0.1
        
        # Signal 6: Follow-up patterns → ask_clarifying_question
        if recent_turns and len(recent_turns) >= 2:
            last_assistant = next(
                (t for t in reversed(recent_turns) if t.get("type") == "assistant_response"),
                None
            )
            if last_assistant and last_assistant.get("metadata", {}).get("epistemic_state") == "refused":
                ask_clarifying_question = True
                signals_used.append("previous_refusal")
                reasoning_parts.append("Previous response was a refusal")
                confidence += 0.2
        
        # Cap confidence at 1.0
        confidence = min(1.0, confidence)
        
        # Build reasoning string
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "No strong signals detected"
        
        decision = MediatorDecision(
            verbosity=verbosity,
            structure=structure,
            show_reasoning=show_reasoning,
            ask_clarifying_question=ask_clarifying_question,
            confidence=confidence,
            signals_used=signals_used,
            reasoning=reasoning
        )
        
        # Log decision (observation only)
        self._log_decision(query, decision)
        
        return decision
    
    def _log_decision(self, query: str, decision: MediatorDecision):
        """Log a shadow decision for future analysis."""
        log_entry = {
            "query": query[:100],  # Truncate for logging
            "decision": decision.to_dict(),
            "timestamp": __import__("datetime").datetime.utcnow().isoformat()
        }
        self.decisions_log.append(log_entry)
        
        logger.info(
            f"🔮 Shadow Mediator Decision: "
            f"verbosity={decision.verbosity}, "
            f"structure={decision.structure}, "
            f"show_reasoning={decision.show_reasoning}, "
            f"ask_clarifying={decision.ask_clarifying_question}, "
            f"confidence={decision.confidence:.2f}"
        )
        logger.debug(f"Reasoning: {decision.reasoning}")
    
    def get_recent_decisions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent shadow decisions for analysis."""
        return self.decisions_log[-limit:]
    
    def get_decision_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics about shadow decisions."""
        if not self.decisions_log:
            return {
                "total_decisions": 0,
                "avg_confidence": 0.0,
                "verbosity_distribution": {},
                "structure_distribution": {},
                "show_reasoning_rate": 0.0,
                "ask_clarifying_rate": 0.0
            }
        
        total = len(self.decisions_log)
        
        verbosity_counts = {}
        structure_counts = {}
        show_reasoning_count = 0
        ask_clarifying_count = 0
        total_confidence = 0.0
        
        for entry in self.decisions_log:
            decision = entry["decision"]
            verbosity_counts[decision["verbosity"]] = verbosity_counts.get(decision["verbosity"], 0) + 1
            structure_counts[decision["structure"]] = structure_counts.get(decision["structure"], 0) + 1
            if decision["show_reasoning"]:
                show_reasoning_count += 1
            if decision["ask_clarifying_question"]:
                ask_clarifying_count += 1
            total_confidence += decision["confidence"]
        
        return {
            "total_decisions": total,
            "avg_confidence": total_confidence / total,
            "verbosity_distribution": {k: v/total for k, v in verbosity_counts.items()},
            "structure_distribution": {k: v/total for k, v in structure_counts.items()},
            "show_reasoning_rate": show_reasoning_count / total,
            "ask_clarifying_rate": ask_clarifying_count / total
        }


# Global shadow mediator instance
_shadow_mediator = ShadowConversationMediator()


def get_shadow_mediator() -> ShadowConversationMediator:
    """Get the global shadow mediator instance."""
    return _shadow_mediator
