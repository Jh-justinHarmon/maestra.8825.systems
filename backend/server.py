"""
Maestra Backend Server

FastAPI service powering the Maestra browser extension.

Endpoints:
- POST /api/maestra/advisor/ask - Ask the advisor a question
- GET /api/maestra/context/{session_id} - Get session context
- GET /api/maestra/research/{job_id} - Get research job status
- GET /health - Health check
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
import uuid
from datetime import datetime, date
from pydantic import BaseModel
from typing import Optional
import os
import sys
from collections import defaultdict

from models import (
    AdvisorAskRequest,
    AdvisorAskResponse,
    ContextSummaryResponse,
    ResearchStatusResponse,
    HealthResponse,
    SmartPDFExportRequest,
    SmartPDFExportResponse,
    SmartPDFImportRequest,
    SmartPDFImportResponse
)
from advisor import ask_advisor
from context import get_session_context
from research import get_research_status
from smart_pdf_handler import export_smart_pdf_handler, import_smart_pdf_handler
from session_manager import register_session, get_session, has_capability, SessionCapabilities, SessionInfo
from llm_router import get_configured_llm_provider, LLMConfigurationError
from collaboration import (
    get_or_create_team, add_session_to_team, track_document,
    get_team_context_for_session
)
from learning_loop import (
    record_feedback, record_quality_score, get_feedback_summary,
    get_routing_accuracy, get_mcp_performance
)
from identity import get_identity

# Setup logging
# LLM call tracking (in-memory; resets on restart)
llm_call_counter = defaultdict(int)  # date -> count
daily_quota = int(os.getenv("DAILY_LLM_QUOTA", "10000"))  # Default 10k calls/day
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Memory Assimilator integration (used by Capture)
try:
    # server.py is at 8825_core/tools/8825_backend/server.py
    # We want  8825_core/brain/memory_assimilator
    TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ASSIMILATOR_DIR = os.path.join(TOOLS_DIR, "..", "brain", "memory_assimilator")
    if os.path.exists(ASSIMILATOR_DIR) and ASSIMILATOR_DIR not in sys.path:
        sys.path.insert(0, ASSIMILATOR_DIR)
    from pipeline import get_pipeline  # type: ignore
    HAS_ASSIMILATOR = True
except Exception as e:  # pragma: no cover - best-effort wiring
    logger.warning(f"Memory Assimilator unavailable: {e}")
    HAS_ASSIMILATOR = False
    get_pipeline = None  # type: ignore

# Ingestion Orchestrator integration
try:
    ORCHESTRATOR_DIR = os.path.join(TOOLS_DIR, "..", "agents", "ingestion_orchestrator")
    if os.path.exists(ORCHESTRATOR_DIR) and ORCHESTRATOR_DIR not in sys.path:
        sys.path.insert(0, ORCHESTRATOR_DIR)
    from orchestrator import IngestionOrchestrator, CaptureItem  # type: ignore
    HAS_ORCHESTRATOR = True
except Exception as e:  # pragma: no cover - best-effort wiring
    logger.warning(f"Ingestion Orchestrator unavailable: {e}")
    HAS_ORCHESTRATOR = False
    IngestionOrchestrator = None  # type: ignore
    CaptureItem = None  # type: ignore

# Feature flags and telemetry
try:
    from pathlib import Path
    # Add system tools to path for config and platform modules
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "system"))
    from root_finder import find_8825_root, get_8825_paths
    
    # Try to import feature flags
    try:
        from config.feature_flags import is_enabled
    except ImportError:
        def is_enabled(flag: str) -> bool:
            return os.getenv(f"FEATURE_{flag}", "false").lower() == "true"
    
    # Try to import telemetry
    try:
        from platform.telemetry import TelemetryService
        telemetry = TelemetryService()
        HAS_TELEMETRY = True
    except ImportError:
        telemetry = None
        HAS_TELEMETRY = False
except Exception as e:
    logger.warning(f"Feature flags/telemetry unavailable: {e}")
    HAS_TELEMETRY = False
    telemetry = None
    def is_enabled(flag): return os.getenv(f"FEATURE_{flag}", "false").lower() == "true"


app = FastAPI(
    title="Maestra Backend",
    description="Backend service for the Maestra browser extension",
    version="1.0.0"
)

# CORS configuration
# In production, this is handled by the API Gateway
# This is for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for browser extension compatibility
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Middleware
# ============================================================================

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID to all requests."""
    request.state.request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


# ============================================================================
# Endpoints
# ============================================================================

@app.get("/identity")
async def get_backend_identity():
    """
    Backend Identity endpoint.
    Returns cryptographic identity for backend sync protocol.
    """
    identity = get_identity(backend_type="hosted")
    return identity.to_dict()


@app.get("/health")
async def health_check() -> HealthResponse:
    """
    Health check endpoint.
    
    Returns service status, dependency health, and LLM quota usage.
    """
    # Check dependencies
    dependencies = {
        "jh_brain": "unknown",  # Would ping Jh Brain MCP
        "memory_hub": "unknown",  # Would ping Memory Hub MCP
        "deep_research": "unknown"  # Would ping deep-research MCP
    }

    try:
        provider, _ = get_configured_llm_provider()
        dependencies["llm"] = f"configured:{provider}"
    except Exception:
        dependencies["llm"] = "missing"
    
    # Calculate quota usage
    today = date.today()
    daily_calls = llm_call_counter[today]
    quota_usage_pct = (daily_calls / daily_quota * 100) if daily_quota > 0 else 0.0
    
    return HealthResponse(
        status="healthy",
        service="maestra-backend",
        version="1.0.0",
        timestamp=datetime.utcnow(),
        dependencies=dependencies,
        daily_llm_calls=daily_calls,
        daily_quota=daily_quota,
        quota_usage_pct=round(quota_usage_pct, 2)
    )


@app.post("/api/maestra/advisor/ask")
async def advisor_ask(request: AdvisorAskRequest) -> AdvisorAskResponse:
    """
    Ask the Maestra advisor a question.
    
    Modes:
    - quick: Instant response using Jh Brain context and guidance
    - deep: Creates a research job for thorough investigation
    
    Returns the answer, sources, and optional job_id for deep mode.
    Gracefully degrades if dependencies unavailable.
    """
    try:
        response = await ask_advisor(request)
        # Increment LLM call counter
        today = date.today()
        llm_call_counter[today] += 1
        return response
    except LLMConfigurationError as e:
        logger.error(f"Advisor misconfigured (LLM): {e}")
        raise HTTPException(
            status_code=503,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Advisor error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Advisor processing failed"
        )


@app.get("/api/maestra/context/{session_id}")
async def context_summary(session_id: str) -> ContextSummaryResponse:
    """
    Get context summary for a session.
    
    Returns recent decisions, open loops, and topics discussed.
    Gracefully degrades if dependencies unavailable.
    """
    try:
        response = await get_session_context(session_id)
        return response
    except Exception as e:
        logger.error(f"Context error: {e}", exc_info=True)
        # Graceful degradation: return empty context instead of 500
        return ContextSummaryResponse(
            session_id=session_id,
            summary="Context unavailable - services offline",
            key_decisions=[],
            open_loops=[],
            topics_discussed=[],
            last_activity=datetime.utcnow().isoformat()
        )


@app.get("/api/maestra/research/{job_id}")
async def research_status(job_id: str) -> ResearchStatusResponse:
    """
    Get status of a deep research job.
    
    Returns progress, current phase, and summary when complete.
    Gracefully degrades if dependencies unavailable.
    """
    try:
        response = await get_research_status(job_id)
        return response
    except Exception as e:
        logger.error(f"Research status error: {e}", exc_info=True)
        # Graceful degradation: return pending status instead of 500
        return ResearchStatusResponse(
            job_id=job_id,
            status="pending",
            progress=0.0,
            title="Research Job",
            summary="Research unavailable - services offline",
            current_phase=None,
            error=None,
            created_at=datetime.utcnow().isoformat(),
            completed_at=None
        )


# ============================================================================
# Alias Routes (for extension compatibility)
# Extension expects: /advisor/ask, /context/{id}, /research/{id}
# ============================================================================

@app.post("/advisor/ask")
async def advisor_ask_alias(request: AdvisorAskRequest) -> AdvisorAskResponse:
    """Alias for /api/maestra/advisor/ask"""
    return await advisor_ask(request)


@app.get("/context/{session_id}")
async def context_summary_alias(session_id: str) -> ContextSummaryResponse:
    """Alias for /api/maestra/context/{session_id}"""
    return await context_summary(session_id)


@app.get("/research/{job_id}")
async def research_status_alias(job_id: str) -> ResearchStatusResponse:
    """Alias for /api/maestra/research/{job_id}"""
    return await research_status(job_id)


@app.put("/api/maestra/session/{session_id}/capabilities")
async def register_session_capabilities(session_id: str, request: SessionCapabilities) -> SessionInfo:
    """
    Register session capabilities from handshake.
    
    Called by UI after receiving JWT from local companion.
    Verifies JWT and enables advanced features for authenticated sessions.
    """
    logger.info(f"Registering session capabilities: {session_id}")
    
    try:
        # Register session (verifies JWT internally)
        session_info = register_session(
            session_id=session_id,
            library_id=request.library_id,
            jwt_token=request.jwt,
            capabilities=request.capabilities
        )
        
        return session_info
    except Exception as e:
        logger.error(f"Session registration error: {e}", exc_info=True)
        # Return anonymous session on error
        return SessionInfo(
            session_id=session_id,
            status="anonymous",
            library_id=None,
            capabilities_enabled=[],
            authenticated_at=None,
            expires_at=None
        )


@app.get("/api/maestra/session/{session_id}")
async def get_session_info(session_id: str) -> SessionInfo:
    """Get session info (status, capabilities, etc)."""
    return get_session(session_id)


# ============================================================================
# Collaboration Endpoints
# ============================================================================

class TeamJoinRequest(BaseModel):
    """Request to join a team."""
    session_id: str
    team_id: str
    team_name: Optional[str] = None

class DocumentTrackRequest(BaseModel):
    """Request to track a document."""
    team_id: str
    doc_id: str
    title: str
    doc_type: str
    session_id: str
    url: Optional[str] = None
    excerpt: str = ""

@app.post("/api/maestra/team/join")
async def join_team(request: TeamJoinRequest) -> dict:
    """Join a team for collaborative context sharing."""
    try:
        add_session_to_team(request.session_id, request.team_id)
        team = get_or_create_team(request.team_id, request.team_name or "Team")
        
        return {
            "status": "joined",
            "team_id": request.team_id,
            "team_name": team.name,
            "session_id": request.session_id
        }
    except Exception as e:
        logger.error(f"Team join error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/maestra/document/track")
async def track_doc(request: DocumentTrackRequest) -> dict:
    """Track a document being discussed in collaboration."""
    try:
        doc = track_document(
            team_id=request.team_id,
            doc_id=request.doc_id,
            title=request.title,
            doc_type=request.doc_type,
            session_id=request.session_id,
            url=request.url,
            excerpt=request.excerpt
        )
        
        return {
            "status": "tracked",
            "doc_id": doc.doc_id,
            "title": doc.title,
            "mentioned_in_sessions": len(doc.mentioned_in_sessions)
        }
    except Exception as e:
        logger.error(f"Document track error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/maestra/team/context/{session_id}")
async def get_team_context(session_id: str) -> dict:
    """Get team context for a session (shared documents, decisions, etc)."""
    try:
        context = get_team_context_for_session(session_id)
        
        if not context:
            return {
                "team_id": None,
                "team_name": None,
                "active_sessions": 0,
                "documents_count": 0,
                "shared_contexts_count": 0,
                "collaborative_decisions_count": 0,
                "recent_documents": [],
                "shared_context_keys": [],
                "active_decisions": []
            }
        
        return context
    except Exception as e:
        logger.error(f"Team context error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Learning Loop Endpoints
# ============================================================================

class FeedbackRequest(BaseModel):
    """Request to submit feedback."""
    session_id: str
    response_id: str
    feedback_type: str
    rating: int
    comment: str = ""

class QualityScoreRequest(BaseModel):
    """Request to record quality metric."""
    response_id: str
    metric: str
    score: float

@app.post("/api/maestra/feedback")
async def submit_feedback(request: FeedbackRequest) -> dict:
    """Submit feedback on a response."""
    try:
        import uuid
        feedback_id = str(uuid.uuid4())
        
        feedback = record_feedback(
            feedback_id=feedback_id,
            session_id=request.session_id,
            response_id=request.response_id,
            feedback_type=request.feedback_type,
            rating=request.rating,
            comment=request.comment
        )
        
        return {
            "status": "recorded",
            "feedback_id": feedback_id,
            "rating": request.rating,
            "feedback_type": request.feedback_type
        }
    except Exception as e:
        logger.error(f"Feedback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/maestra/quality-score")
async def record_quality(request: QualityScoreRequest) -> dict:
    """Record quality metric for a response."""
    try:
        quality = record_quality_score(
            response_id=request.response_id,
            metric=request.metric,
            score=request.score
        )
        
        return {
            "status": "recorded",
            "metric": request.metric,
            "score": request.score
        }
    except Exception as e:
        logger.error(f"Quality score error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/maestra/analytics/feedback")
async def get_feedback_analytics() -> dict:
    """Get feedback analytics."""
    try:
        return get_feedback_summary()
    except Exception as e:
        logger.error(f"Feedback analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/maestra/analytics/routing")
async def get_routing_analytics() -> dict:
    """Get routing decision accuracy."""
    try:
        return get_routing_accuracy()
    except Exception as e:
        logger.error(f"Routing analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/maestra/analytics/mcp/{mcp_name}")
async def get_mcp_analytics(mcp_name: str) -> dict:
    """Get MCP performance metrics."""
    try:
        return get_mcp_performance(mcp_name)
    except Exception as e:
        logger.error(f"MCP analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/maestra/smart-pdf/export")
async def smart_pdf_export(request: SmartPDFExportRequest) -> SmartPDFExportResponse:
    """
    Export a template as a Smart PDF.
    
    Creates a PDF with embedded 8825 manifest and edge AI configuration.
    Returns download URL for the generated PDF.
    """
    try:
        response = await export_smart_pdf_handler(request)
        return response
    except Exception as e:
        logger.error(f"Smart PDF export error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Smart PDF export error: {str(e)}"
        )


@app.post("/smart-pdf/export")
async def smart_pdf_export_alias(request: SmartPDFExportRequest) -> SmartPDFExportResponse:
    """Alias for /api/maestra/smart-pdf/export"""
    return await smart_pdf_export(request)


@app.post("/api/maestra/smart-pdf/import")
async def smart_pdf_import(request: SmartPDFImportRequest) -> SmartPDFImportResponse:
    """
    Import a Smart PDF back to template.
    
    Extracts manifest and reconstructs template data.
    Returns template data for use in Maestra.
    """
    try:
        response = await import_smart_pdf_handler(request)
        return response
    except Exception as e:
        logger.error(f"Smart PDF import error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Smart PDF import error: {str(e)}"
        )


@app.post("/smart-pdf/import")
async def smart_pdf_import_alias(request: SmartPDFImportRequest) -> SmartPDFImportResponse:
    """Alias for /api/maestra/smart-pdf/import"""
    return await smart_pdf_import(request)

class AssimilateRequest(BaseModel):
    """Request model for assimilation (mirrors Memory Assimilator server)"""
    text: Optional[str] = None
    memory_text: Optional[str] = None
    scope_hint: str = "auto"

    @property
    def resolved_text(self) -> str:
        return (self.text or self.memory_text or "").strip()


@app.post("/assimilate")
async def assimilate(request: AssimilateRequest):
    """Assimilate memory text via internal pipeline.

    The extension and other tools may POST here directly.
    """
    if not HAS_ASSIMILATOR or get_pipeline is None:
        raise HTTPException(status_code=503, detail="Memory Assimilator not available")

    text = request.resolved_text
    if not text:
        raise HTTPException(status_code=400, detail="No text provided (use 'text' or 'memory_text')")

    pipeline = get_pipeline()
    result = await pipeline.assimilate(text)
    return result


@app.post("/api/maestra/capture")
async def capture_content(request: dict):
    """Capture web content from Maestra and run assimilation.

    Expected payload (extension):
      {"session_id", "content", "page_url", "page_title", ...}
    """
    session_id = request.get("session_id") or "maestra"
    content = request.get("content") or request.get("text") or ""
    page_url = request.get("page_url") or ""
    page_title = request.get("page_title") or ""
    content_length = len(content)
    
    # Route capture through Ingestion Orchestrator (if enabled)
    orchestrator_decision = None
    if is_enabled("ORCHESTRATOR_ENABLED"):
        try:
            import asyncio
            
            if HAS_ORCHESTRATOR and IngestionOrchestrator is not None:
                # Create capture item for orchestrator
                capture_item = CaptureItem(
                    capture_id=session_id,
                    content=content,
                    source_surface="maestra",
                    metadata={
                        "url": page_url,
                        "title": page_title,
                        "content_length": content_length
                    }
                )
                
                # Route through orchestrator
                orchestrator = IngestionOrchestrator()
                orchestrator_decision = await orchestrator.route(capture_item)
                
                logger.info(f"📥 Orchestrator routed {session_id}: {orchestrator_decision.intent} (confidence: {orchestrator_decision.confidence:.0%})")
                
                # Send notification if not in shadow mode
                if not is_enabled("ORCHESTRATOR_SHADOW_MODE"):
                    try:
                        from pathlib import Path
                        import sys
                        
                        notifier_path = Path(__file__).parent.parent.parent / "brain" / "capture_router"
                        if str(notifier_path) not in sys.path:
                            sys.path.insert(0, str(notifier_path))
                        
                        from notifier import notify
                        
                        notify(
                            title=f"Capture Routed: {orchestrator_decision.intent.title()}",
                            message=orchestrator_decision.notification,
                            level="success",
                            metadata={
                                "capture_id": session_id,
                                "intent": orchestrator_decision.intent,
                                "confidence": orchestrator_decision.confidence,
                                "conversation_id": orchestrator_decision.conversation_id
                            }
                        )
                    except Exception as notify_error:
                        logger.warning(f"Failed to send notification: {notify_error}")
        
        except Exception as orchestrator_error:
            logger.warning(f"Orchestrator routing failed: {orchestrator_error}")
    
    # Fallback to old router if orchestrator not enabled
    route_decision = None
    if not is_enabled("ORCHESTRATOR_ENABLED") and is_enabled("CAPTURE_ROUTER_ENABLED"):
        try:
            from pathlib import Path
            from datetime import datetime
            import json
            import sys
            
            # Add capture_router to path
            router_path = Path(__file__).parent.parent.parent / "brain" / "capture_router"
            if str(router_path) not in sys.path:
                sys.path.insert(0, str(router_path))
            
            from router import CaptureRouter
            from notifier import notify
            
            # Route the capture
            router = CaptureRouter()
            route_decision = router.route(
                capture_id=session_id,
                content=content,
                metadata={
                    "url": page_url,
                    "title": page_title,
                    "content_length": content_length
                }
            )
            
            # Send notification
            notify(
                title=f"Capture Routed: {route_decision.intent.value.title()}",
                message=route_decision.notification,
                level="success",
                metadata={
                    "capture_id": session_id,
                    "intent": route_decision.intent.value,
                    "confidence": route_decision.confidence,
                    "conversation_id": route_decision.conversation_id
                }
            )
            
            logger.info(f"📥 Routed capture {session_id}: {route_decision.intent.value} (confidence: {route_decision.confidence:.0%})")
            
        except Exception as routing_error:
            logger.warning(f"Routing failed: {routing_error}")
    
    # Save to inbox for monitoring (always, regardless of routing)
    try:
        from pathlib import Path
        from datetime import datetime
        import json
        
        inbox_dir = Path(__file__).parent.parent.parent / "data" / "maestra_inbox"
        inbox_dir.mkdir(parents=True, exist_ok=True)
        
        inbox_item = {
            "id": session_id,
            "timestamp": datetime.now().isoformat() + "Z",
            "source": "maestra_capture",
            "content": content,
            "metadata": {
                "url": page_url,
                "title": page_title,
                "content_length": content_length
            }
        }
        
        # Add route decision if available
        if route_decision:
            inbox_item["route"] = route_decision.to_dict()
        
        inbox_file = inbox_dir / f"{session_id}.json"
        with open(inbox_file, 'w') as f:
            json.dump(inbox_item, f, indent=2)
    
    except Exception as inbox_error:
        logger.warning(f"Failed to save to inbox: {inbox_error}")
    
    # Log capture start
    if HAS_TELEMETRY and telemetry:
        telemetry.log(
            event_type="capture_start",
            service="maestra_capture",
            operation_id=session_id,
            metadata={
                "content_length": content_length,
                "page_url": page_url,
                "page_title": page_title,
            }
        )
    
    try:
        if not content:
            raise HTTPException(status_code=400, detail="No content provided")

        # Clean HTML if content looks like HTML
        if is_enabled("HTML_NOISE_CLEANING") and ('<script' in content or '<style' in content or 'data-' in content):
            try:
                from html_cleaner import HTMLCleaner
                cleaner = HTMLCleaner()
                
                # Estimate reduction
                estimate = cleaner.estimate_reduction(content)
                logger.info(f"HTML cleaning: {estimate['original_size']:,} → {estimate['cleaned_size']:,} chars ({estimate['reduction_percent']:.1f}% reduction)")
                
                # Clean the content
                content = cleaner.clean(content, aggressive=True)
            except Exception as e:
                logger.warning(f"HTML cleaning failed: {e}")
        
        header_parts = []
        if page_title:
            header_parts.append(f"Title: {page_title}")
        if page_url:
            header_parts.append(f"URL: {page_url}")
        header = "\n".join(header_parts)
        memory_text = f"{header}\n\n{content}" if header else content

        assimilation_result = None
        if HAS_ASSIMILATOR and get_pipeline is not None:
            # SAFETY: Check for excessive content length
            MAX_CAPTURE_SIZE = 500_000  # 500k chars max (~60 chunks)
            if len(memory_text) > MAX_CAPTURE_SIZE:
                logger.warning(f"Content too large: {len(memory_text):,} chars (max {MAX_CAPTURE_SIZE:,})")
                assimilation_result = {
                    "success": False,
                    "summary": f"❌ Content too large ({len(memory_text):,} characters, max {MAX_CAPTURE_SIZE:,})\n\n"
                              f"This would require {len(memory_text) // 8000} chunks and cost ~${(len(memory_text) // 8000) * 0.015:.2f} in API calls.\n\n"
                              f"Please use Selection mode to capture specific sections instead of Full Page.",
                    "gate_results": {"gate1": {"error": "too_large", "length": len(memory_text)}},
                    "actions_taken": {},
                }
            # Check if chunking is needed and enabled
            elif len(memory_text) > 10000 and is_enabled("LONG_CAPTURE_CHUNKING"):
                # Import chunking modules
                import sys
                chunker_path = os.path.join(ASSIMILATOR_DIR, "chunker.py")
                reconciler_path = os.path.join(ASSIMILATOR_DIR, "reconciler.py")
                
                if os.path.exists(chunker_path) and os.path.exists(reconciler_path):
                    from chunker import SemanticChunker
                    from reconciler import reconcile_chunks
                    
                    # Chunk the content
                    chunker = SemanticChunker(max_chunk_size=8000, overlap=500)
                    chunks = chunker.chunk(
                        text=content,  # Just content, not header (header added per chunk)
                        metadata={
                            "title": page_title,
                            "url": page_url,
                            "session_id": session_id,
                        }
                    )
                    
                    logger.info(f"Chunking {content_length} chars into {len(chunks)} chunks")
                    
                    # Process chunks in parallel batches
                    import asyncio
                    chunk_results = []
                    pipeline = get_pipeline()
                    
                    BATCH_SIZE = 5  # Process 5 chunks at a time
                    
                    async def process_chunk(chunk):
                        try:
                            result = await pipeline.assimilate(chunk.text)
                            logger.info(f"Chunk {chunk.index} completed successfully")
                            return result
                        except Exception as chunk_error:
                            logger.error(f"Chunk {chunk.index} failed: {chunk_error}", exc_info=True)
                            return {
                                "success": False,
                                "error": str(chunk_error),
                                "gate_results": {},
                                "actions_taken": {}
                            }
                    
                    # Process in batches with better error handling
                    try:
                        for i in range(0, len(chunks), BATCH_SIZE):
                            batch = chunks[i:i + BATCH_SIZE]
                            batch_num = i//BATCH_SIZE + 1
                            total_batches = (len(chunks) + BATCH_SIZE - 1)//BATCH_SIZE
                            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)")
                            
                            # Use gather with return_exceptions to prevent one failure from killing all
                            batch_results = await asyncio.gather(
                                *[process_chunk(chunk) for chunk in batch],
                                return_exceptions=True
                            )
                            
                            # Handle any exceptions that were returned
                            for idx, result in enumerate(batch_results):
                                if isinstance(result, Exception):
                                    logger.error(f"Batch {batch_num} chunk {idx} raised exception: {result}")
                                    chunk_results.append({
                                        "success": False,
                                        "error": str(result),
                                        "gate_results": {},
                                        "actions_taken": {}
                                    })
                                else:
                                    chunk_results.append(result)
                            
                            logger.info(f"Batch {batch_num}/{total_batches} complete")
                        
                        # Reconcile all chunk results
                        assimilation_result = reconcile_chunks(chunk_results)
                    except Exception as batch_error:
                        logger.error(f"Batch processing failed: {batch_error}", exc_info=True)
                        # Fall back to sequential processing
                        logger.warning("Falling back to sequential processing")
                        chunk_results = []
                        for chunk in chunks:
                            try:
                                result = await pipeline.assimilate(chunk.text)
                                chunk_results.append(result)
                            except Exception as e:
                                logger.error(f"Sequential chunk {chunk.index} failed: {e}")
                                chunk_results.append({
                                    "success": False,
                                    "error": str(e),
                                    "gate_results": {},
                                    "actions_taken": {}
                                })
                        assimilation_result = reconcile_chunks(chunk_results)
                    
                    logger.info(f"Reconciled {len(chunks)} chunks: {assimilation_result.get('summary')}")
                else:
                    logger.warning("Chunking enabled but chunker.py/reconciler.py not found")
                    pipeline = get_pipeline()
                    assimilation_result = await pipeline.assimilate(memory_text)
            else:
                # Normal path for short content or chunking disabled
                pipeline = get_pipeline()
                assimilation_result = await pipeline.assimilate(memory_text)
        
        # Log capture complete
        if HAS_TELEMETRY and telemetry:
            gate3 = assimilation_result.get("gate_results", {}).get("gate3_classification", {}) if assimilation_result else {}
            telemetry.log(
                event_type="capture_complete",
                service="maestra_capture",
                operation_id=session_id,
                metadata={
                    "success": assimilation_result.get("success") if assimilation_result else False,
                    "classification": gate3.get("type"),
                    "artifacts_created": len(assimilation_result.get("actions_taken", {})) if assimilation_result else 0,
                    "content_length": content_length,
                    "chunks_processed": assimilation_result.get("chunks_processed", 0) if assimilation_result else 0,
                    "was_chunked": assimilation_result.get("chunks_processed", 0) > 1 if assimilation_result else False,
                }
            )

        return {
            "success": True,
            "session_id": session_id,
            "assimilation": assimilation_result,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Capture error: {e}", exc_info=True)
        
        # Log capture failure
        if HAS_TELEMETRY and telemetry:
            telemetry.log(
                event_type="capture_failed",
                service="maestra_capture",
                operation_id=session_id,
                metadata={
                    "error": str(e),
                    "content_length": content_length,
                }
            )
        
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/maestra/recommend-conversation")
async def recommend_conversation(request: dict):
    """Recommend best conversation based on page context.

    Currently returns a neutral response instructing the extension to
    create a new conversation. Can be enhanced to search Conversation Hub.
    """
    try:
        return {
            "success": True,
            "conversation_id": None,
            "message": "No specific conversation recommended",
            "create_new": True,
        }
    except Exception as e:
        logger.error(f"Recommend conversation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Recommend conversation error: {str(e)}",
        )


# ============================================================================
# Ingestion Orchestrator Endpoint
# ============================================================================

@app.post("/api/orchestrator/ingest")
async def orchestrator_ingest(request: dict):
    """
    Intelligent ingestion orchestration.
    
    Routes captures to appropriate handlers based on intent detection,
    conversation linking, and all available 8825 context.
    
    Expected payload:
      {
        "capture_id": "...",
        "content": "...",
        "source_surface": "chatgpt|claude|windsurf|email|otter",
        "metadata": {
          "url": "...",
          "title": "...",
          "session_id": "...",
          "timestamp": "..."
        }
      }
    """
    if not is_enabled("ORCHESTRATOR_ENABLED"):
        raise HTTPException(
            status_code=503,
            detail="Orchestrator not enabled (set FEATURE_ORCHESTRATOR_ENABLED=true)"
        )
    
    if not HAS_ORCHESTRATOR or IngestionOrchestrator is None:
        raise HTTPException(
            status_code=503,
            detail="Orchestrator not available"
        )
    
    try:
        import asyncio
        
        # Create capture item
        capture_item = CaptureItem(
            capture_id=request.get("capture_id", "unknown"),
            content=request.get("content", ""),
            source_surface=request.get("source_surface", "unknown"),
            metadata=request.get("metadata", {})
        )
        
        # Route through orchestrator
        orchestrator = IngestionOrchestrator()
        decision = await orchestrator.route(capture_item)
        
        # Check shadow mode
        in_shadow_mode = is_enabled("ORCHESTRATOR_SHADOW_MODE")
        
        # Log decision
        logger.info(f"Orchestrator decision: {decision.intent} (confidence: {decision.confidence:.0%})")
        
        # Execute actions if not in shadow mode
        if not in_shadow_mode:
            logger.info(f"Executing actions: {', '.join(decision.actions)}")
            # TODO: Execute actions (update_conversation, create_research_job, etc.)
        else:
            logger.info("Shadow mode: decision logged but not executed")
        
        return {
            "status": "shadow_mode" if in_shadow_mode else "success",
            "route_decision": decision.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Orchestrator error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Orchestrator error: {str(e)}"
        )


# ============================================================================
# Notifications UI Endpoint
# ============================================================================

@app.get("/notifications")
async def notifications_ui():
    """
    Notifications UI for viewing orchestrator routing decisions.
    
    Displays recent routing decisions, notifications, and conversation links
    in a simple web interface.
    """
    try:
        import sys
        from pathlib import Path
        
        # Add orchestrator to path
        orchestrator_path = Path(__file__).parent.parent.parent / "agents" / "ingestion_orchestrator"
        if str(orchestrator_path) not in sys.path:
            sys.path.insert(0, str(orchestrator_path))
        
        from notifications_ui import notifications_page
        
        return await notifications_page()
    
    except Exception as e:
        logger.error(f"Notifications UI error: {e}", exc_info=True)
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content=f"<html><body><h1>Error loading notifications</h1><p>{str(e)}</p></body></html>",
            status_code=500
        )


@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """
    Get conversation details for cross-surface continuation.
    
    Returns conversation context with deep links for continuation
    in any surface (Windsurf, ChatGPT, Claude, etc.)
    """
    try:
        import sys
        from pathlib import Path
        
        # Add orchestrator to path
        orchestrator_path = Path(__file__).parent.parent.parent / "agents" / "ingestion_orchestrator"
        if str(orchestrator_path) not in sys.path:
            sys.path.insert(0, str(orchestrator_path))
        
        from conversation_loader import ConversationLoader
        
        loader = ConversationLoader()
        context = loader.get_conversation_context(conversation_id)
        
        if not context:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return context
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get conversation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load conversation: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8825)
