"""
Hosted Brain Router for Quad-Core Handshake.

Runs in Maestra backend, accepts signed manifests from local authority service.
Routes tasks to cloud tools or delegates to local execution via capability sidecar.

Endpoints:
  POST /api/v1/capability-delegation - Establish capability delegation
  POST /api/v1/execute - Execute capability (local or cloud)
  GET /api/v1/session/{session_id}/audit - Get audit trail
"""

import json
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import sys
import httpx

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage for session overlays (production: use Redis)
session_overlays = {}  # session_id -> overlay_data
execution_history = {}  # session_id -> [receipts]


# ============================================================================
# Pydantic Models
# ============================================================================

class DelegationPolicy(BaseModel):
    tier: int = Field(ge=0, le=2)
    allowlist: List[Dict[str, Any]] = []
    rate_limit: Optional[Dict[str, int]] = None
    redaction_rules: Optional[List[Dict[str, str]]] = None


class DelegationToken(BaseModel):
    token_id: str
    manifest_id: str
    capability_id: str
    session_id: str
    subject: str
    issued_at: str
    expires_at: str
    policy: DelegationPolicy
    nonce: str
    signature: str


class Tier2Grant(BaseModel):
    grant_id: str
    token_id: str
    session_id: str
    issued_at: str
    expires_at: str
    byte_budget: int
    bytes_used: int = 0
    consent_given_at: Optional[str] = None
    consent_context: Optional[Dict[str, Any]] = None
    signature: str


class CapabilityDelegationRequest(BaseModel):
    session_id: str
    capabilities_requested: List[str]
    tier_preference: int = Field(default=0, ge=0, le=2)


class CapabilityDelegationResponse(BaseModel):
    session_id: str
    tokens: List[DelegationToken]
    tier2_grant: Optional[Tier2Grant] = None
    timestamp: str


class ExecuteRequest(BaseModel):
    session_id: str
    capability_id: str
    token: DelegationToken
    input_params: Dict[str, Any]
    execute_locally: bool = False  # If True, delegate to local sidecar


class ExecutionReceipt(BaseModel):
    receipt_id: str
    token_id: str
    session_id: str
    capability_id: str
    executed_at: str
    executed_by: str
    status: str
    input_hash: str
    output_hash: str
    bytes_returned: int
    error_message: Optional[str] = None
    drift_detected: bool = False
    drift_reason: Optional[str] = None


class SessionOverlay(BaseModel):
    session_id: str
    created_at: str
    tokens: List[DelegationToken] = []
    tier2_grant: Optional[Tier2Grant] = None
    drift_state: Dict[str, Any] = {}
    execution_count: int = 0


# ============================================================================
# Brain Router
# ============================================================================

class BrainRouter:
    """Routes capability requests to local or cloud execution."""
    
    def __init__(self, local_sidecar_url: str = "http://127.0.0.1:5160"):
        self.local_sidecar_url = local_sidecar_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def establish_delegation(
        self,
        session_id: str,
        capabilities_requested: List[str],
        tier_preference: int
    ) -> CapabilityDelegationResponse:
        """
        Establish capability delegation with local authority service.
        
        Calls local sidecar /handshake endpoint to get tokens.
        """
        logger.info(
            f"Establishing delegation: session={session_id}, "
            f"capabilities={capabilities_requested}, tier={tier_preference}"
        )
        
        try:
            # Call local sidecar
            response = await self.client.post(
                f"{self.local_sidecar_url}/handshake",
                json={
                    "session_id": session_id,
                    "manifest_id": str(uuid.uuid4()),
                    "capabilities_requested": capabilities_requested,
                    "tier_preference": tier_preference
                }
            )
            
            if response.status_code != 200:
                raise ValueError(f"Sidecar error: {response.text}")
            
            data = response.json()
            
            # Create session overlay
            overlay = SessionOverlay(
                session_id=session_id,
                created_at=datetime.utcnow().isoformat(),
                tokens=[DelegationToken(**t) for t in data.get("tokens", [])],
                tier2_grant=Tier2Grant(**data["tier2_grant"]) if data.get("tier2_grant") else None
            )
            session_overlays[session_id] = overlay
            execution_history[session_id] = []
            
            logger.info(f"Delegation established: session={session_id}")
            
            return CapabilityDelegationResponse(
                session_id=session_id,
                tokens=overlay.tokens,
                tier2_grant=overlay.tier2_grant,
                timestamp=datetime.utcnow().isoformat()
            )
        
        except Exception as e:
            logger.error(f"Delegation error: {e}", exc_info=True)
            raise
    
    async def execute(
        self,
        session_id: str,
        capability_id: str,
        token: DelegationToken,
        input_params: Dict[str, Any],
        execute_locally: bool = False
    ) -> ExecutionReceipt:
        """
        Execute capability (local or cloud).
        
        If execute_locally=True, delegates to local sidecar.
        Otherwise, executes cloud tool (mock for now).
        """
        logger.info(
            f"Execute request: session={session_id}, capability={capability_id}, "
            f"local={execute_locally}"
        )
        
        try:
            if execute_locally:
                return await self._execute_locally(
                    session_id, capability_id, token, input_params
                )
            else:
                return await self._execute_cloud(
                    session_id, capability_id, token, input_params
                )
        
        except Exception as e:
            logger.error(f"Execution error: {e}", exc_info=True)
            receipt = ExecutionReceipt(
                receipt_id=str(uuid.uuid4()),
                token_id=token.token_id,
                session_id=session_id,
                capability_id=capability_id,
                executed_at=datetime.utcnow().isoformat(),
                executed_by="brain_router",
                status="failure",
                input_hash="",
                output_hash="",
                bytes_returned=0,
                error_message=str(e)
            )
            self._record_execution(session_id, receipt)
            raise
    
    async def _execute_locally(
        self,
        session_id: str,
        capability_id: str,
        token: DelegationToken,
        input_params: Dict[str, Any]
    ) -> ExecutionReceipt:
        """Delegate execution to local sidecar."""
        logger.info(f"Delegating to local sidecar: {capability_id}")
        
        try:
            response = await self.client.post(
                f"{self.local_sidecar_url}/execute",
                json={
                    "token": token.dict(),
                    "session_id": session_id,
                    "input_params": input_params
                }
            )
            
            if response.status_code != 200:
                raise ValueError(f"Sidecar error: {response.text}")
            
            receipt_data = response.json()
            receipt = ExecutionReceipt(**receipt_data)
            
            self._record_execution(session_id, receipt)
            logger.info(f"Local execution complete: {receipt.receipt_id}")
            
            return receipt
        
        except Exception as e:
            logger.error(f"Local execution error: {e}")
            raise
    
    async def _execute_cloud(
        self,
        session_id: str,
        capability_id: str,
        token: DelegationToken,
        input_params: Dict[str, Any]
    ) -> ExecutionReceipt:
        """Execute cloud tool (mock implementation)."""
        logger.info(f"Executing cloud tool: {capability_id}")
        
        # Mock cloud execution
        receipt = ExecutionReceipt(
            receipt_id=str(uuid.uuid4()),
            token_id=token.token_id,
            session_id=session_id,
            capability_id=capability_id,
            executed_at=datetime.utcnow().isoformat(),
            executed_by="brain_router_cloud",
            status="success",
            input_hash=self._hash_data(json.dumps(input_params)),
            output_hash=self._hash_data(json.dumps({"result": "cloud_execution"})),
            bytes_returned=50
        )
        
        self._record_execution(session_id, receipt)
        logger.info(f"Cloud execution complete: {receipt.receipt_id}")
        
        return receipt
    
    def _record_execution(self, session_id: str, receipt: ExecutionReceipt):
        """Record execution in history."""
        if session_id not in execution_history:
            execution_history[session_id] = []
        execution_history[session_id].append(receipt)
    
    def _hash_data(self, data: str) -> str:
        """Hash data with SHA256."""
        import hashlib
        return hashlib.sha256(data.encode()).hexdigest()
    
    def get_session_overlay(self, session_id: str) -> Optional[SessionOverlay]:
        """Get session overlay."""
        return session_overlays.get(session_id)
    
    def get_execution_history(self, session_id: str) -> List[ExecutionReceipt]:
        """Get execution history for session."""
        return execution_history.get(session_id, [])


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(title="Brain Router", version="1.0.0")
router = BrainRouter()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "brain_router",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/v1/capability-delegation")
async def capability_delegation(
    request: CapabilityDelegationRequest
) -> CapabilityDelegationResponse:
    """
    Establish capability delegation.
    
    Calls local authority service to get delegation tokens.
    """
    try:
        return await router.establish_delegation(
            session_id=request.session_id,
            capabilities_requested=request.capabilities_requested,
            tier_preference=request.tier_preference
        )
    except Exception as e:
        logger.error(f"Delegation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/execute")
async def execute(request: ExecuteRequest) -> ExecutionReceipt:
    """
    Execute capability.
    
    Routes to local sidecar or cloud tool based on execute_locally flag.
    """
    try:
        return await router.execute(
            session_id=request.session_id,
            capability_id=request.capability_id,
            token=request.token,
            input_params=request.input_params,
            execute_locally=request.execute_locally
        )
    except Exception as e:
        logger.error(f"Execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/session/{session_id}/overlay")
async def get_session_overlay(session_id: str) -> Dict[str, Any]:
    """Get session overlay."""
    overlay = router.get_session_overlay(session_id)
    if not overlay:
        raise HTTPException(status_code=404, detail="Session not found")
    return overlay.dict()


@app.get("/api/v1/session/{session_id}/audit")
async def get_audit_trail(session_id: str) -> Dict[str, Any]:
    """Get execution audit trail for session."""
    history = router.get_execution_history(session_id)
    return {
        "session_id": session_id,
        "execution_count": len(history),
        "executions": [h.dict() for h in history],
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
