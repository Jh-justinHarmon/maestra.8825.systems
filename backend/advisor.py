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
    logger.info("🟢 MAESTRA_MINIMAL_MODE enabled - using stubs")
    
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
        return ""
    
    def get_session_summary(session_id: str, **kwargs):
        """No summary in minimal mode."""
        return ""
    
    def accumulate_context(session_id: str, context: str, **kwargs):
        """No-op in minimal mode."""
        pass
    
    def record_decision(session_id: str, decision: str, **kwargs):
        """No-op in minimal mode."""
        pass

else:
    logger = logging.getLogger(__name__)
    logger.info("🔴 MAESTRA_MINIMAL_MODE disabled - using full system")
    
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

logger = logging.getLogger(__name__)

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
    
    # Use router-enforced memory search
    return search_memory(session_id, query, max_entries)


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
            
            return AdvisorAskResponse(
                answer=f"Loaded conversation '{potential_id}' with {len(session.turns)} turns",
                trace_id=trace_id,
                session_id=request.session_id,
                mode="quick",
                sources=[
                    SourceReference(
                        title="Conversation History",
                        type="conversation",
                        confidence=1.0,
                        excerpt=f"{len(session.turns)} turns loaded"
                    )
                ],
                conversation_id=potential_id,
                turns=[t.to_dict() for t in session.turns],
                agent=agent_info
            )
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
            
            return AdvisorAskResponse(
                answer=f"Conversation '{potential_id}' not found or is empty",
                trace_id=trace_id,
                session_id=request.session_id,
                mode="quick",
                sources=[],
                conversation_id=potential_id,
                turns=[],
                agent=agent_info
            )
    
    all_sources: List[SourceReference] = []
    
    # Add user query to session continuity
    add_turn(
        session_id=request.session_id,
        turn_id=trace_id,
        turn_type="user_query",
        content=question,
        metadata={"mode": "quick"}
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
    
    routing = route_query(question, session_capabilities)
    logger.info(f"Query routed to: {routing['primary_capability']} (pattern: {routing['pattern']})")

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
    grounding_result = verify_grounding(
        query=question,
        sources=library_sources,
        trace_id=trace_id
    )
    
    logger.info(f"Query type: {query_type.value}, Grounding required: {grounding_result.requires_grounding}, Sources found: {library_found}")
    
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
        return AdvisorAskResponse(
            answer=refused_response.answer,
            trace_id=trace_id,
            session_id=request.session_id,
            mode="quick",
            sources=[],
            epistemic_state=refused_response.epistemic_state.value,
            grounding_sources=refused_response.grounding_sources,
            confidence=refused_response.confidence,
            agent=agent_info
        )
    
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
        chain_results["conversation_history"] = str(previous_context.get('recent_turns', []))[:1500]
    
    # Use context injection to build messages with verified grounding
    messages = inject_context_into_prompt(
        query=question,
        chain_results=chain_results,
        grounding_sources=library_sources,
        epistemic_state=epistemic_state
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
    
    # Add assistant response to session continuity
    add_turn(
        session_id=request.session_id,
        turn_id=trace_id,
        turn_type="assistant_response",
        content=answer,
        metadata={
            "mode": "quick",
            "routing_pattern": routing['pattern'],
            "sources_count": len(all_sources),
            "epistemic_state": epistemic_state.value
        }
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
    
    return AdvisorAskResponse(
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
        agent=agent_info
    )


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
    
    return AdvisorAskResponse(
        answer=f"Deep research job created. Poll /api/maestra/research/{job_id} for status.",
        session_id=request.session_id,
        job_id=job_id,
        sources=[],
        trace_id=trace_id,
        mode="deep",
        processing_time_ms=processing_time,
        agent=agent_info
    )


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
        return await process_quick_question(request)
