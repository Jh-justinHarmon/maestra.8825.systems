"""
Maestra Backend - Research Logic

Handles /research/{job_id} endpoint logic.
Interfaces with deep-research MCP for job status and reports.
"""
import os
import sys
import logging
import time
import uuid
from typing import Optional
from datetime import datetime

# Add parent paths for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import ResearchStatusResponse

logger = logging.getLogger(__name__)

# In-memory job cache for demo purposes
# In production, this would query the deep-research MCP
_job_cache = {}


async def get_research_status_from_mcp(job_id: str) -> Optional[dict]:
    """
    Get research job status from deep-research MCP.
    
    In production, this calls mcp3_research_status.
    """
    # Simulated response - in production, call deep-research MCP
    # This would be: result = await research_status(job_id=job_id)
    
    # Check cache first
    if job_id in _job_cache:
        return _job_cache[job_id]
    
    # Simulate a job that doesn't exist
    return None


async def get_research_report_from_mcp(job_id: str) -> Optional[str]:
    """
    Get research report from deep-research MCP.
    
    In production, this calls mcp3_research_get_report.
    """
    # Simulated response - in production, call deep-research MCP
    # This would be: result = await research_get_report(job_id=job_id)
    
    return f"Research report for job {job_id}:\n\n[Full report would be here]"


def register_job(job_id: str, target: str) -> None:
    """
    Register a new research job in the cache.
    Called when a deep research job is created.
    """
    _job_cache[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0.0,
        "title": target,
        "created_at": datetime.utcnow().isoformat(),
        "current_phase": "Initializing research job"
    }
    logger.info(f"Registered research job: {job_id}")


def update_job_status(job_id: str, status: str, progress: float, phase: str = None) -> None:
    """
    Update a research job's status.
    Called by the research worker as it progresses.
    """
    if job_id in _job_cache:
        _job_cache[job_id]["status"] = status
        _job_cache[job_id]["progress"] = progress
        if phase:
            _job_cache[job_id]["current_phase"] = phase
        if status == "done":
            _job_cache[job_id]["completed_at"] = datetime.utcnow().isoformat()
        logger.info(f"Updated job {job_id}: status={status}, progress={progress}")


async def get_research_status(job_id: str) -> ResearchStatusResponse:
    """
    Get the status of a research job.
    
    If the job is done, includes the summary.
    """
    logger.info(f"Getting research status for job: {job_id}")
    
    # Try to get status from MCP
    status_data = await get_research_status_from_mcp(job_id)
    
    if not status_data:
        # Job not found
        return ResearchStatusResponse(
            job_id=job_id,
            status="failed",
            progress=0.0,
            error="Job not found"
        )
    
    # Parse status data
    status = status_data.get("status", "pending")
    progress = status_data.get("progress", 0.0)
    title = status_data.get("title")
    current_phase = status_data.get("current_phase")
    error = status_data.get("error")
    
    # Get summary if done
    summary = None
    if status == "done":
        summary = await get_research_report_from_mcp(job_id)
    
    # Parse timestamps
    created_at = None
    completed_at = None
    if "created_at" in status_data:
        try:
            created_at = datetime.fromisoformat(status_data["created_at"])
        except:
            pass
    if "completed_at" in status_data:
        try:
            completed_at = datetime.fromisoformat(status_data["completed_at"])
        except:
            pass
    
    return ResearchStatusResponse(
        job_id=job_id,
        status=status,
        progress=progress,
        title=title,
        summary=summary,
        current_phase=current_phase,
        error=error,
        created_at=created_at,
        completed_at=completed_at
    )
