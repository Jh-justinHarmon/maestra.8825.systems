"""
Response Validator

Validates all responses before returning to ensure epistemic integrity.
Enforces that responses match their declared epistemic state.
"""

import logging
from typing import Any, Dict
from epistemic import EpistemicState

logger = logging.getLogger(__name__)


class ResponseValidator:
    """Validates responses for epistemic integrity."""
    
    @staticmethod
    def validate_grounded_response(response: Dict[str, Any]) -> bool:
        """
        Validate GROUNDED response.
        
        Requirements:
        - epistemic_state must be "grounded"
        - Must have at least one grounding source
        - Confidence must be >= 0.5
        - Answer must not contain refusal language
        """
        errors = []
        
        # Check epistemic state
        if response.get("epistemic_state") != EpistemicState.GROUNDED.value:
            errors.append(f"Expected epistemic_state=grounded, got {response.get('epistemic_state')}")
        
        # Check grounding sources
        sources = response.get("grounding_sources", [])
        if not sources or len(sources) == 0:
            errors.append("GROUNDED response must have at least one grounding source")
        
        # Check confidence
        confidence = response.get("confidence", 0)
        if confidence < 0.5:
            errors.append(f"GROUNDED response must have confidence >= 0.5, got {confidence}")
        
        # Check answer doesn't contain refusal language
        answer = response.get("answer", "").lower()
        refusal_phrases = ["cannot answer", "don't have enough", "insufficient context", "no sources"]
        if any(phrase in answer for phrase in refusal_phrases):
            errors.append("GROUNDED response contains refusal language")
        
        if errors:
            logger.error(f"GROUNDED response validation failed: {errors}")
            return False
        
        logger.info(f"GROUNDED response validated ({len(sources)} sources, confidence={confidence})")
        return True
    
    @staticmethod
    def validate_ungrounded_response(response: Dict[str, Any]) -> bool:
        """
        Validate UNGROUNDED response.
        
        Requirements:
        - epistemic_state must be "ungrounded"
        - Answer should indicate it's speculative
        - No grounding sources required
        """
        errors = []
        
        # Check epistemic state
        if response.get("epistemic_state") != EpistemicState.UNGROUNDED.value:
            errors.append(f"Expected epistemic_state=ungrounded, got {response.get('epistemic_state')}")
        
        # Check answer indicates speculation
        answer = response.get("answer", "").lower()
        speculation_phrases = ["speculative", "based on general knowledge", "without verified sources", "my understanding"]
        if not any(phrase in answer for phrase in speculation_phrases):
            logger.warning("UNGROUNDED response should indicate it's speculative")
        
        if errors:
            logger.error(f"UNGROUNDED response validation failed: {errors}")
            return False
        
        logger.info("UNGROUNDED response validated")
        return True
    
    @staticmethod
    def validate_refused_response(response: Dict[str, Any]) -> bool:
        """
        Validate REFUSED response.
        
        Requirements:
        - epistemic_state must be "refused"
        - Answer must clearly indicate refusal
        - No grounding sources
        - Should suggest what would help
        """
        errors = []
        
        # Check epistemic state
        if response.get("epistemic_state") != EpistemicState.REFUSED.value:
            errors.append(f"Expected epistemic_state=refused, got {response.get('epistemic_state')}")
        
        # Check answer indicates refusal
        answer = response.get("answer", "").lower()
        refusal_phrases = ["cannot answer", "don't have enough", "insufficient context", "no sources available"]
        if not any(phrase in answer for phrase in refusal_phrases):
            errors.append("REFUSED response must clearly indicate refusal")
        
        # Check no grounding sources
        sources = response.get("grounding_sources", [])
        if sources and len(sources) > 0:
            errors.append("REFUSED response should not have grounding sources")
        
        # Check confidence is low
        confidence = response.get("confidence", 0)
        if confidence > 0.3:
            logger.warning(f"REFUSED response has high confidence ({confidence}), expected < 0.3")
        
        if errors:
            logger.error(f"REFUSED response validation failed: {errors}")
            return False
        
        logger.info("REFUSED response validated")
        return True
    
    @staticmethod
    def validate_response(response: Dict[str, Any]) -> bool:
        """
        Validate response based on its epistemic state.
        
        Args:
            response: Response dictionary with epistemic_state
        
        Returns:
            True if valid, False otherwise
        """
        epistemic_state = response.get("epistemic_state")
        
        if epistemic_state == EpistemicState.GROUNDED.value:
            return ResponseValidator.validate_grounded_response(response)
        elif epistemic_state == EpistemicState.UNGROUNDED.value:
            return ResponseValidator.validate_ungrounded_response(response)
        elif epistemic_state == EpistemicState.REFUSED.value:
            return ResponseValidator.validate_refused_response(response)
        else:
            logger.error(f"Unknown epistemic_state: {epistemic_state}")
            return False
    
    @staticmethod
    def validate_all_responses(responses: list) -> bool:
        """
        Validate multiple responses.
        
        Args:
            responses: List of response dictionaries
        
        Returns:
            True if all valid, False if any invalid
        """
        all_valid = True
        for i, response in enumerate(responses):
            if not ResponseValidator.validate_response(response):
                logger.error(f"Response {i} failed validation")
                all_valid = False
        
        return all_valid
