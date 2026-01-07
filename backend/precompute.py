"""
Precompute Orchestrator Backend

Endpoint: POST /api/precompute
Receives raw user text, runs PromptGen + context gathering, returns optimized prompt.

Architecture:
- Receives raw text from frontend
- Gathers context from library/memory
- Runs PromptGen agent
- Returns structured result with model recommendation + cost estimate
"""

import asyncio
import json
import logging
from dataclasses import asdict
from pathlib import Path
import sys
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

# Add root finder to path - find 8825_core in workspace
workspace_root = Path(__file__).parent.parent.parent.parent
# Look for 8825_core in users/justin_harmon/8825-Jh/
core_root = workspace_root / "users" / "justin_harmon" / "8825-Jh" / "8825_core"

if not core_root.exists():
    # Fallback: look in workspace root
    core_root = workspace_root / "8825_core"

sys.path.insert(0, str(core_root / "system"))
sys.path.insert(0, str(core_root))
sys.path.insert(0, str(Path(__file__).parent))

try:
    from root_finder import find_8825_root, get_8825_paths
except ImportError:
    # If still not found, create minimal stubs
    def find_8825_root():
        return str(workspace_root)
    def get_8825_paths():
        return {"8825_CORE": str(core_root)}

# Import PromptGen agent
try:
    from agents.prompt_gen import PromptGenAgent, PromptGenResult
except ImportError:
    # Fallback if import fails
    PromptGenAgent = None
    PromptGenResult = None

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/precompute", tags=["precompute"])

# Initialize PromptGen agent
_agent: Optional[PromptGenAgent] = None


def get_agent() -> PromptGenAgent:
    """Get or initialize PromptGen agent."""
    global _agent
    if _agent is None:
        if PromptGenAgent is None:
            raise RuntimeError("PromptGenAgent not available")
        _agent = PromptGenAgent()
    return _agent


# Request/Response models
class PrecomputeRequest(BaseModel):
    """Request to precompute a prompt."""
    text: str


class PrecomputeResponse(BaseModel):
    """Response with precomputed prompt and metadata."""
    optimized_prompt: str
    context_refs: list[str]
    recommended_model: str
    cost_estimate: str
    confidence: float
    intent: Optional[str] = None
    entities: Optional[list[str]] = None


@router.post("")
async def precompute(request: PrecomputeRequest) -> PrecomputeResponse:
    """
    Precompute optimized prompt from raw text.
    
    Called by frontend during typing (500ms debounce).
    Returns optimized prompt + context + model recommendation.
    
    Args:
        request: PrecomputeRequest with raw text
    
    Returns:
        PrecomputeResponse with optimized prompt and metadata
    
    Raises:
        HTTPException: If precompute fails
    """
    try:
        if not request.text or len(request.text) < 5:
            raise HTTPException(
                status_code=400,
                detail="Text too short for precompute"
            )
        
        logger.info(f"Precompute request: {len(request.text)} chars")
        
        # Get agent
        agent = get_agent()
        
        # Run precompute with context gathering
        result = await agent.refine_with_context(
            raw_text=request.text,
            gather_context=True
        )
        
        logger.info(
            f"Precompute complete: intent={result.intent}, "
            f"model={result.recommended_model}, confidence={result.confidence:.2f}"
        )
        
        # Convert to response
        return PrecomputeResponse(
            optimized_prompt=result.optimized_prompt,
            context_refs=result.context_refs,
            recommended_model=result.recommended_model,
            cost_estimate=result.cost_estimate,
            confidence=result.confidence,
            intent=result.intent,
            entities=result.entities,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Precompute error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Precompute failed: {str(e)}"
        )


@router.get("/health")
async def health() -> Dict[str, Any]:
    """Health check for precompute service."""
    try:
        agent = get_agent()
        return {
            "status": "healthy",
            "agent": "ready",
            "model": agent.local_model,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }


@router.post("/test")
async def test(request: PrecomputeRequest) -> Dict[str, Any]:
    """
    Test endpoint for precompute.
    
    Useful for debugging and testing without full integration.
    """
    try:
        agent = get_agent()
        
        # Run without context gathering for speed
        result = await agent.refine(
            raw_text=request.text,
            context=None
        )
        
        return {
            "success": True,
            "input": request.text,
            "intent": result.intent,
            "confidence": result.confidence,
            "model": result.recommended_model,
            "cost": result.cost_estimate,
            "prompt_length": len(result.optimized_prompt),
        }
    
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


def setup_precompute_routes(app):
    """
    Setup precompute routes on FastAPI app.
    
    Usage in main app:
    from backend.precompute import setup_precompute_routes
    setup_precompute_routes(app)
    """
    app.include_router(router)
    logger.info("Precompute routes registered")
