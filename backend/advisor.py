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


async def get_context_from_brain(topic: str, focus: str = "global") -> Tuple[str, List[SourceReference]]:
    """
    Get context from Jh Brain on a topic.
    
    In production, this calls mcp8_jh_brain_get_context.
    """
    # Simulated response - in production, call Jh Brain MCP
    # This would be: result = await jh_brain_get_context(topic=topic, focus=focus)
    
    context = f"Context retrieved for: {topic}"
    sources = [
        SourceReference(
            title="Jh Brain Context",
            type="knowledge",
            confidence=0.8,
            excerpt=f"Retrieved context for topic: {topic}"
        )
    ]
    
    return context, sources


async def get_guidance_from_brain(request: str, task_type: str = "analyze") -> Tuple[str, List[SourceReference]]:
    """
    Get philosophy-based guidance from Jh Brain.
    
    In production, this calls mcp8_jh_brain_guidance.
    """
    # Simulated response - in production, call Jh Brain MCP
    # This would be: result = await jh_brain_guidance(request=request, task_type=task_type)
    
    guidance = f"Guidance for: {request}"
    sources = [
        SourceReference(
            title="8825 Philosophy",
            type="protocol",
            confidence=0.9,
            excerpt="Applied 8825 principles to generate guidance"
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
    start_time = time.time()
    trace_id = str(uuid.uuid4())
    question = request.get_question
    
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

    # Client-provided context (e.g., from local companion) is the primary context source in prod.
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
        "You are Maestra, an expert assistant for operations, execution, and planning. "
        "Be direct, specific, and helpful. If context is insufficient, ask 1-2 focused questions. "
        "Do not mention internal implementation details."
    )

    user_prompt = (
        f"User question:\n{question}\n\n"
        f"Session summary (best-effort):\n{previous_context.get('session_summary', '')}\n\n"
        f"Recent turns (best-effort):\n{str(previous_context.get('recent_turns', []))[:1500]}\n"
    )

    if client_context_text:
        user_prompt += f"\n\n{client_context_text}\n"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

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
