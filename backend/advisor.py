"""
Maestra Backend - Advisor Logic

Handles /advisor/ask endpoint logic.
Uses Jh Brain for context and guidance, Memory Hub for session tracking.
Routes queries to appropriate MCPs based on query type.
"""
import os
import sys
import time
import uuid
import logging
import asyncio
from typing import Optional, List, Tuple

# Add parent paths for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import AdvisorAskRequest, AdvisorAskResponse, SourceReference
from capability_router import route_query
from session_manager import has_capability, get_library_id
from mcp_chain import get_chain_for_query, execute_mcp_chain
from session_continuity import (
    add_turn, get_context_for_next_turn, get_session_summary,
    accumulate_context, record_decision
)
from optimization import (
    cached_query, monitored_endpoint, speculative_executor,
    performance_monitor
)
from llm_router import chat_completion

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
                turns=[t.to_dict() for t in session.turns]
            )
        # Check if it's a library entry ID (16 hex chars)
        elif re.match(r'^[a-f0-9]{16}$', potential_id.lower()):
            # Already handled above via library_context, continue to normal processing
            pass
        else:
            return AdvisorAskResponse(
                answer=f"Conversation '{potential_id}' not found or is empty",
                trace_id=trace_id,
                session_id=request.session_id,
                mode="quick",
                sources=[],
                conversation_id=potential_id,
                turns=[]
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
    session_capabilities = []
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
    
    # Legacy stubs remain for optional Jh Brain wiring, but are no longer used for synthesis by default.
    context, context_sources = await get_context_from_brain(topic=question, focus="global")
    guidance, guidance_sources = await get_guidance_from_brain(request=question, task_type="analyze")
    all_sources.extend(context_sources)
    all_sources.extend(guidance_sources)
    
    # Add routing info to sources
    all_sources.append(SourceReference(
        title=f"Query routed to {routing['primary_capability']}",
        type="routing",
        confidence=routing['confidence'],
        excerpt=f"Query pattern detected: {routing['pattern']}"
    ))
    
    system_prompt = (
        "You are Maestra, the AI assistant for 8825 - a platform that amplifies human operators with AI.\n\n"
        f"{guidance}\n\n"
        f"{context}\n\n"
        "IMPORTANT: If the user provides a PAGE SNAPSHOT in the request (domain/url/title/visible text/selection), "
        "treat it as an authoritative description of what they are seeing. Use it to answer questions like "
        "'what website am I on' or 'can you see what I am seeing' without guessing. "
        "If no snapshot is provided, say you don't have enough context and ask 1-2 focused questions.\n\n"
        "LIBRARY ENTRIES: If the user references an Entry ID (16-character hex string like '5ce9e4d4f0f23d90'), "
        "the content from that library entry will be provided below. Use it to answer their question with full context."
    )

    user_prompt = f"User question: {question}"
    
    # Add library context if any Entry IDs were found and loaded
    if library_context:
        user_prompt += f"\n\n--- LIBRARY CONTEXT ---{library_context}"
        all_sources.append(SourceReference(
            title=f"Library Entries ({len(entry_id_matches)} loaded)",
            type="library",
            confidence=0.95,
            excerpt=f"Entry IDs: {', '.join(entry_id_matches)}"
        ))
    
    # Add conversation history if available
    if previous_context.get('recent_turns'):
        user_prompt += f"\n\nRecent conversation:\n{str(previous_context.get('recent_turns', []))[:1500]}"

    if client_context_text:
        user_prompt += f"\n\nAdditional context:\n{client_context_text}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Record user message in session continuity (for conversation feed)
    add_turn(
        session_id=request.session_id,
        turn_id=f"{trace_id}_user",
        turn_type="user_query",
        content=question,
        metadata={
            "mode": request.mode,
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
            "sources_count": len(all_sources)
        }
    )
    
    processing_time = int((time.time() - start_time) * 1000)
    
    return AdvisorAskResponse(
        answer=answer,
        session_id=request.session_id,
        job_id=None,
        sources=all_sources,
        trace_id=trace_id,
        mode="quick",
        processing_time_ms=processing_time
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
    
    return AdvisorAskResponse(
        answer=f"Deep research job created. Poll /api/maestra/research/{job_id} for status.",
        session_id=request.session_id,
        job_id=job_id,
        sources=[],
        trace_id=trace_id,
        mode="deep",
        processing_time_ms=processing_time
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
