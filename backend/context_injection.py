"""
Context Injection System

Injects verified context into LLM prompts.
Ensures no answer is generated without grounding verification.
"""

from typing import List, Dict, Any, Optional
from epistemic import GroundingSource, EpistemicState
import logging

logger = logging.getLogger(__name__)


class ContextInjector:
    """Injects verified context into LLM prompts."""
    
    @staticmethod
    def build_system_prompt(
        base_system_prompt: str,
        grounding_sources: List[GroundingSource],
        epistemic_state: EpistemicState
    ) -> str:
        """
        Build system prompt with context injection.
        
        Args:
            base_system_prompt: Base system prompt
            grounding_sources: List of verified grounding sources
            epistemic_state: GROUNDED, UNGROUNDED, or REFUSED
        
        Returns:
            Enhanced system prompt with context
        """
        if epistemic_state == EpistemicState.REFUSED:
            return base_system_prompt + "\n\n[EPISTEMIC STATE: REFUSED - No grounding sources available. Do not answer.]"
        
        if not grounding_sources:
            return base_system_prompt + "\n\n[EPISTEMIC STATE: UNGROUNDED - Answer is speculative, not based on verified sources.]"
        
        # Build context section
        context_section = "\n\n[VERIFIED CONTEXT - Source of Truth]\n"
        context_section += f"Epistemic State: {epistemic_state.value}\n"
        context_section += f"Sources ({len(grounding_sources)}):\n"
        
        for i, source in enumerate(grounding_sources, 1):
            context_section += f"\n{i}. {source.title} (Confidence: {source.confidence:.1%})\n"
            context_section += f"   Source: {source.source_type.value}\n"
            if source.excerpt:
                context_section += f"   Excerpt: {source.excerpt[:200]}...\n"
        
        context_section += "\n[Use the above verified sources to ground your answer. If sources don't support your answer, refuse.]"
        
        return base_system_prompt + context_section
    
    @staticmethod
    def build_user_prompt(
        base_user_prompt: str,
        chain_results: Dict[str, Any],
        grounding_sources: List[GroundingSource],
        epistemic_state: EpistemicState
    ) -> str:
        """
        Build user prompt with chain results and context.
        
        Args:
            base_user_prompt: Base user prompt
            chain_results: Results from MCP chain execution
            grounding_sources: List of verified grounding sources
            epistemic_state: GROUNDED, UNGROUNDED, or REFUSED
        
        Returns:
            Enhanced user prompt with context
        """
        if epistemic_state == EpistemicState.REFUSED:
            return base_user_prompt + "\n\n[CONTEXT UNAVAILABLE - Cannot answer this question without required context.]"
        
        # Build context section from chain results
        context_section = "\n\n[CONTEXT FROM CHAIN EXECUTION]\n"
        
        if chain_results:
            for step_name, step_result in chain_results.items():
                if step_result:
                    context_section += f"\n{step_name}:\n"
                    if isinstance(step_result, dict):
                        for key, value in step_result.items():
                            if key not in ["step", "mcp", "grounded"]:
                                context_section += f"  {key}: {str(value)[:200]}\n"
                    else:
                        context_section += f"  {str(step_result)[:200]}\n"
        
        if grounding_sources:
            context_section += "\n[GROUNDING SOURCES - USE THIS INFORMATION TO ANSWER]\n"
            for i, source in enumerate(grounding_sources, 1):
                context_section += f"\n--- Source {i}: {source.title} ({source.source_type.value}) ---\n"
                if source.excerpt:
                    # Include full excerpt content for the LLM to use
                    context_section += f"{source.excerpt}\n"
        
        return base_user_prompt + context_section
    
    @staticmethod
    def build_messages(
        query: str,
        chain_results: Dict[str, Any],
        grounding_sources: List[GroundingSource],
        epistemic_state: EpistemicState,
        base_system_prompt: str = None
    ) -> List[Dict[str, str]]:
        """
        Build complete message list for LLM with injected context.
        
        Args:
            query: User's query
            chain_results: Results from MCP chain execution
            grounding_sources: List of verified grounding sources
            epistemic_state: GROUNDED, UNGROUNDED, or REFUSED
            base_system_prompt: Optional base system prompt
        
        Returns:
            List of messages ready for LLM
        """
        if base_system_prompt is None:
            base_system_prompt = "You are Maestra, an AI advisor powered by the 8825 system. Provide grounded, honest answers based on verified context."
        
        # Build system prompt with context
        system_prompt = ContextInjector.build_system_prompt(
            base_system_prompt,
            grounding_sources,
            epistemic_state
        )
        
        # Build user prompt with chain results
        user_prompt = ContextInjector.build_user_prompt(
            query,
            chain_results,
            grounding_sources,
            epistemic_state
        )
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]


def inject_context_into_prompt(
    query: str,
    chain_results: Dict[str, Any],
    grounding_sources: List[GroundingSource],
    epistemic_state: EpistemicState,
    formatting_hint: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    Convenience function to inject context into prompt.
    
    Args:
        query: User's query
        chain_results: Results from MCP chain execution
        grounding_sources: List of verified grounding sources
        epistemic_state: GROUNDED, UNGROUNDED, or REFUSED
        formatting_hint: Optional formatting hint for structure adaptation
    
    Returns:
        List of messages ready for LLM
    """
    base_system_prompt = "You are Maestra, an AI advisor powered by the 8825 system. Provide grounded, honest answers based on verified context."
    
    # Add formatting hint if provided (for structure adaptation)
    if formatting_hint:
        base_system_prompt += f"\n\n{formatting_hint}"
    
    return ContextInjector.build_messages(
        query=query,
        chain_results=chain_results,
        grounding_sources=grounding_sources,
        epistemic_state=epistemic_state,
        base_system_prompt=base_system_prompt
    )
