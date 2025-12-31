"""
Maestra Backend - Learning Loop

Implements feedback collection, governance, and auto-tuning for continuous improvement.

Features:
- Feedback collection (user ratings, corrections)
- Quality metrics tracking (accuracy, relevance, latency)
- Auto-tuning (adjust routing, caching, MCP selection based on feedback)
- Governance (track decisions, audit trail, compliance)
- A/B testing framework (test new strategies)
"""

import logging
import time
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class FeedbackType(str, Enum):
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"
    INCORRECT = "incorrect"
    INCOMPLETE = "incomplete"
    SLOW = "slow"
    IRRELEVANT = "irrelevant"

class QualityMetric(str, Enum):
    ACCURACY = "accuracy"
    RELEVANCE = "relevance"
    LATENCY = "latency"
    COMPLETENESS = "completeness"
    USER_SATISFACTION = "user_satisfaction"

@dataclass
class UserFeedback:
    """User feedback on a response."""
    feedback_id: str
    session_id: str
    response_id: str
    feedback_type: str  # FeedbackType
    rating: int  # 1-5
    comment: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class QualityScore:
    """Quality score for a response."""
    response_id: str
    metric: str  # QualityMetric
    score: float  # 0-1
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class RoutingDecision:
    """Record of a routing decision for governance."""
    decision_id: str
    session_id: str
    query: str
    pattern_detected: str
    primary_mcp: str
    secondary_mcps: List[str]
    feedback_received: bool = False
    feedback_type: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class ABTest:
    """A/B test for comparing strategies."""
    test_id: str
    name: str
    description: str
    control_strategy: str
    test_strategy: str
    metric_to_optimize: str
    control_results: Dict[str, Any] = field(default_factory=dict)
    test_results: Dict[str, Any] = field(default_factory=dict)
    status: str = "active"  # active, completed, abandoned
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)

class LearningLoopTracker:
    """Tracks feedback, quality metrics, and auto-tuning."""
    
    def __init__(self):
        self.feedback: Dict[str, UserFeedback] = {}
        self.quality_scores: Dict[str, List[QualityScore]] = {}
        self.routing_decisions: Dict[str, RoutingDecision] = {}
        self.ab_tests: Dict[str, ABTest] = {}
        self.mcp_performance: Dict[str, Dict[str, float]] = {}  # MCP → metrics
    
    def record_feedback(
        self,
        feedback_id: str,
        session_id: str,
        response_id: str,
        feedback_type: str,
        rating: int,
        comment: str = ""
    ) -> UserFeedback:
        """Record user feedback."""
        feedback = UserFeedback(
            feedback_id=feedback_id,
            session_id=session_id,
            response_id=response_id,
            feedback_type=feedback_type,
            rating=rating,
            comment=comment
        )
        
        self.feedback[feedback_id] = feedback
        logger.info(f"Feedback recorded: {feedback_type} (rating: {rating})")
        
        # Update routing decision if available
        self._update_routing_feedback(response_id, feedback_type)
        
        return feedback
    
    def record_quality_score(
        self,
        response_id: str,
        metric: str,
        score: float
    ) -> QualityScore:
        """Record quality metric for a response."""
        quality = QualityScore(
            response_id=response_id,
            metric=metric,
            score=score
        )
        
        if response_id not in self.quality_scores:
            self.quality_scores[response_id] = []
        
        self.quality_scores[response_id].append(quality)
        logger.info(f"Quality score recorded: {metric}={score:.2f}")
        
        return quality
    
    def record_routing_decision(
        self,
        decision_id: str,
        session_id: str,
        query: str,
        pattern_detected: str,
        primary_mcp: str,
        secondary_mcps: Optional[List[str]] = None
    ) -> RoutingDecision:
        """Record a routing decision for governance."""
        decision = RoutingDecision(
            decision_id=decision_id,
            session_id=session_id,
            query=query,
            pattern_detected=pattern_detected,
            primary_mcp=primary_mcp,
            secondary_mcps=secondary_mcps or []
        )
        
        self.routing_decisions[decision_id] = decision
        logger.info(f"Routing decision recorded: {pattern_detected} → {primary_mcp}")
        
        return decision
    
    def _update_routing_feedback(self, response_id: str, feedback_type: str) -> None:
        """Update routing decision with feedback."""
        # Find routing decision for this response
        for decision in self.routing_decisions.values():
            if decision.decision_id == response_id:
                decision.feedback_received = True
                decision.feedback_type = feedback_type
                logger.info(f"Updated routing decision with feedback: {feedback_type}")
                break
    
    def get_mcp_performance(self, mcp_name: str) -> Dict[str, Any]:
        """Get performance metrics for an MCP."""
        if mcp_name not in self.mcp_performance:
            return {
                "mcp": mcp_name,
                "total_uses": 0,
                "avg_rating": 0,
                "success_rate": 0,
                "avg_latency_ms": 0
            }
        
        metrics = self.mcp_performance[mcp_name]
        return {
            "mcp": mcp_name,
            "total_uses": metrics.get("total_uses", 0),
            "avg_rating": metrics.get("avg_rating", 0),
            "success_rate": metrics.get("success_rate", 0),
            "avg_latency_ms": metrics.get("avg_latency_ms", 0)
        }
    
    def update_mcp_performance(
        self,
        mcp_name: str,
        rating: float,
        latency_ms: float,
        success: bool
    ) -> None:
        """Update MCP performance metrics."""
        if mcp_name not in self.mcp_performance:
            self.mcp_performance[mcp_name] = {
                "total_uses": 0,
                "total_rating": 0,
                "avg_rating": 0,
                "successes": 0,
                "success_rate": 0,
                "total_latency": 0,
                "avg_latency_ms": 0
            }
        
        metrics = self.mcp_performance[mcp_name]
        metrics["total_uses"] += 1
        metrics["total_rating"] += rating
        metrics["avg_rating"] = metrics["total_rating"] / metrics["total_uses"]
        
        if success:
            metrics["successes"] += 1
        metrics["success_rate"] = metrics["successes"] / metrics["total_uses"]
        
        metrics["total_latency"] += latency_ms
        metrics["avg_latency_ms"] = metrics["total_latency"] / metrics["total_uses"]
        
        logger.info(f"Updated MCP performance: {mcp_name} (avg_rating: {metrics['avg_rating']:.2f})")
    
    def create_ab_test(
        self,
        test_id: str,
        name: str,
        description: str,
        control_strategy: str,
        test_strategy: str,
        metric_to_optimize: str
    ) -> ABTest:
        """Create an A/B test."""
        test = ABTest(
            test_id=test_id,
            name=name,
            description=description,
            control_strategy=control_strategy,
            test_strategy=test_strategy,
            metric_to_optimize=metric_to_optimize
        )
        
        self.ab_tests[test_id] = test
        logger.info(f"A/B test created: {name}")
        
        return test
    
    def record_ab_test_result(
        self,
        test_id: str,
        is_control: bool,
        metric_value: float
    ) -> None:
        """Record result from an A/B test."""
        if test_id not in self.ab_tests:
            return
        
        test = self.ab_tests[test_id]
        results = test.control_results if is_control else test.test_results
        
        if "values" not in results:
            results["values"] = []
        results["values"].append(metric_value)
        
        # Calculate average
        results["average"] = sum(results["values"]) / len(results["values"])
        results["count"] = len(results["values"])
        
        logger.info(f"A/B test result recorded: {test.name} ({'control' if is_control else 'test'})")
    
    def get_ab_test_results(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Get results from an A/B test."""
        if test_id not in self.ab_tests:
            return None
        
        test = self.ab_tests[test_id]
        
        control_avg = test.control_results.get("average", 0)
        test_avg = test.test_results.get("average", 0)
        
        improvement = 0
        if control_avg > 0:
            improvement = ((test_avg - control_avg) / control_avg) * 100
        
        return {
            "test_id": test_id,
            "name": test.name,
            "control_avg": control_avg,
            "test_avg": test_avg,
            "improvement_percent": improvement,
            "control_count": test.control_results.get("count", 0),
            "test_count": test.test_results.get("count", 0),
            "status": test.status,
            "winner": "test" if improvement > 0 else "control"
        }
    
    def get_feedback_summary(self) -> Dict[str, Any]:
        """Get summary of feedback."""
        if not self.feedback:
            return {
                "total_feedback": 0,
                "avg_rating": 0,
                "feedback_types": {}
            }
        
        total = len(self.feedback)
        avg_rating = sum(f.rating for f in self.feedback.values()) / total
        
        feedback_types = {}
        for feedback in self.feedback.values():
            if feedback.feedback_type not in feedback_types:
                feedback_types[feedback.feedback_type] = 0
            feedback_types[feedback.feedback_type] += 1
        
        return {
            "total_feedback": total,
            "avg_rating": f"{avg_rating:.2f}",
            "feedback_types": feedback_types
        }
    
    def get_routing_accuracy(self) -> Dict[str, Any]:
        """Get routing decision accuracy."""
        if not self.routing_decisions:
            return {
                "total_decisions": 0,
                "with_feedback": 0,
                "accuracy_rate": 0
            }
        
        total = len(self.routing_decisions)
        with_feedback = sum(1 for d in self.routing_decisions.values() if d.feedback_received)
        
        # Count positive feedback
        positive_feedback = sum(
            1 for d in self.routing_decisions.values()
            if d.feedback_received and d.feedback_type in ["helpful", "correct"]
        )
        
        accuracy = (positive_feedback / total * 100) if total > 0 else 0
        
        return {
            "total_decisions": total,
            "with_feedback": with_feedback,
            "positive_feedback": positive_feedback,
            "accuracy_rate": f"{accuracy:.1f}%"
        }

# Global learning loop tracker
learning_tracker = LearningLoopTracker()

def record_feedback(
    feedback_id: str,
    session_id: str,
    response_id: str,
    feedback_type: str,
    rating: int,
    comment: str = ""
) -> UserFeedback:
    """Record user feedback."""
    return learning_tracker.record_feedback(
        feedback_id, session_id, response_id, feedback_type, rating, comment
    )

def record_quality_score(response_id: str, metric: str, score: float) -> QualityScore:
    """Record quality metric."""
    return learning_tracker.record_quality_score(response_id, metric, score)

def get_feedback_summary() -> Dict[str, Any]:
    """Get feedback summary."""
    return learning_tracker.get_feedback_summary()

def get_routing_accuracy() -> Dict[str, Any]:
    """Get routing accuracy."""
    return learning_tracker.get_routing_accuracy()

def get_mcp_performance(mcp_name: str) -> Dict[str, Any]:
    """Get MCP performance."""
    return learning_tracker.get_mcp_performance(mcp_name)
