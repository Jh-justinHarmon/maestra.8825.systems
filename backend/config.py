"""
Configuration for Maestra Backend

Feature flags and configuration settings.
"""

import os
from typing import Dict, Any

# =============================================================================
# FEATURE FLAGS
# =============================================================================

# Personalization: Structure Adaptation
# When enabled, applies structured formatting (bullets, code blocks) for artifact requests
# When disabled, all responses use conversational formatting
ENABLE_STRUCTURE_ADAPTATION = os.getenv("ENABLE_STRUCTURE_ADAPTATION", "false").lower() == "true"

# A/B Test: Structure Adaptation
# Percentage of sessions in treatment group (0-100)
# Set to 50 for 50/50 split, 0 to disable A/B test (all control), 100 for all treatment
STRUCTURE_AB_TEST_PERCENTAGE = int(os.getenv("STRUCTURE_AB_TEST_PERCENTAGE", "50"))

# =============================================================================
# CONFIGURATION
# =============================================================================

def get_feature_flags() -> Dict[str, Any]:
    """
    Get current feature flag values.
    
    Returns:
        dict: Feature flag configuration
    """
    return {
        "structure_adaptation": ENABLE_STRUCTURE_ADAPTATION,
        "structure_ab_test_percentage": STRUCTURE_AB_TEST_PERCENTAGE,
    }


def is_feature_enabled(feature_name: str) -> bool:
    """
    Check if a feature is enabled.
    
    Args:
        feature_name: Name of the feature flag
        
    Returns:
        bool: True if enabled, False otherwise
    """
    flags = get_feature_flags()
    return flags.get(feature_name, False)
