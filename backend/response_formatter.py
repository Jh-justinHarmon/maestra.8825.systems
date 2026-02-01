"""
Response Formatting Logic

Applies structured formatting to responses based on mediator decisions.
"""

from typing import Optional


def apply_structured_formatting(response: str, should_structure: bool) -> str:
    """
    Apply structured formatting to a response if appropriate.
    
    This is a simple implementation that adds structure hints.
    The actual formatting is done by the LLM based on system prompt hints.
    
    Args:
        response: The raw response text
        should_structure: Whether to apply structured formatting
        
    Returns:
        str: Response with formatting hints (if applicable)
    """
    # For now, we return the response as-is
    # The actual formatting will be controlled via system prompt modification
    # in inject_context_into_prompt
    return response


def get_formatting_hint(should_structure: bool) -> Optional[str]:
    """
    Get a formatting hint to add to the system prompt.
    
    Args:
        should_structure: Whether structured formatting is requested
        
    Returns:
        str: Formatting hint for system prompt, or None
    """
    if should_structure:
        return (
            "Format your response with clear structure:\n"
            "- Use bullet points for lists\n"
            "- Use code blocks for code/scripts\n"
            "- Use headings for sections\n"
            "- Keep explanations concise"
        )
    else:
        return None
