"""
PROMPT 7: Synthetic Test Data for Shadow Mediator Accuracy Review

Since no real session data is available yet, this creates representative
conversation turns based on realistic patterns to validate instrumentation logic.
"""

# 30 representative conversation turns across different interaction patterns
SYNTHETIC_TEST_TURNS = [
    # ========================================================================
    # EXPLORE QUERIES (10 examples)
    # ========================================================================
    {
        "turn_index": 1,
        "user_message": "Why did we separate trust from capability in the enforcement architecture?",
        "expected_signals": {
            "query_type": "explore",
            "depth_requested": True,  # "why" signal
            "alignment_signal": False,
            "tools_requested": False,
            "epistemic_query_type": "MEMORY_REQUIRED",  # "we" + "did we"
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "medium",
            "structure": "conversational",
            "show_reasoning": True,  # depth requested
            "ask_clarifying_question": False
        },
        "context": "User asking about past architectural decision"
    },
    {
        "turn_index": 2,
        "user_message": "What's the difference between grounding and authority?",
        "expected_signals": {
            "query_type": "explore",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
            "epistemic_query_type": "GENERATIVE_ALLOWED",
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "medium",
            "structure": "conversational",
            "show_reasoning": False,
            "ask_clarifying_question": False
        },
        "context": "Conceptual question, no depth signal"
    },
    {
        "turn_index": 3,
        "user_message": "Explain how the memory router enforces isolation",
        "expected_signals": {
            "query_type": "explore",
            "depth_requested": True,  # "explain" + "how"
            "alignment_signal": False,
            "tools_requested": False,
            "epistemic_query_type": "GENERATIVE_ALLOWED",
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "medium",
            "structure": "conversational",
            "show_reasoning": True,
            "ask_clarifying_question": False
        },
        "context": "Explanation request with depth"
    },
    {
        "turn_index": 4,
        "user_message": "What am I looking at on this page?",
        "expected_signals": {
            "query_type": "explore",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
            "epistemic_query_type": "CONTEXT_REQUIRED",  # "what am i looking at"
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "medium",
            "structure": "conversational",
            "show_reasoning": False,
            "ask_clarifying_question": False
        },
        "context": "Context-dependent query"
    },
    {
        "turn_index": 5,
        "user_message": "Can you walk me through the session continuity flow?",
        "expected_signals": {
            "query_type": "explore",
            "depth_requested": True,  # "walk me through"
            "alignment_signal": False,
            "tools_requested": False,
            "epistemic_query_type": "GENERATIVE_ALLOWED",
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "high",  # "walk through" suggests detailed explanation
            "structure": "conversational",
            "show_reasoning": True,
            "ask_clarifying_question": False
        },
        "context": "Step-by-step explanation request"
    },
    {
        "turn_index": 6,
        "user_message": "What did we decide about personalization boundaries?",
        "expected_signals": {
            "query_type": "explore",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
            "epistemic_query_type": "MEMORY_REQUIRED",  # "what did we decide"
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "medium",
            "structure": "conversational",
            "show_reasoning": False,
            "ask_clarifying_question": False
        },
        "context": "Memory recall query"
    },
    {
        "turn_index": 7,
        "user_message": "How does this compare to the old approach?",
        "expected_signals": {
            "query_type": "explore",
            "depth_requested": True,  # "how"
            "alignment_signal": False,
            "tools_requested": False,
            "epistemic_query_type": "MEMORY_REQUIRED",  # "old approach" implies history
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "medium",
            "structure": "conversational",
            "show_reasoning": True,
            "ask_clarifying_question": False
        },
        "context": "Comparison query with depth"
    },
    {
        "turn_index": 8,
        "user_message": "Tell me about the enforcement kernel",
        "expected_signals": {
            "query_type": "explore",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
            "epistemic_query_type": "GENERATIVE_ALLOWED",
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "medium",
            "structure": "conversational",
            "show_reasoning": False,
            "ask_clarifying_question": False
        },
        "context": "General information request"
    },
    {
        "turn_index": 9,
        "user_message": "Why is isolation important here?",
        "expected_signals": {
            "query_type": "explore",
            "depth_requested": True,  # "why"
            "alignment_signal": False,
            "tools_requested": False,
            "epistemic_query_type": "GENERATIVE_ALLOWED",
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "medium",
            "structure": "conversational",
            "show_reasoning": True,
            "ask_clarifying_question": False
        },
        "context": "Reasoning question"
    },
    {
        "turn_index": 10,
        "user_message": "Research best practices for memory isolation in multi-tenant systems",
        "expected_signals": {
            "query_type": "explore",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
            "epistemic_query_type": "RESEARCH_REQUIRED",  # "research"
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "medium",
            "structure": "conversational",
            "show_reasoning": False,
            "ask_clarifying_question": False
        },
        "context": "Research request"
    },
    
    # ========================================================================
    # EXECUTE QUERIES (10 examples)
    # ========================================================================
    {
        "turn_index": 11,
        "user_message": "Create a script to validate enforcement invariants",
        "expected_signals": {
            "query_type": "execute",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": True,  # "script"
            "epistemic_query_type": "GENERATIVE_ALLOWED",
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "low",  # execute queries prefer terse
            "structure": "structured",  # artifact requested
            "show_reasoning": False,
            "ask_clarifying_question": False
        },
        "context": "Artifact creation request"
    },
    {
        "turn_index": 12,
        "user_message": "Add instrumentation to the session continuity module",
        "expected_signals": {
            "query_type": "execute",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
            "epistemic_query_type": "GENERATIVE_ALLOWED",
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "low",
            "structure": "conversational",
            "show_reasoning": False,
            "ask_clarifying_question": False
        },
        "context": "Code modification request"
    },
    {
        "turn_index": 13,
        "user_message": "Fix the model selection bug in llm_router.py",
        "expected_signals": {
            "query_type": "execute",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
            "epistemic_query_type": "GENERATIVE_ALLOWED",
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "low",
            "structure": "conversational",
            "show_reasoning": False,
            "ask_clarifying_question": False
        },
        "context": "Bug fix request"
    },
    {
        "turn_index": 14,
        "user_message": "Deploy the changes to staging",
        "expected_signals": {
            "query_type": "execute",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
            "epistemic_query_type": "GENERATIVE_ALLOWED",
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "low",
            "structure": "conversational",
            "show_reasoning": False,
            "ask_clarifying_question": False
        },
        "context": "Deployment command"
    },
    {
        "turn_index": 15,
        "user_message": "Generate a prompt for testing depth detection",
        "expected_signals": {
            "query_type": "execute",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": True,  # "prompt"
            "epistemic_query_type": "GENERATIVE_ALLOWED",
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "low",
            "structure": "structured",
            "show_reasoning": False,
            "ask_clarifying_question": False
        },
        "context": "Prompt generation request"
    },
    {
        "turn_index": 16,
        "user_message": "Update the README with the new instrumentation features",
        "expected_signals": {
            "query_type": "execute",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
            "epistemic_query_type": "GENERATIVE_ALLOWED",
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "low",
            "structure": "conversational",
            "show_reasoning": False,
            "ask_clarifying_question": False
        },
        "context": "Documentation update"
    },
    {
        "turn_index": 17,
        "user_message": "Run the invariant tests",
        "expected_signals": {
            "query_type": "execute",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
            "epistemic_query_type": "GENERATIVE_ALLOWED",
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "low",
            "structure": "conversational",
            "show_reasoning": False,
            "ask_clarifying_question": False
        },
        "context": "Test execution command"
    },
    {
        "turn_index": 18,
        "user_message": "Write a tool to analyze session metadata",
        "expected_signals": {
            "query_type": "execute",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": True,  # "tool"
            "epistemic_query_type": "GENERATIVE_ALLOWED",
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "low",
            "structure": "structured",
            "show_reasoning": False,
            "ask_clarifying_question": False
        },
        "context": "Tool creation request"
    },
    {
        "turn_index": 19,
        "user_message": "Let's add confidence scoring to the mediator",
        "expected_signals": {
            "query_type": "execute",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
            "epistemic_query_type": "GENERATIVE_ALLOWED",
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "low",
            "structure": "conversational",
            "show_reasoning": False,
            "ask_clarifying_question": False
        },
        "context": "Feature addition suggestion"
    },
    {
        "turn_index": 20,
        "user_message": "Search Sentinel for enforcement architecture decisions",
        "expected_signals": {
            "query_type": "execute",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
            "epistemic_query_type": "MEMORY_REQUIRED",
            "tool_required": True,  # explicit "Sentinel" tool assertion
            "tool_name": "sentinel"
        },
        "expected_mediator": {
            "verbosity": "low",
            "structure": "conversational",
            "show_reasoning": False,
            "ask_clarifying_question": False
        },
        "context": "Explicit tool assertion"
    },
    
    # ========================================================================
    # REFLECT QUERIES (10 examples)
    # ========================================================================
    {
        "turn_index": 21,
        "user_message": "Does this approach feel right, or am I overthinking the isolation guarantees?",
        "expected_signals": {
            "query_type": "reflect",
            "depth_requested": False,
            "alignment_signal": True,  # "does this feel right" + "am I overthinking"
            "tools_requested": False,
            "epistemic_query_type": "GENERATIVE_ALLOWED",
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "high",  # reflect queries benefit from dialogue
            "structure": "conversational",
            "show_reasoning": False,
            "ask_clarifying_question": True,  # alignment signal
            "confidence_boost": True  # alignment + reflect should boost confidence
        },
        "context": "Uncertainty expression"
    },
    {
        "turn_index": 22,
        "user_message": "Is this the right way to handle session state?",
        "expected_signals": {
            "query_type": "reflect",
            "depth_requested": False,
            "alignment_signal": True,  # "is this right"
            "tools_requested": False,
            "epistemic_query_type": "GENERATIVE_ALLOWED",
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "high",
            "structure": "conversational",
            "show_reasoning": False,
            "ask_clarifying_question": True,
            "confidence_boost": True
        },
        "context": "Validation request"
    },
    {
        "turn_index": 23,
        "user_message": "What do you think about this personalization strategy?",
        "expected_signals": {
            "query_type": "reflect",
            "depth_requested": False,
            "alignment_signal": False,  # "what do you think" is reflect but not alignment
            "tools_requested": False,
            "epistemic_query_type": "GENERATIVE_ALLOWED",
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "high",
            "structure": "conversational",
            "show_reasoning": False,
            "ask_clarifying_question": False,  # no alignment signal
            "confidence_boost": True  # reflect query
        },
        "context": "Opinion request"
    },
    {
        "turn_index": 24,
        "user_message": "Am I missing something obvious here?",
        "expected_signals": {
            "query_type": "reflect",
            "depth_requested": False,
            "alignment_signal": True,  # "am I missing"
            "tools_requested": False,
            "epistemic_query_type": "GENERATIVE_ALLOWED",
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "high",
            "structure": "conversational",
            "show_reasoning": False,
            "ask_clarifying_question": True,
            "confidence_boost": True
        },
        "context": "Self-doubt expression"
    },
    {
        "turn_index": 25,
        "user_message": "Should I be worried about cross-session leakage?",
        "expected_signals": {
            "query_type": "reflect",
            "depth_requested": False,
            "alignment_signal": True,  # "should I be worried"
            "tools_requested": False,
            "epistemic_query_type": "GENERATIVE_ALLOWED",
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "high",
            "structure": "conversational",
            "show_reasoning": False,
            "ask_clarifying_question": True,
            "confidence_boost": True
        },
        "context": "Concern expression"
    },
    {
        "turn_index": 26,
        "user_message": "Does it make sense to separate these concerns?",
        "expected_signals": {
            "query_type": "reflect",
            "depth_requested": False,
            "alignment_signal": True,  # "make sense"
            "tools_requested": False,
            "epistemic_query_type": "GENERATIVE_ALLOWED",
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "high",
            "structure": "conversational",
            "show_reasoning": False,
            "ask_clarifying_question": True,
            "confidence_boost": True
        },
        "context": "Sanity check"
    },
    {
        "turn_index": 27,
        "user_message": "I'm uncertain about the confidence threshold - thoughts?",
        "expected_signals": {
            "query_type": "reflect",
            "depth_requested": False,
            "alignment_signal": True,  # "uncertain"
            "tools_requested": False,
            "epistemic_query_type": "GENERATIVE_ALLOWED",
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "high",
            "structure": "conversational",
            "show_reasoning": False,
            "ask_clarifying_question": True,
            "confidence_boost": True
        },
        "context": "Explicit uncertainty"
    },
    {
        "turn_index": 28,
        "user_message": "Is this too complex?",
        "expected_signals": {
            "query_type": "reflect",
            "depth_requested": False,
            "alignment_signal": True,  # "is this" (validation)
            "tools_requested": False,
            "epistemic_query_type": "GENERATIVE_ALLOWED",
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "high",
            "structure": "conversational",
            "show_reasoning": False,
            "ask_clarifying_question": True,
            "confidence_boost": True
        },
        "context": "Complexity concern"
    },
    {
        "turn_index": 29,
        "user_message": "How confident are you in this recommendation?",
        "expected_signals": {
            "query_type": "reflect",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
            "epistemic_query_type": "GENERATIVE_ALLOWED",
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "high",
            "structure": "conversational",
            "show_reasoning": False,
            "ask_clarifying_question": False,
            "confidence_boost": True
        },
        "context": "Confidence check"
    },
    {
        "turn_index": 30,
        "user_message": "What are the tradeoffs here?",
        "expected_signals": {
            "query_type": "reflect",
            "depth_requested": False,
            "alignment_signal": False,
            "tools_requested": False,
            "epistemic_query_type": "GENERATIVE_ALLOWED",
            "tool_required": False
        },
        "expected_mediator": {
            "verbosity": "high",
            "structure": "conversational",
            "show_reasoning": False,
            "ask_clarifying_question": False,
            "confidence_boost": True
        },
        "context": "Tradeoff analysis request"
    },
]
