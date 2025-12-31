"""
Maestra Backend - Pydantic Models

Request/Response models for the Maestra API.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime


# ============================================================================
# Advisor Models
# ============================================================================

class AdvisorAskRequest(BaseModel):
    """Request to ask the Maestra advisor a question."""
    session_id: str = Field(default="default", description="Session identifier for context continuity")
    user_id: str = Field(default="anonymous", description="User identifier")
    question: Optional[str] = Field(None, description="The question to ask (legacy field)")
    message: Optional[str] = Field(None, description="The question to ask (new field)")
    mode: Literal["quick", "deep"] = Field(default="quick", description="Response mode: quick (instant) or deep (research)")
    context_hints: List[str] = Field(default_factory=list, description="Optional hints to guide context retrieval")
    client_context: Optional[dict] = Field(
        default=None,
        description="Optional client-provided context payload (e.g., local companion summary, selection, relevant IDs)"
    )
    
    @property
    def get_question(self) -> str:
        """Get the question from either field."""
        return self.message or self.question or ""


class SourceReference(BaseModel):
    """A source reference for an answer."""
    title: str
    type: str  # knowledge, decision, pattern, protocol, external
    confidence: float = 1.0
    excerpt: Optional[str] = None
    url: Optional[str] = None


class AdvisorAskResponse(BaseModel):
    """Response from the Maestra advisor."""
    schema_version: str = Field(default="1", description="API schema version")
    answer: str = Field(..., description="The advisor's answer")
    session_id: str = Field(..., description="Session ID for follow-up questions")
    job_id: Optional[str] = Field(None, description="Research job ID if mode=deep")
    sources: List[SourceReference] = Field(default_factory=list, description="Sources used to generate the answer")
    trace_id: str = Field(..., description="Unique trace ID for debugging")
    mode: str = Field(..., description="Mode used: quick or deep")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")


# ============================================================================
# Context Models
# ============================================================================

class ContextSummaryResponse(BaseModel):
    """Summary of a session's context."""
    session_id: str
    summary: str = Field(..., description="Natural language summary of the session")
    key_decisions: List[str] = Field(default_factory=list, description="Key decisions made in this session")
    open_loops: List[str] = Field(default_factory=list, description="Unresolved items or questions")
    topics_discussed: List[str] = Field(default_factory=list, description="Main topics covered")
    last_activity: Optional[datetime] = None


# ============================================================================
# Research Models
# ============================================================================

class ResearchStatusResponse(BaseModel):
    """Status of a deep research job."""
    job_id: str
    status: Literal["pending", "planning", "discovery", "deep_dive", "synthesis", "done", "failed"]
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress from 0.0 to 1.0")
    title: Optional[str] = Field(None, description="Research title")
    summary: Optional[str] = Field(None, description="Final summary (when done)")
    current_phase: Optional[str] = Field(None, description="Current phase description")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ============================================================================
# Smart PDF Models
# ============================================================================

class SmartPDFExportRequest(BaseModel):
    """Request to export a template as Smart PDF."""
    template_data: dict = Field(..., description="Template data including fields, sections, metadata")
    output_filename: str = Field(..., description="Desired output filename (without path)")
    edge_config: Optional[dict] = Field(None, description="Optional edge AI configuration")
    create_library_entry: bool = Field(default=True, description="Whether to create Library entry")


class SmartPDFExportResponse(BaseModel):
    """Response from Smart PDF export."""
    success: bool
    pdf_id: str = Field(..., description="Generated PDF ID")
    download_url: str = Field(..., description="URL to download the PDF")
    file_size_bytes: int
    manifest_version: str
    library_entry_id: Optional[str] = None
    trace_id: str = Field(..., description="Unique trace ID for debugging")


class SmartPDFImportRequest(BaseModel):
    """Request to import a Smart PDF."""
    pdf_url: str = Field(..., description="URL or path to Smart PDF file")
    validate_schema: bool = Field(default=True, description="Whether to validate manifest schema")
    create_library_entry: bool = Field(default=True, description="Whether to create Library entry")


class SmartPDFImportResponse(BaseModel):
    """Response from Smart PDF import."""
    success: bool
    template_data: dict = Field(..., description="Reconstructed template data")
    pdf_id: str = Field(..., description="PDF ID from manifest")
    manifest_version: str
    library_entry_id: Optional[str] = None
    imported_at: str = Field(..., description="ISO 8601 timestamp")
    trace_id: str = Field(..., description="Unique trace ID for debugging")


# ============================================================================
# Health Models
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
    timestamp: datetime
    dependencies: dict = Field(default_factory=dict, description="Status of dependent services")
    daily_llm_calls: Optional[int] = Field(None, description="Number of LLM calls today")
    daily_quota: Optional[int] = Field(None, description="Daily LLM call quota")
    quota_usage_pct: Optional[float] = Field(None, description="Percentage of daily quota used")
