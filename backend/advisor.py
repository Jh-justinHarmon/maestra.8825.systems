"""
Maestra Backend - Advisor Logic

Handles /advisor/ask endpoint logic.
Uses Jh Brain for context and guidance, Memory Hub for session tracking.
Routes queries to appropriate MCPs based on query type.

MAESTRA_MINIMAL_MODE: When enabled, uses stubs instead of system dependencies.
"""
import os
import sys
import time
import uuid
import logging
import asyncio
from pathlib import Path
from typing import Optional, List, Tuple

# =============================================================================
# MINIMAL MODE CONFIGURATION
# =============================================================================

MINIMAL_MODE = os.getenv("MAESTRA_MINIMAL_MODE", "false").lower() == "true"

if MINIMAL_MODE:
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ MAESTRA_MINIMAL_MODE=true - EMERGENCY MODE. Using stubs instead of real system.")
    
    # Use stubs instead of system imports
    from stubs.stub_agent_registry import get_agent
    from stubs.stub_agent_telemetry import log_agent_event
    from stubs.stub_routed_memory import search_memory
    
    # Stub functions for features not available in minimal mode
    def ensure_session_initialized(session_id: str):
        """No-op in minimal mode."""
        pass
    
    def get_session_router_state(session_id: str):
        """Returns None in minimal mode."""
        return None
    
    def is_personal_enabled(session_id: str) -> bool:
        """Always False in minimal mode."""
        return False
    
    def has_capability(session_id: str, capability: str) -> bool:
        """No capabilities in minimal mode."""
        return False
    
    def get_library_id(session_id: str) -> Optional[str]:
        """No library in minimal mode."""
        return None
    
    def route_query(query: str, session_id: str):
        """No routing in minimal mode."""
        return None
    
    def get_chain_for_query(query: str):
        """No MCP chains in minimal mode."""
        return None
    
    def execute_mcp_chain(chain, query: str, session_id: str):
        """No MCP execution in minimal mode."""
        return []
    
    def add_turn(session_id: str, **kwargs):
        """No-op in minimal mode. Accepts any parameters."""
        pass
    
    def get_context_for_next_turn(session_id: str, **kwargs):
        """No context in minimal mode."""
        return {"recent_turns": [], "summary": "", "context": ""}
    
    def get_session_summary(session_id: str, **kwargs):
        """No summary in minimal mode."""
        return {"summary": "", "turn_count": 0}
    
    def accumulate_context(session_id: str, context: str, **kwargs):
        """No-op in minimal mode."""
        pass
    
    def record_decision(session_id: str, decision: str, **kwargs):
        """No-op in minimal mode."""
        pass

else:
    logger = logging.getLogger(__name__)
    logger.info("✅ FULL MODE - using real system dependencies")
    
    # Add parent paths for imports
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Add system/agents to path for agent_registry
    AGENTS_PATH = Path(__file__).parent.parent.parent.parent / "system" / "agents"
    sys.path.insert(0, str(AGENTS_PATH))
    
    from agent_registry import get_agent
    from agent_telemetry import log_agent_event
    
    from capability_router import route_query
    from session_manager import has_capability, get_library_id
    from mcp_chain import get_chain_for_query, execute_mcp_chain
    from session_continuity import (
        add_turn, get_context_for_next_turn, get_session_summary,
        accumulate_context, record_decision
    )
    from routed_memory import (
        search_memory,
        ensure_session_initialized,
        get_session_router_state,
        is_personal_enabled
    )

# =============================================================================
# COMMON IMPORTS (Available in both modes)
# =============================================================================

from models import AdvisorAskRequest, AdvisorAskResponse, SourceReference
from turn_instrumentation import instrument_user_turn, instrument_assistant_turn
from conversation_mediator import get_shadow_mediator
from optimization import (
    cached_query, monitored_endpoint, speculative_executor,
    performance_monitor
)
from llm_router import chat_completion
from epistemic import (
    EpistemicState, GroundingSourceType, GroundingSource, GroundingResult,
    classify_query, verify_grounding, EpistemicResponse,
    create_refused_response, create_grounded_response, create_ungrounded_response
)
from context_injection import inject_context_into_prompt
from enforcement_kernel import (
    EnforcementKernel, ContextTrace, ContextSource,
    EnforcementViolation, ContextUnavailable, get_enforcement_kernel
)
from tool_assertion_classifier import classify_tool_assertion, query_requires_sentinel
from mcp_context_adapter import query_sentinel, check_sentinel_available, ContextSource as SentinelContextSource
from models import MCPMetadata
from config import ENABLE_STRUCTURE_ADAPTATION, STRUCTURE_AB_TEST_PERCENTAGE
from ab_test import should_apply_structure
from response_formatter import get_formatting_hint

logger = logging.getLogger(__name__)

# =============================================================================
# ENFORCEMENT KERNEL (NON-BYPASSABLE)
# =============================================================================

def build_context_trace(
    sources: list,
    required_but_missing: list,
    system_mode: str
) -> ContextTrace:
    """
    Build a ContextTrace from response assembly data.
    
    Args:
        sources: List of SourceReference objects used in response
        required_but_missing: List of context sources that were required but unavailable
        system_mode: Current system mode ("full", "minimal", "local_power")
    
    Returns:
        ContextTrace for enforcement
    """
    context_sources = []
    for source in sources:
        if source.type == "library":
            context_sources.append(ContextSource(source="library", identifier=source.title))
        elif source.type == "chain":
            # Chain results may include tool calls
            context_sources.append(ContextSource(source="system"))
        elif source.type == "routing":
            context_sources.append(ContextSource(source="system"))
        elif source.type == "tool":
            # Determine tool type from title
            if "sentinel" in source.title.lower():
                context_sources.append(ContextSource(source="tool:sentinel"))
            elif "research" in source.title.lower():
                context_sources.append(ContextSource(source="tool:deep_research"))
            else:
                context_sources.append(ContextSource(source="tool:external"))
    
    # Default to system if no sources
    if not context_sources:
        context_sources.append(ContextSource(source="system"))
    
    return ContextTrace(
        sources=context_sources,
        required_but_missing=required_but_missing,
        system_mode=system_mode
    )


def enforce_and_return(
    response: AdvisorAskResponse,
    sources: list,
    required_but_missing: list = None,
    system_mode: str = "full",
    epistemic_state: str = "GROUNDED",
    tool_context_used: bool = False
) -> AdvisorAskResponse:
    """
    Enforce speech rules and return response.
    
    This is the ONLY legal exit point for responses.
    All response returns MUST go through this function.
    
    Args:
        response: The assembled response
        sources: List of SourceReference objects used
        required_but_missing: Context that was required but unavailable
        system_mode: Current system mode
        epistemic_state: The epistemic state of the response (GROUNDED, UNGROUNDED, REFUSED)
        tool_context_used: Whether any tool context was successfully invoked
    
    Returns:
        The response (unchanged) if enforcement passes
    
    Raises:
        EnforcementViolation: If response violates speech rules
    """
    from refusal_normalizer import normalize_refusal
    
    if required_but_missing is None:
        required_but_missing = []
    
    # 🔴 HR-1: REFUSAL NORMALIZATION — runs BEFORE enforcement
    # Converts soft refusals to hard refusals with authority="none"
    normalization = normalize_refusal(
        answer=response.answer,
        sources=sources,
        authority=response.authority,
        epistemic_state=epistemic_state,
        tool_context_used=tool_context_used
    )
    
    # Apply normalization if needed
    effective_authority = normalization.normalized_authority
    effective_epistemic_state = normalization.normalized_epistemic_state
    
    # If normalized, we need to update the response
    if normalization.is_soft_refusal and normalization.normalized_authority == "none":
        # Create a new response with normalized values
        response = AdvisorAskResponse(
            answer=normalization.normalized_answer,
            session_id=response.session_id,
            trace_id=response.trace_id,
            mode=response.mode,
            sources=response.sources,
            system_mode=response.system_mode,
            authority="none",  # Normalized
            job_id=response.job_id,
            processing_time_ms=response.processing_time_ms,
            conversation_id=response.conversation_id,
            turns=response.turns,
            agent=response.agent,
        )
        effective_authority = "none"
        effective_epistemic_state = "REFUSED"
    
    context_trace = build_context_trace(sources, required_but_missing, system_mode)
    
    # Create a minimal object for enforcement
    class ResponseForEnforcement:
        def __init__(self, resp, ep_state, auth):
            self.authority = auth
            self.system_mode = resp.system_mode
            self.epistemic_state = ep_state.upper() if isinstance(ep_state, str) else str(ep_state)
    
    enforcement_response = ResponseForEnforcement(response, effective_epistemic_state, effective_authority)
    
    # 🔴 ENFORCEMENT KERNEL — NON-BYPASSABLE
    kernel = get_enforcement_kernel()
    kernel.enforce(enforcement_response, context_trace)
    
    return response

# =============================================================================
# MINIMAL MODE ADVISOR (Bypasses all system dependencies)
# =============================================================================

async def minimal_process_quick_question(request: AdvisorAskRequest) -> AdvisorAskResponse:
    """
    Minimal advisor that only handles:
    1. Query classification
    2. Memory search (always empty in minimal mode)
    3. Grounding verification
    4. Refusal if grounding required
    5. LLM answer if allowed
    
    No routing, no MCP chains, no session continuity.
    """
    question = request.question
    trace_id = str(uuid.uuid4())[:8]
    
    logger.info(f"[MINIMAL MODE] Processing question: {question[:50]}...")
    
    # Step 1: Classify query
    query_type = classify_query(question)
    logger.info(f"[MINIMAL MODE] Query classified as: {query_type}")
    
    # Step 2: Search memory (always returns empty in minimal mode)
    grounding_sources, library_found = search_memory(
        session_id=request.session_id,
        query=question,
        max_entries=5
    )
    logger.info(f"[MINIMAL MODE] Memory search returned {len(grounding_sources)} sources, library_found={library_found}")
    
    # Step 3: Verify grounding
    grounding_result = verify_grounding(
        query=question,
        sources=grounding_sources,
        trace_id=trace_id
    )
    logger.info(f"[MINIMAL MODE] Grounding result: requires_grounding={grounding_result.requires_grounding}, library_found={library_found}")
    
    # Step 4: REFUSAL LOGIC (THE CRITICAL TEST)
    if grounding_result.requires_grounding and not library_found:
        logger.critical(f"🔴 REFUSAL_TRIGGERED | query={question[:50]} | trace_id={trace_id} | requires_grounding=True | library_found=False")
        
        response = AdvisorAskResponse(
            answer=(
                "I need access to your personal memory to answer questions about your specific context, "
                "but I don't have that access right now. This is by design - I only access your memory "
                "when explicitly authorized.\n\n"
                "In minimal mode, personal memory is not available."
            ),
            sources=[],
            epistemic_state=EpistemicState.REFUSED,
            confidence=0.0,
            trace_id=trace_id,
            session_id=request.session_id,
            mode="quick",
            system_mode="minimal",
            authority="none"
        )
        
        logger.critical(f"🔴 REFUSAL_RETURNING | trace_id={trace_id} | epistemic_state=REFUSED")
        return enforce_and_return(response, sources=[], system_mode="minimal", epistemic_state="REFUSED")
    
    logger.critical(f"🔴 REFUSAL_BYPASSED | trace_id={trace_id} | This should not happen for memory-required queries!")
    
    # Step 5: Generate answer (if we got here, query doesn't require grounding)
    logger.info(f"[MINIMAL MODE] Query does not require grounding, generating answer")
    
    messages = [
        {"role": "system", "content": "You are Maestra, a helpful AI assistant. Be concise and direct."},
        {"role": "user", "content": question}
    ]
    
    answer = await chat_completion(messages=messages)
    
    response = AdvisorAskResponse(
        answer=answer,
        sources=[],
        epistemic_state=EpistemicState.UNGROUNDED,
        confidence=0.7,
        trace_id=trace_id,
        session_id=request.session_id,
        mode="quick",
        system_mode="minimal",
        authority="system"  # Ungrounded responses use system authority
    )
    return enforce_and_return(response, sources=[], system_mode="minimal", epistemic_state="UNGROUNDED")

# MCP client paths - these would be replaced with actual MCP calls in production
JH_BRAIN_URL = os.getenv("JH_BRAIN_URL", "http://localhost:8825")
MEMORY_HUB_URL = os.getenv("MEMORY_HUB_URL", "http://localhost:8826")
DEEP_RESEARCH_URL = os.getenv("DEEP_RESEARCH_URL", "http://localhost:8827")


# 8825 Core Knowledge - loaded once at module level
_8825_KNOWLEDGE = None

def _load_8825_knowledge() -> str:
    """Load 8825 manifesto and philosophy from strategic docs."""
    global _8825_KNOWLEDGE
    if _8825_KNOWLEDGE is not None:
        return _8825_KNOWLEDGE
    
    knowledge_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "docs", "strategic", "MANIFESTO_PHILOSOPHY_STRATEGIC_REFERENCE.md"
    )
    
    try:
        with open(knowledge_path, 'r') as f:
            _8825_KNOWLEDGE = f.read()
        logger.info(f"Loaded 8825 knowledge: {len(_8825_KNOWLEDGE)} chars")
    except Exception as e:
        logger.warning(f"Could not load 8825 knowledge: {e}")
        _8825_KNOWLEDGE = ""
    
    return _8825_KNOWLEDGE


def extract_search_keywords(query: str) -> str:
    """
    Extract meaningful search keywords from a natural language question.
    
    Removes common question words and stop words to get searchable terms.
    Handles special identity queries that would otherwise be stripped entirely.
    """
    query_lower = query.lower().strip()
    
    # Special case: identity queries - map to searchable terms
    identity_patterns = [
        'who am i', 'who are you', 'what am i', 'tell me about myself',
        'what do you know about me', 'do you know me', 'my name', 'my profile'
    ]
    for pattern in identity_patterns:
        if pattern in query_lower:
            # Search for user profile, owner, Justin, Harmon, etc.
            return 'Justin Harmon user owner profile'
    
    # Common question words and stop words to remove
    stop_words = {
        'what', 'is', 'are', 'was', 'were', 'who', 'whom', 'which', 'where', 'when',
        'why', 'how', 'can', 'could', 'would', 'should', 'do', 'does', 'did',
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'into', 'through', 'during', 'before',
        'after', 'above', 'below', 'between', 'under', 'again', 'further', 'then',
        'once', 'here', 'there', 'all', 'each', 'few', 'more', 'most', 'other',
        'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
        'too', 'very', 'just', 'about', 'tell', 'me', 'us', 'you', 'your', 'my',
        'our', 'i', 'we', 'they', 'it', 'this', 'that', 'these', 'those', 'be',
        'been', 'being', 'have', 'has', 'had', 'having', 'will', 'shall', 'am'
    }
    
    # Tokenize and filter
    words = query_lower.split()
    keywords = [w.strip('?.,!;:') for w in words if w.strip('?.,!;:') not in stop_words]
    
    # If we filtered everything, use the original query
    if not keywords:
        return query
    
    # Return space-separated keywords for OR-style matching
    return ' '.join(keywords)


def search_8825_library(query: str, max_entries: int = 5, session_id: str = None) -> tuple[List[GroundingSource], bool]:
    """
    Search the 8825 library for relevant context via Context Router.
    
    IMPORTANT: Uses router-enforced memory access. Session must be initialized.
    
    Returns: (grounding_sources, sources_found)
    - grounding_sources: List of GroundingSource objects with actual entries
    - sources_found: True if any sources were found, False if empty
    """
    if session_id is None:
        logger.warning("search_8825_library called without session_id, using default")
        session_id = "default_session"
    
    # Ensure session has a router (creates default system-only if missing)
    ensure_session_initialized(session_id)
    
    # Extract keywords for better search matching
    search_query = extract_search_keywords(query)
    logger.info(f"Library search: original='{query[:50]}' -> keywords='{search_query}'")
    
    # Use router-enforced memory search with extracted keywords
    return search_memory(session_id, search_query, max_entries)


async def get_context_from_brain(topic: str, focus: str = "global") -> Tuple[str, List[SourceReference]]:
    """
    Get context from 8825 knowledge base.
    
    Loads manifesto, philosophy, and strategic reference for context.
    """
    knowledge = _load_8825_knowledge()
    
    # Extract relevant sections based on topic keywords
    topic_lower = topic.lower()
    context_parts = []
    
    # Always include core manifesto for 8825-related queries
    if any(kw in topic_lower for kw in ['8825', 'maestra', 'philosophy', 'context', 'ai', 'work', 'help']):
        # Include key sections
        context_parts.append("8825 CORE KNOWLEDGE:\n")
        context_parts.append(knowledge[:4000])  # First 4000 chars covers manifesto + pillars
    
    context = "\n".join(context_parts) if context_parts else f"Topic: {topic}"
    
    sources = [
        SourceReference(
            title="8825 Manifesto & Philosophy",
            type="knowledge",
            confidence=0.95,
            excerpt="Core 8825 philosophy: AI amplifies people, context is power, collaboration over automation"
        )
    ]
    
    return context, sources


async def get_guidance_from_brain(request: str, task_type: str = "analyze") -> Tuple[str, List[SourceReference]]:
    """
    Get philosophy-based guidance from 8825 principles.
    
    Applies 8825 brand voice and philosophy to guide responses.
    """
    guidance = """
8825 RESPONSE GUIDELINES:
- Be direct, specific, and helpful
- AI amplifies people, doesn't replace them
- Context is power - use what you know about the user's situation
- Collaboration over automation
- Real work > theoretical frameworks
- Never be cold, robotic, or jargon-heavy
- Sound confident but never arrogant
- If you don't know something, say so clearly
"""
    
    sources = [
        SourceReference(
            title="8825 Philosophy",
            type="protocol",
            confidence=0.9,
            excerpt="Applied 8825 principles: amplify people, context is power, collaboration over automation"
        )
    ]
    
    return guidance, sources


async def create_research_job(target: str) -> str:
    """
    Create a deep research job.
    
    In production, this calls mcp3_research_create_job.
    """
    # Simulated response - in production, call deep-research MCP
    # This would be: result = await research_create_job(target=target, preset="balanced")
    
    job_id = f"research_{uuid.uuid4().hex[:12]}"
    logger.info(f"Created research job {job_id} for target: {target}")
    
    return job_id


async def log_to_memory(session_id: str, event_type: str, payload: dict) -> None:
    """
    Log an event to Memory Hub.
    
    In production, this calls mcp13_memory_append_event.
    """
    # Simulated - in production, call Memory Hub MCP
    # This would be: await memory_append_event(session_id=session_id, event_type=event_type, payload=payload)
    
    logger.info(f"Memory event logged: {event_type} for session {session_id}")


async def process_quick_question(request: AdvisorAskRequest) -> AdvisorAskResponse:
    """
    Process a quick question using Jh Brain context and guidance.
    Routes to appropriate MCPs based on query type.
    Maintains session continuity across turns.
    """
    import re
    import json
    from pathlib import Path
    
    start_time = time.time()
    trace_id = str(uuid.uuid4())
    question = request.get_question
    
    # Check for Entry ID references in the question
    # Entry IDs are 16-character hex strings like "5ce9e4d4f0f23d90"
    entry_id_pattern = r'\b([a-f0-9]{16})\b'
    entry_id_matches = re.findall(entry_id_pattern, question.lower())
    
    library_context = ""
    if entry_id_matches:
        # Try to load library entries
        possible_paths = [
            Path(__file__).parent.parent.parent.parent / "shared" / "8825-library",
            Path("/Users/justinharmon/Hammer Consulting Dropbox/Justin Harmon/8825-Team/shared/8825-library"),
        ]
        
        library_dir = None
        for path in possible_paths:
            if path.exists():
                library_dir = path
                break
        
        if library_dir:
            for entry_id in entry_id_matches:
                entry_file = library_dir / f"{entry_id}.json"
                if entry_file.exists():
                    try:
                        with open(entry_file, 'r') as f:
                            entry = json.load(f)
                        library_context += f"\n\n--- LIBRARY ENTRY {entry_id} ---\n"
                        library_context += f"Title: {entry.get('title', 'Untitled')}\n"
                        library_context += f"Source: {entry.get('source', 'unknown')}\n"
                        library_context += f"Content: {entry.get('content', '')}\n"
                        library_context += "--- END ENTRY ---\n"
                        logger.info(f"Loaded library entry: {entry_id}")
                    except Exception as e:
                        logger.warning(f"Failed to load library entry {entry_id}: {e}")
    
    # Check if the message looks like a session_id or conversation reference
    # Accept: session_ids, UUIDs, or "load <id>" format
    load_match = re.match(r'^(?:load\s+)?([a-zA-Z0-9_-]+)$', question.strip(), re.IGNORECASE)
    if load_match:
        potential_id = load_match.group(1)
        # Try to load this as a session
        from session_continuity import continuity_tracker
        session = continuity_tracker.get_session_state(potential_id)
        if session.turns:
            # Return the loaded conversation
            # Resolve agent identity
            agent = get_agent("assistant")
            agent_info = {
                "id": agent.agent_id,
                "display_name": agent.display_name
            } if agent else {"id": "assistant", "display_name": "Assistant"}
            
            conv_sources = [
                SourceReference(
                    title="Conversation History",
                    type="conversation",
                    confidence=1.0,
                    excerpt=f"{len(session.turns)} turns loaded"
                )
            ]
            response = AdvisorAskResponse(
                answer=f"Loaded conversation '{potential_id}' with {len(session.turns)} turns",
                trace_id=trace_id,
                session_id=request.session_id,
                mode="quick",
                sources=conv_sources,
                conversation_id=potential_id,
                turns=[t.to_dict() for t in session.turns],
                agent=agent_info,
                system_mode="full",
                authority="memory"
            )
            return enforce_and_return(response, sources=conv_sources, system_mode="full", epistemic_state="GROUNDED")
        # Check if it's a library entry ID (16 hex chars)
        elif re.match(r'^[a-f0-9]{16}$', potential_id.lower()):
            # Already handled above via library_context, continue to normal processing
            pass
        else:
            # Resolve agent identity
            agent = get_agent("assistant")
            agent_info = {
                "id": agent.agent_id,
                "display_name": agent.display_name
            } if agent else {"id": "assistant", "display_name": "Assistant"}
            
            response = AdvisorAskResponse(
                answer=f"Conversation '{potential_id}' not found or is empty",
                trace_id=trace_id,
                session_id=request.session_id,
                mode="quick",
                sources=[],
                conversation_id=potential_id,
                turns=[],
                agent=agent_info,
                system_mode="full",
                authority="system"  # No memory sources, use system
            )
            return enforce_and_return(response, sources=[], system_mode="full", epistemic_state="UNGROUNDED")
    
    all_sources: List[SourceReference] = []
    
    # Capture start time for latency measurement
    start_time_ms = int(time.time() * 1000)
    
    # Classify query early for metadata logging (behavior unchanged)
    query_type_classification = classify_query(question)
    tool_assertion_classification = classify_tool_assertion(question)
    
    # Add user query to session continuity with instrumentation
    user_metadata = instrument_user_turn(
        query=question,
        start_time_ms=start_time_ms,
        epistemic_query_type=query_type_classification.value,
        tool_required=tool_assertion_classification.requires_tool,
        tool_name=tool_assertion_classification.tool_name if tool_assertion_classification.requires_tool else None,
        classification_confidence=tool_assertion_classification.confidence
    )
    user_metadata["mode"] = "quick"  # Preserve existing metadata
    
    add_turn(
        session_id=request.session_id,
        turn_id=trace_id,
        turn_type="user_query",
        content=question,
        metadata=user_metadata
    )
    
    # Get context from previous turns
    previous_context = get_context_for_next_turn(request.session_id)
    logger.info(f"Session has {len(previous_context['recent_turns'])} recent turns")
    
    # Route query to appropriate capabilities
    # Always include context_builder and library_bridge - they're local file-based, always available
    session_capabilities = ["context_builder", "library_bridge"]
    if has_capability(request.session_id, "context_for_query"):
        session_capabilities.append("local_companion")
    if has_capability(request.session_id, "open_loops"):
        session_capabilities.append("local_companion")
    
    # Skip routing in minimal mode
    if not MINIMAL_MODE:
        routing = route_query(question, session_capabilities)
        logger.info(f"Query routed to: {routing['primary_capability']} (pattern: {routing['pattern']})")
    else:
        logger.info("Minimal mode - skipping query routing")

    # Client-provided context (e.g., from extension/local companion) is the primary context source in prod.
    client_context_text = ""
    if request.client_context:
        try:
            summary = request.client_context.get("summary") if isinstance(request.client_context, dict) else None
            if summary:
                client_context_text += f"\n\nLocal Companion Summary:\n{summary}\n"
                all_sources.append(SourceReference(
                    title="Local Companion Context",
                    type="local_context",
                    confidence=0.9,
                    excerpt=str(summary)[:500]
                ))

            relevant = request.client_context.get("relevant") if isinstance(request.client_context, dict) else None
            if isinstance(relevant, list) and relevant:
                all_sources.append(SourceReference(
                    title=f"Local Companion Relevant Items ({len(relevant)})",
                    type="local_context",
                    confidence=0.8,
                    excerpt=str(relevant)[:500]
                ))

            selection = request.client_context.get("selection") if isinstance(request.client_context, dict) else None
            if selection:
                client_context_text += f"\n\nUser Selection:\n{selection}\n"

            # Extension/browser snapshot (authoritative description of what the user is seeing)
            page_snapshot = request.client_context.get("page_snapshot") if isinstance(request.client_context, dict) else None
            if isinstance(page_snapshot, dict) and page_snapshot:
                ps_url = page_snapshot.get("url")
                ps_title = page_snapshot.get("title")
                ps_domain = page_snapshot.get("domain")
                ps_timestamp = page_snapshot.get("timestamp")
                ps_selection = page_snapshot.get("selection")
                ps_visible_text = page_snapshot.get("visible_text")

                # Some clients may also send visible_text at top-level
                if not ps_visible_text and isinstance(request.client_context, dict):
                    ps_visible_text = request.client_context.get("visible_text")

                client_context_text += "\n\nPAGE SNAPSHOT (AUTHORITATIVE):\n"
                if ps_domain or ps_title:
                    client_context_text += f"Domain: {ps_domain or ''}\nTitle: {ps_title or ''}\n"
                if ps_url:
                    client_context_text += f"URL: {ps_url}\n"
                if ps_timestamp:
                    client_context_text += f"Captured At: {ps_timestamp}\n"
                if ps_selection:
                    client_context_text += f"\nSelection on page:\n{str(ps_selection)[:2000]}\n"
                if ps_visible_text:
                    client_context_text += f"\nVisible text (viewport, truncated):\n{str(ps_visible_text)[:4000]}\n"

                all_sources.append(SourceReference(
                    title="Page Snapshot (extension)",
                    type="page_snapshot",
                    confidence=0.95,
                    excerpt=f"{(ps_domain or '')} {(ps_title or '')}".strip()[:500]
                ))
        except Exception:
            # Best effort; proceed without client context
            pass
    
    # Check if we should use MCP chaining for this query
    chain = await get_chain_for_query(question, routing)
    print(f"[DEBUG] Chain returned: {chain is not None}, routing pattern: {routing.get('pattern')}")
    if chain:
        logger.info(f"Using MCP chain with {len(chain)} steps")
        chain_result = await execute_mcp_chain(
            chain=chain,
            query=question,
            session_context=previous_context,
            available_capabilities=session_capabilities
        )
        
        if chain_result.success:
            all_sources.append(SourceReference(
                title=f"Multi-step intelligence ({len(chain_result.steps_executed)} steps)",
                type="chain",
                confidence=0.9,
                excerpt=f"Executed: {', '.join(chain_result.steps_executed)}"
            ))
            # Inject chain context into the prompt
            chain_context = chain_result.results.get("gather_context", {}).get("context_text", "")
            if chain_context:
                library_context += f"\n\n--- MEMORY CONTEXT ---\n{chain_context}"
                logger.info(f"Added chain context ({len(chain_context)} chars) to prompt")
    
    # Gather grounding sources from library (router-enforced)
    library_sources, library_found = search_8825_library(question, session_id=request.session_id)
    
    # Classify query to determine if grounding is required
    query_type = classify_query(question)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TRACK 5: SENTINEL MCP INTEGRATION
    # ═══════════════════════════════════════════════════════════════════════════
    # Check if query requires Sentinel (explicit tool assertion)
    tool_assertion = classify_tool_assertion(question)
    sentinel_sources = []
    sentinel_errors = []
    sentinel_required_but_missing = False
    tool_context_used = False
    
    if tool_assertion.requires_tool and tool_assertion.tool_name in ["sentinel", "internal_documents"]:
        logger.info(f"🔧 Tool assertion detected: {tool_assertion.tool_name} required for query")
        
        # Query Sentinel MCP
        try:
            sentinel_sources, sentinel_errors, sentinel_required_but_missing = await query_sentinel(
                query=question,
                required=True,  # Tool was explicitly asserted
                max_results=10
            )
            
            if sentinel_sources:
                tool_context_used = True
                logger.info(f"✅ Sentinel returned {len(sentinel_sources)} sources")
                
                # Add Sentinel sources to all_sources with tool type
                for src in sentinel_sources:
                    # SentinelContextSource has: type, excerpt, confidence, artifact_id, uri, timestamp
                    artifact_label = src.artifact_id or "artifact"
                    excerpt_text = src.excerpt[:200] if src.excerpt else ""
                    
                    all_sources.append(SourceReference(
                        title=f"Sentinel: {artifact_label}",
                        type="tool",
                        confidence=src.confidence,
                        excerpt=excerpt_text
                    ))
                    # Also add to library_sources for grounding
                    library_sources.append(GroundingSource(
                        source_type=GroundingSourceType.TOOL,
                        identifier=src.artifact_id or "sentinel",
                        title=f"Sentinel: {artifact_label}",
                        confidence=src.confidence,
                        excerpt=src.excerpt
                    ))
                library_found = True  # Sentinel sources count as found
            else:
                logger.warning(f"⚠️ Sentinel returned no sources (errors: {sentinel_errors})")
                # If Sentinel returned no sources but was required, mark as missing
                if tool_assertion.required:
                    sentinel_required_but_missing = True
                
        except Exception as e:
            logger.error(f"❌ Sentinel query failed: {e}")
            sentinel_required_but_missing = True
            sentinel_errors.append(str(e))
        
        # If Sentinel was required but unavailable, refuse immediately
        if sentinel_required_but_missing:
            logger.critical(f"🔴 SENTINEL_REQUIRED_BUT_MISSING | query={question[:50]} | errors={sentinel_errors}")
            
            # Build MCP metadata for disclosure
            mcp_metadata = MCPMetadata(
                mcp_used=False,
                sentinel_available=False,
                sentinel_artifacts=0,
                tool_sources=[],
                retry_guidance="Sentinel is currently unavailable. Try again later or rephrase without referencing Sentinel."
            )
            
            response = AdvisorAskResponse(
                answer=(
                    f"I cannot answer this question because it requires Sentinel, "
                    f"which is currently unavailable.\n\n"
                    f"Your query explicitly referenced '{tool_assertion.matched_pattern}', "
                    f"which requires tool access I don't have right now.\n\n"
                    f"**What would help:**\n"
                    f"- Try again later when Sentinel is available\n"
                    f"- Rephrase your question without referencing Sentinel"
                ),
                trace_id=trace_id,
                session_id=request.session_id,
                mode="quick",
                sources=[],
                system_mode="full",
                authority="none",
                mcp_metadata=mcp_metadata
            )
            return enforce_and_return(
                response, 
                sources=[], 
                required_but_missing=["sentinel"],
                system_mode="full", 
                epistemic_state="REFUSED"
            )
    # ═══════════════════════════════════════════════════════════════════════════
    
    grounding_result = verify_grounding(
        query=question,
        sources=library_sources,
        trace_id=trace_id
    )
    
    logger.info(f"Query type: {query_type.value}, Grounding required: {grounding_result.requires_grounding}, Sources found: {library_found}, Tool context: {tool_context_used}")
    
    # If grounding is required but no sources found, refuse to answer
    if grounding_result.requires_grounding and not library_found:
        logger.critical(f"🔴 REFUSAL_TRIGGERED | query={question[:50]} | requires_grounding={grounding_result.requires_grounding} | library_found={library_found} | trace_id={trace_id}")
        logger.warning(f"Query requires grounding but no sources found: {question[:50]}")
        
        # Return REFUSED response
        refused_response = create_refused_response(
            query=question,
            trace_id=trace_id,
            what_would_help=[
                "Library entries about this topic",
                "Recent decisions or context",
                "Project history or background"
            ]
        )
        
        # Resolve agent identity for refused response
        agent_id = "analyst"  # Refusals come from Analyst
        agent = get_agent(agent_id)
        agent_info = {
            "id": agent.agent_id,
            "display_name": agent.display_name
        } if agent else {"id": "analyst", "display_name": "Analyst"}
        
        # Telemetry: agent_refused
        log_agent_event(
            event_type="agent_refused",
            agent_id=agent_id,
            query=question,
            auto_selected=True,  # Refusals are always from auto-selected Analyst
            session_id=request.session_id,
            metadata={"trace_id": trace_id, "epistemic_state": "REFUSED"}
        )
        
        logger.critical(f"🔴 REFUSAL_RETURNING | trace_id={trace_id} | epistemic_state=REFUSED | about_to_return=True")
        response = AdvisorAskResponse(
            answer=refused_response.answer,
            trace_id=trace_id,
            session_id=request.session_id,
            mode="quick",
            sources=[],
            epistemic_state=refused_response.epistemic_state.value,
            grounding_sources=refused_response.grounding_sources,
            confidence=refused_response.confidence,
            agent=agent_info,
            system_mode="full",
            authority="none"  # Refusals must claim authority="none"
        )
        return enforce_and_return(response, sources=[], system_mode="full", epistemic_state="REFUSED")
    
    logger.critical(f"🔴 REFUSAL_BYPASSED | trace_id={trace_id} | execution_continued_past_refusal_block=True | THIS_SHOULD_NOT_HAPPEN")
    
    # Add library sources to all_sources
    if library_sources:
        for source in library_sources:
            all_sources.append(SourceReference(
                title=source.title,
                type="library",
                confidence=source.confidence,
                excerpt=source.excerpt or ""
            ))
        logger.info(f"Added {len(library_sources)} library sources to response")
    
    # Add routing info to sources
    all_sources.append(SourceReference(
        title=f"Query routed to {routing['primary_capability']}",
        type="routing",
        confidence=routing['confidence'],
        excerpt=f"Query pattern detected: {routing['pattern']}"
    ))
    
    # Determine epistemic state based on grounding
    if grounding_result.requires_grounding and library_found:
        epistemic_state = EpistemicState.GROUNDED
    elif not grounding_result.requires_grounding:
        epistemic_state = EpistemicState.UNGROUNDED
    else:
        epistemic_state = EpistemicState.REFUSED
    
    # Check actual 8825 system availability
    system_status = {
        "library_available": library_found,
        "library_entries": len(library_sources) if library_sources else 0,
        "jh_brain": "unknown",  # From health check
        "memory_hub": "unknown",
        "deep_research": "unknown"
    }
    
    # Build base system prompt with anti-hallucination constraints AND honest availability reporting
    base_system_prompt = (
        "You are Maestra, the intelligence layer for the 8825 browser extension.\n\n"
        "SURFACE ARCHITECTURE:\n"
        "- This is a thin-client browser extension with NO local intelligence\n"
        "- You (Maestra) are the brain - all decisions, memory, and tools live in your backend\n"
        "- The extension only provides UI and basic page context\n\n"
        "OPERATING CONSTRAINTS:\n"
        "- PARTIAL CONTEXT: The extension provides limited context (URL, title, domain, selection)\n"
        "- LOSSY INFORMATION: Not all page details are captured - work with what's provided\n"
        "- NO GUESSING: If you don't have the required context, explicitly state what you need\n"
        "- ACKNOWLEDGE LIMITATIONS: Be clear about what you can and cannot see\n\n"
        f"CURRENT 8825 SYSTEM STATUS:\n"
        f"- Library: {'✓ Available' if system_status['library_available'] else '✗ Not available'} "
        f"({system_status['library_entries']} entries found)\n"
        f"- Jh Brain: {system_status['jh_brain']}\n"
        f"- Memory Hub: {system_status['memory_hub']}\n"
        f"- Deep Research: {system_status['deep_research']}\n\n"
        "CRITICAL: If the user asks about 8825 systems, projects, or knowledge and the library shows "
        "'Not available' or 0 entries, you MUST say: 'I'm not currently connected to the 8825 library. "
        "I cannot access project history, decisions, or knowledge without it.'\n"
        "DO NOT pretend to have access to systems that show 'unknown' or 'Not available'.\n\n"
        "RESPONSE GUIDELINES:\n"
        "- If the user provides a PAGE SNAPSHOT (domain/url/title/selection), treat it as authoritative\n"
        "- If NO snapshot is provided, say: 'I cannot answer this question because I don't have the required context. "
        "To help you, I would need: [specific items]'\n"
        "- Never make up information about the page or user's context\n"
        "- If you need more context, ask 1-2 focused questions\n\n"
        "LIBRARY ENTRIES: If the user references an Entry ID (16-character hex string like '5ce9e4d4f0f23d90'), "
        "the content from that library entry will be provided below. Use it to answer their question with full context."
    )
    
    # Build chain results dictionary for context injection
    chain_results = {}
    if library_context:
        chain_results["library_context"] = library_context
    if client_context_text:
        chain_results["client_context"] = client_context_text
    if previous_context.get('recent_turns'):
        chain_results["conversation_history"] = str(previous_context.get('recent_turns', []))[:8000]
    
    # Shadow Mediator: Compute response-shaping decision
    shadow_mediator = get_shadow_mediator()
    mediator_decision = shadow_mediator.compute_decision(
        query=question,
        recent_turns=previous_context.get('recent_turns', []),
        query_metadata=user_metadata,
        session_context=previous_context
    )
    # Store decision in assistant metadata for telemetry
    mediator_decision_dict = mediator_decision.to_dict()
    
    # Structure Adaptation: Determine if structured formatting should be applied
    apply_structure, ab_group = should_apply_structure(
        tools_requested=user_metadata.get("tools_requested", False),
        mediator_structure=mediator_decision.structure,
        mediator_confidence=mediator_decision.confidence,
        session_id=request.session_id,
        feature_enabled=ENABLE_STRUCTURE_ADAPTATION,
        test_percentage=STRUCTURE_AB_TEST_PERCENTAGE
    )
    
    # Get formatting hint if structure should be applied
    formatting_hint = get_formatting_hint(apply_structure) if apply_structure else None
    
    # Use context injection to build messages with verified grounding
    # NOTE: formatting_hint is added to system prompt if structure is enabled
    messages = inject_context_into_prompt(
        query=question,
        chain_results=chain_results,
        grounding_sources=library_sources,
        epistemic_state=epistemic_state,
        formatting_hint=formatting_hint
    )
    
    logger.info(f"Built messages with epistemic_state={epistemic_state.value}, sources={len(library_sources)}")

    # Record user message in session continuity (for conversation feed)
    add_turn(
        session_id=request.session_id,
        turn_id=f"{trace_id}_user",
        turn_type="user_query",
        content=question,
        metadata={
            "mode": request.mode,
            "epistemic_state": epistemic_state.value,
            "has_page_snapshot": bool(request.client_context and request.client_context.get('page_snapshot'))
        }
    )

    # LLM synthesis (OpenRouter default; OpenAI/Anthropic fallbacks)
    answer = await chat_completion(messages=messages)
    
    # Log to memory
    await log_to_memory(
        session_id=request.session_id,
        event_type="tool_use",
        payload={
            "tool": "maestra_advisor",
            "question": question,
            "mode": "quick",
            "trace_id": trace_id
        }
    )
    
    # Add assistant response to session continuity with instrumentation
    tools_used = []
    if sentinel_sources:
        tools_used.append("sentinel")
    if routing and routing.get('pattern'):
        tools_used.append(routing['pattern'])
    
    assistant_metadata = instrument_assistant_turn(
        response=answer,
        start_time_ms=start_time_ms,
        query_type=user_metadata.get("query_type"),
        tools_used=tools_used if tools_used else None,
        confidence=grounding_result.confidence if grounding_result else None
    )
    
    # Preserve existing metadata
    assistant_metadata.update({
        "mode": "quick",
        "routing_pattern": routing['pattern'],
        "sources_count": len(all_sources),
        "epistemic_state": epistemic_state.value,
        "shadow_mediator_decision": mediator_decision_dict,
        "ab_test_group": ab_group,  # A/B test group assignment
        "structure_applied": apply_structure,  # Whether structured formatting was applied
        "structure_feature_enabled": ENABLE_STRUCTURE_ADAPTATION  # Feature flag state
    })
    
    add_turn(
        session_id=request.session_id,
        turn_id=trace_id,
        turn_type="assistant_response",
        content=answer,
        metadata=assistant_metadata
    )
    
    processing_time = int((time.time() - start_time) * 1000)
    
    # Convert grounding sources to response format
    grounding_sources_response = [
        {
            "type": source.source_type.value,
            "identifier": source.identifier,
            "title": source.title,
            "confidence": source.confidence,
            "excerpt": source.excerpt,
            "timestamp": source.timestamp
        }
        for source in library_sources
    ]
    
    # Resolve agent identity for response
    # Default to assistant if agent selection not yet integrated
    agent_id = "assistant"  # Will be replaced with orchestrator.run() integration
    agent = get_agent(agent_id)
    agent_info = {
        "id": agent.agent_id,
        "display_name": agent.display_name
    } if agent else {"id": "assistant", "display_name": "Assistant"}
    
    # Telemetry: agent_answered
    log_agent_event(
        event_type="agent_answered",
        agent_id=agent_id,
        query=question,
        auto_selected=True,  # Will be replaced with actual auto_selected value
        session_id=request.session_id,
        metadata={
            "trace_id": trace_id,
            "epistemic_state": epistemic_state.value,
            "sources_count": len(all_sources),
            "processing_time_ms": processing_time
        }
    )
    
    # Determine authority based on source types (tool > memory > system)
    has_tool_sources = any(s.type == "tool" for s in all_sources)
    has_library_sources = any(s.type == "library" for s in all_sources)
    
    if has_tool_sources:
        authority = "tool"  # Tool sources take precedence
    elif has_library_sources:
        authority = "memory"
    else:
        authority = "system"
    
    # Build MCP metadata for disclosure
    mcp_metadata = MCPMetadata(
        mcp_used=has_tool_sources,
        sentinel_available=True if has_tool_sources else False,
        sentinel_artifacts=len([s for s in all_sources if s.type == "tool"]),
        tool_sources=["sentinel"] if has_tool_sources else [],
        retry_guidance=None
    )
    
    response = AdvisorAskResponse(
        answer=answer,
        session_id=request.session_id,
        job_id=None,
        sources=all_sources,
        trace_id=trace_id,
        mode="quick",
        processing_time_ms=processing_time,
        epistemic_state=epistemic_state.value,
        grounding_sources=grounding_sources_response,
        confidence=grounding_result.confidence,
        agent=agent_info,
        system_mode="full",
        authority=authority,
        mcp_metadata=mcp_metadata
    )
    return enforce_and_return(response, sources=all_sources, system_mode="full", epistemic_state=epistemic_state.value, tool_context_used=has_tool_sources)


async def process_deep_question(request: AdvisorAskRequest) -> AdvisorAskResponse:
    """
    Process a deep question by creating a research job.
    """
    start_time = time.time()
    trace_id = str(uuid.uuid4())
    question = request.get_question
    
    # Create research job
    job_id = await create_research_job(target=question)
    
    # Log to memory
    await log_to_memory(
        session_id=request.session_id,
        event_type="tool_use",
        payload={
            "tool": "maestra_advisor",
            "question": question,
            "mode": "deep",
            "job_id": job_id,
            "trace_id": trace_id
        }
    )
    
    processing_time = int((time.time() - start_time) * 1000)
    
    # Resolve agent identity
    agent = get_agent("assistant")
    agent_info = {
        "id": agent.agent_id,
        "display_name": agent.display_name
    } if agent else {"id": "assistant", "display_name": "Assistant"}
    
    response = AdvisorAskResponse(
        answer=f"Deep research job created. Poll /api/maestra/research/{job_id} for status.",
        session_id=request.session_id,
        job_id=job_id,
        sources=[],
        trace_id=trace_id,
        mode="deep",
        processing_time_ms=processing_time,
        agent=agent_info,
        system_mode="full",
        authority="system"
    )
    return enforce_and_return(response, sources=[], system_mode="full", epistemic_state="UNGROUNDED")


@monitored_endpoint("advisor_ask")
async def ask_advisor(request: AdvisorAskRequest) -> AdvisorAskResponse:
    """
    Main entry point for advisor questions.
    
    Routes to quick or deep processing based on mode.
    Includes performance monitoring and speculative prefetch.
    """
    start_time = time.time()
    question = request.get_question
    logger.info(f"Advisor request: session={request.session_id}, mode={request.mode}, question={question[:50] if question else 'empty'}...")
    
    # Trigger speculative prefetch for likely next queries
    asyncio.create_task(
        speculative_executor.speculative_prefetch(
            current_query=question,
            fetch_fn=lambda q: process_quick_question(AdvisorAskRequest(
                session_id=request.session_id,
                question=q,
                mode="quick"
            )),
            top_k=2
        )
    )
    
    if request.mode == "deep":
        return await process_deep_question(request)
    else:
        # Use minimal advisor in minimal mode
        if MINIMAL_MODE:
            return await minimal_process_quick_question(request)
        else:
            return await process_quick_question(request)
