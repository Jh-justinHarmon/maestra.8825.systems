"""
PROMPT 8: User Archetypes for Overfitting Analysis

Partitions the synthetic test data into 3 distinct user archetypes
to validate signal generalization.
"""

# ============================================================================
# ARCHETYPE 1: CASUAL / LOW-EFFORT USER
# ============================================================================
# Characteristics:
# - Short queries (avg 30-50 chars)
# - Minimal depth requests
# - Rare alignment signals
# - Prefers quick answers
# - Low technical language

CASUAL_USER_TURNS = [
    {
        "turn_index": 1,
        "archetype": "casual",
        "user_message": "What's the difference between grounding and authority?",
        "message_length": 54,
        "expected_signals": {
            "query_type": "explore",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
        }
    },
    {
        "turn_index": 2,
        "archetype": "casual",
        "user_message": "What am I looking at on this page?",
        "message_length": 35,
        "expected_signals": {
            "query_type": "explore",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
        }
    },
    {
        "turn_index": 3,
        "archetype": "casual",
        "user_message": "Tell me about the enforcement kernel",
        "message_length": 37,
        "expected_signals": {
            "query_type": "explore",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
        }
    },
    {
        "turn_index": 4,
        "archetype": "casual",
        "user_message": "Deploy the changes to staging",
        "message_length": 29,
        "expected_signals": {
            "query_type": "execute",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
        }
    },
    {
        "turn_index": 5,
        "archetype": "casual",
        "user_message": "Run the invariant tests",
        "message_length": 23,
        "expected_signals": {
            "query_type": "execute",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
        }
    },
    {
        "turn_index": 6,
        "archetype": "casual",
        "user_message": "Is this too complex?",
        "message_length": 19,
        "expected_signals": {
            "query_type": "reflect",
            "depth_requested": False,
            "alignment_signal": True,
            "tools_requested": False,
        }
    },
    {
        "turn_index": 7,
        "archetype": "casual",
        "user_message": "What are the tradeoffs here?",
        "message_length": 28,
        "expected_signals": {
            "query_type": "reflect",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
        }
    },
    {
        "turn_index": 8,
        "archetype": "casual",
        "user_message": "Fix the model selection bug in llm_router.py",
        "message_length": 45,
        "expected_signals": {
            "query_type": "execute",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
        }
    },
    {
        "turn_index": 9,
        "archetype": "casual",
        "user_message": "What did we decide about personalization boundaries?",
        "message_length": 52,
        "expected_signals": {
            "query_type": "explore",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
        }
    },
    {
        "turn_index": 10,
        "archetype": "casual",
        "user_message": "Update the README with the new instrumentation features",
        "message_length": 57,
        "expected_signals": {
            "query_type": "execute",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
        }
    },
]

# ============================================================================
# ARCHETYPE 2: TASK-ORIENTED / EXECUTION-FOCUSED USER
# ============================================================================
# Characteristics:
# - Medium queries (avg 50-80 chars)
# - Frequent tool/artifact requests
# - Minimal reflection
# - Action-oriented language
# - Technical but terse

TASK_ORIENTED_USER_TURNS = [
    {
        "turn_index": 11,
        "archetype": "task_oriented",
        "user_message": "Create a script to validate enforcement invariants",
        "message_length": 51,
        "expected_signals": {
            "query_type": "execute",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": True,
        }
    },
    {
        "turn_index": 12,
        "archetype": "task_oriented",
        "user_message": "Add instrumentation to the session continuity module",
        "message_length": 54,
        "expected_signals": {
            "query_type": "execute",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
        }
    },
    {
        "turn_index": 13,
        "archetype": "task_oriented",
        "user_message": "Generate a prompt for testing depth detection",
        "message_length": 46,
        "expected_signals": {
            "query_type": "execute",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": True,
        }
    },
    {
        "turn_index": 14,
        "archetype": "task_oriented",
        "user_message": "Write a tool to analyze session metadata",
        "message_length": 41,
        "expected_signals": {
            "query_type": "execute",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": True,
        }
    },
    {
        "turn_index": 15,
        "archetype": "task_oriented",
        "user_message": "Let's add confidence scoring to the mediator",
        "message_length": 45,
        "expected_signals": {
            "query_type": "execute",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
        }
    },
    {
        "turn_index": 16,
        "archetype": "task_oriented",
        "user_message": "Search Sentinel for enforcement architecture decisions",
        "message_length": 55,
        "expected_signals": {
            "query_type": "execute",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
        }
    },
    {
        "turn_index": 17,
        "archetype": "task_oriented",
        "user_message": "Research best practices for memory isolation in multi-tenant systems",
        "message_length": 69,
        "expected_signals": {
            "query_type": "explore",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
        }
    },
    {
        "turn_index": 18,
        "archetype": "task_oriented",
        "user_message": "How does this compare to the old approach?",
        "message_length": 43,
        "expected_signals": {
            "query_type": "explore",
            "depth_requested": True,
            "alignment_signal": False,
            "tools_requested": False,
        }
    },
    {
        "turn_index": 19,
        "archetype": "task_oriented",
        "user_message": "Is this the right way to handle session state?",
        "message_length": 46,
        "expected_signals": {
            "query_type": "reflect",
            "depth_requested": False,
            "alignment_signal": True,
            "tools_requested": False,
        }
    },
    {
        "turn_index": 20,
        "archetype": "task_oriented",
        "user_message": "How confident are you in this recommendation?",
        "message_length": 45,
        "expected_signals": {
            "query_type": "reflect",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
        }
    },
]

# ============================================================================
# ARCHETYPE 3: EXPLORATORY / REFLECTIVE USER
# ============================================================================
# Characteristics:
# - Long queries (avg 80-150 chars)
# - Frequent depth requests
# - High alignment signals
# - Philosophical/analytical language
# - Seeks understanding over action

EXPLORATORY_USER_TURNS = [
    {
        "turn_index": 21,
        "archetype": "exploratory",
        "user_message": "Why did we separate trust from capability in the enforcement architecture?",
        "message_length": 75,
        "expected_signals": {
            "query_type": "explore",
            "depth_requested": True,
            "alignment_signal": False,
            "tools_requested": False,
        }
    },
    {
        "turn_index": 22,
        "archetype": "exploratory",
        "user_message": "Explain how the memory router enforces isolation",
        "message_length": 49,
        "expected_signals": {
            "query_type": "explore",
            "depth_requested": True,
            "alignment_signal": False,
            "tools_requested": False,
        }
    },
    {
        "turn_index": 23,
        "archetype": "exploratory",
        "user_message": "Can you walk me through the session continuity flow?",
        "message_length": 53,
        "expected_signals": {
            "query_type": "explore",
            "depth_requested": True,
            "alignment_signal": False,
            "tools_requested": False,
        }
    },
    {
        "turn_index": 24,
        "archetype": "exploratory",
        "user_message": "Why is isolation important here?",
        "message_length": 32,
        "expected_signals": {
            "query_type": "explore",
            "depth_requested": True,
            "alignment_signal": False,
            "tools_requested": False,
        }
    },
    {
        "turn_index": 25,
        "archetype": "exploratory",
        "user_message": "Does this approach feel right, or am I overthinking the isolation guarantees?",
        "message_length": 77,
        "expected_signals": {
            "query_type": "reflect",
            "depth_requested": False,
            "alignment_signal": True,
            "tools_requested": False,
        }
    },
    {
        "turn_index": 26,
        "archetype": "exploratory",
        "user_message": "Am I missing something obvious here?",
        "message_length": 36,
        "expected_signals": {
            "query_type": "reflect",
            "depth_requested": False,
            "alignment_signal": True,
            "tools_requested": False,
        }
    },
    {
        "turn_index": 27,
        "archetype": "exploratory",
        "user_message": "Should I be worried about cross-session leakage?",
        "message_length": 48,
        "expected_signals": {
            "query_type": "reflect",
            "depth_requested": False,
            "alignment_signal": True,
            "tools_requested": False,
        }
    },
    {
        "turn_index": 28,
        "archetype": "exploratory",
        "user_message": "Does it make sense to separate these concerns?",
        "message_length": 46,
        "expected_signals": {
            "query_type": "reflect",
            "depth_requested": False,
            "alignment_signal": True,
            "tools_requested": False,
        }
    },
    {
        "turn_index": 29,
        "archetype": "exploratory",
        "user_message": "I'm uncertain about the confidence threshold - thoughts?",
        "message_length": 55,
        "expected_signals": {
            "query_type": "reflect",
            "depth_requested": False,
            "alignment_signal": True,
            "tools_requested": False,
        }
    },
    {
        "turn_index": 30,
        "archetype": "exploratory",
        "user_message": "What do you think about this personalization strategy?",
        "message_length": 54,
        "expected_signals": {
            "query_type": "reflect",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
        }
    },
]

# Combine all archetypes
ALL_ARCHETYPE_TURNS = (
    CASUAL_USER_TURNS +
    TASK_ORIENTED_USER_TURNS +
    EXPLORATORY_USER_TURNS
)
