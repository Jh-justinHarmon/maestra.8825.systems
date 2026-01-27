"""
Maestra Backend - Capability Router

Routes queries to the best MCPs based on query type and available capabilities.
Enables intelligent multi-MCP execution for enhanced answers.

Query patterns:
- Comparison: "Compare X vs Y" → deep-research MCP
- Knowledge: "What did we decide about Z?" → library-bridge MCP
- Summary: "Summarize recent work" → context-builder MCP
- Research: "Research X" → deep-research MCP
- Context: "What's the context for X?" → context-builder MCP
"""

import re
import logging
from typing import List, Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class CapabilityType(str, Enum):
    DEEP_RESEARCH = "deep_research"
    LIBRARY_BRIDGE = "library_bridge"
    CONTEXT_BUILDER = "context_builder"
    JH_BRAIN = "jh_brain"
    LOCAL_COMPANION = "local_companion"

class QueryPattern(str, Enum):
    COMPARISON = "comparison"
    KNOWLEDGE = "knowledge"
    SUMMARY = "summary"
    RESEARCH = "research"
    CONTEXT = "context"
    DECISION = "decision"
    PATTERN = "pattern"
    GENERIC = "generic"

class CapabilityRouter:
    """Routes queries to appropriate MCPs."""
    
    def __init__(self):
        self.patterns = {
            QueryPattern.COMPARISON: [
                r"compare\s+(.+?)\s+(?:vs|versus|with|to)",
                r"(?:what\'s|what is)\s+(?:the\s+)?(?:difference|difference between)",
                r"(?:pros|cons)\s+(?:of|for)",
            ],
            QueryPattern.KNOWLEDGE: [
                r"(?:what|when|where|why|how)\s+(?:did|do|we)\s+(?:decide|choose|pick)",
                r"(?:why|reason)\s+(?:did|do|we)\s+(?:choose|pick|decide)",
                r"(?:what|which)\s+(?:decision|choice|option)\s+(?:did|do|we)\s+(?:make|choose)",
            ],
            QueryPattern.SUMMARY: [
                r"summarize\s+(?:recent|latest|my)",
                r"(?:what|what\'s)\s+(?:the\s+)?(?:summary|overview|status)\s+(?:of|for)",
                r"(?:recap|recap of|recap on)",
            ],
            QueryPattern.RESEARCH: [
                r"research\s+(?:about|on|into)",
                r"(?:investigate|look into|explore)\s+(?:about|on|into)",
                r"(?:find|search)\s+(?:information|details|facts)\s+(?:about|on)",
            ],
            QueryPattern.CONTEXT: [
                r"(?:what\'s|what is)\s+(?:the\s+)?context\s+(?:for|of|around)",
                r"(?:give|provide)\s+(?:context|background)\s+(?:for|on)",
                r"(?:background|context)\s+(?:for|on)",
            ],
            QueryPattern.DECISION: [
                r"(?:decision|choice|option)\s+(?:about|for|on)",
                r"(?:decided|chose|picked)\s+(?:to|that)",
            ],
            QueryPattern.PATTERN: [
                r"pattern\s+(?:for|of|in)",
                r"(?:similar|same|like)\s+(?:situation|problem|case)",
                r"(?:have|we|you)\s+(?:done|solved)\s+(?:this|something like this)",
            ],
        }
    
    def detect_pattern(self, query: str) -> QueryPattern:
        """Detect query pattern using regex matching."""
        query_lower = query.lower()
        
        for pattern_type, regex_patterns in self.patterns.items():
            for regex in regex_patterns:
                if re.search(regex, query_lower):
                    logger.info(f"Detected pattern: {pattern_type} for query: {query}")
                    return pattern_type
        
        return QueryPattern.GENERIC
    
    def get_capabilities(self, pattern: QueryPattern) -> List[CapabilityType]:
        """Get recommended capabilities for a query pattern."""
        routing_map = {
            QueryPattern.COMPARISON: [
                CapabilityType.DEEP_RESEARCH,
                CapabilityType.CONTEXT_BUILDER,
            ],
            QueryPattern.KNOWLEDGE: [
                CapabilityType.LIBRARY_BRIDGE,
                CapabilityType.LOCAL_COMPANION,
                CapabilityType.JH_BRAIN,
            ],
            QueryPattern.SUMMARY: [
                CapabilityType.CONTEXT_BUILDER,
                CapabilityType.LOCAL_COMPANION,
            ],
            QueryPattern.RESEARCH: [
                CapabilityType.DEEP_RESEARCH,
                CapabilityType.CONTEXT_BUILDER,
            ],
            QueryPattern.CONTEXT: [
                CapabilityType.CONTEXT_BUILDER,
                CapabilityType.LOCAL_COMPANION,
                CapabilityType.JH_BRAIN,
            ],
            QueryPattern.DECISION: [
                CapabilityType.LIBRARY_BRIDGE,
                CapabilityType.LOCAL_COMPANION,
            ],
            QueryPattern.PATTERN: [
                CapabilityType.LIBRARY_BRIDGE,
                CapabilityType.LOCAL_COMPANION,
                CapabilityType.CONTEXT_BUILDER,
            ],
            QueryPattern.GENERIC: [
                CapabilityType.CONTEXT_BUILDER,
                CapabilityType.DEEP_RESEARCH,
            ],
        }
        
        return routing_map.get(pattern, [CapabilityType.CONTEXT_BUILDER])
    
    def route(self, query: str, available_capabilities: List[str] = None) -> Dict:
        """
        Route a query to appropriate MCPs.
        
        Returns: {
            "pattern": QueryPattern,
            "recommended_capabilities": [CapabilityType, ...],
            "available_capabilities": [CapabilityType, ...],
            "primary_capability": CapabilityType,
            "secondary_capabilities": [CapabilityType, ...],
            "confidence": float
        }
        """
        if available_capabilities is None:
            available_capabilities = []
        
        # Detect query pattern
        pattern = self.detect_pattern(query)
        
        # Get recommended capabilities for this pattern
        recommended = self.get_capabilities(pattern)
        
        # Filter to only available capabilities
        # Convert strings to CapabilityType if needed
        available_caps = [
            CapabilityType(cap) if isinstance(cap, str) else cap
            for cap in available_capabilities
        ]
        available_set = {cap.value if hasattr(cap, 'value') else cap for cap in available_caps}
        available_recommended = [
            cap for cap in recommended
            if cap.value in available_set
        ]
        
        # If no recommended capabilities available, use all available
        if not available_recommended:
            available_recommended = [
                CapabilityType(cap) if isinstance(cap, str) else cap
                for cap in available_capabilities
            ]
        
        # Determine primary and secondary
        primary = available_recommended[0] if available_recommended else CapabilityType.CONTEXT_BUILDER
        secondary = available_recommended[1:] if len(available_recommended) > 1 else []
        
        # Calculate confidence based on pattern match
        confidence = 0.9 if pattern != QueryPattern.GENERIC else 0.5
        
        return {
            "pattern": pattern.value,
            "recommended_capabilities": [cap.value for cap in recommended],
            "available_capabilities": [cap.value for cap in available_recommended],
            "primary_capability": primary.value,
            "secondary_capabilities": [cap.value for cap in secondary],
            "confidence": confidence
        }

# Global router instance
router = CapabilityRouter()

def route_query(query: str, available_capabilities: List[str] = None) -> Dict:
    """Route a query to appropriate MCPs."""
    return router.route(query, available_capabilities)
