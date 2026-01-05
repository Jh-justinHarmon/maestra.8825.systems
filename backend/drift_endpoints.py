"""
Drift Detection Endpoints for Maestra Backend.

Handles drift detection, re-consent flows, and Tier 2 disabling.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DriftEvent(BaseModel):
    drift_type: str  # hard or soft
    drift_reason: str
    action_taken: str
    timestamp: str


class ReConsentRequest(BaseModel):
    drift_event: DriftEvent
    consent_given: bool
    timestamp: str


class Tier2DisableRequest(BaseModel):
    reason: str
    drift_event: Optional[DriftEvent] = None
    timestamp: str


class DriftDetectionManager:
    """Manages drift detection and re-consent flows."""
    
    def __init__(self):
        self.session_tier2_status = {}  # session_id -> tier2_enabled
        self.session_drift_history = {}  # session_id -> [drift_events]
        self.session_reconsent_history = {}  # session_id -> [reconsent_events]
    
    def record_drift_event(
        self,
        session_id: str,
        drift_event: DriftEvent
    ) -> bool:
        """
        Record drift event and trigger auto-pause.
        
        Returns True if Tier 2 should be paused.
        """
        if session_id not in self.session_drift_history:
            self.session_drift_history[session_id] = []
        
        self.session_drift_history[session_id].append(drift_event.dict())
        
        logger.warning(
            f"Drift event recorded: session={session_id}, "
            f"type={drift_event.drift_type}, reason={drift_event.drift_reason}"
        )
        
        # Auto-pause Tier 2 on drift
        self.session_tier2_status[session_id] = False
        
        return True
    
    def record_reconsent(
        self,
        session_id: str,
        reconsent_request: ReConsentRequest
    ) -> bool:
        """
        Record user re-consent decision.
        
        Returns True if consent was given, False if Tier 2 disabled.
        """
        if session_id not in self.session_reconsent_history:
            self.session_reconsent_history[session_id] = []
        
        self.session_reconsent_history[session_id].append({
            "consent_given": reconsent_request.consent_given,
            "drift_event": reconsent_request.drift_event.dict() if reconsent_request.drift_event else None,
            "timestamp": reconsent_request.timestamp
        })
        
        # Update Tier 2 status based on consent
        self.session_tier2_status[session_id] = reconsent_request.consent_given
        
        logger.info(
            f"Re-consent recorded: session={session_id}, "
            f"consent_given={reconsent_request.consent_given}"
        )
        
        return reconsent_request.consent_given
    
    def disable_tier2(
        self,
        session_id: str,
        disable_request: Tier2DisableRequest
    ) -> bool:
        """Disable Tier 2 for session."""
        self.session_tier2_status[session_id] = False
        
        logger.info(
            f"Tier 2 disabled: session={session_id}, reason={disable_request.reason}"
        )
        
        return True
    
    def is_tier2_enabled(self, session_id: str) -> bool:
        """Check if Tier 2 is enabled for session."""
        return self.session_tier2_status.get(session_id, True)
    
    def get_drift_history(self, session_id: str) -> list:
        """Get drift history for session."""
        return self.session_drift_history.get(session_id, [])
    
    def get_reconsent_history(self, session_id: str) -> list:
        """Get re-consent history for session."""
        return self.session_reconsent_history.get(session_id, [])


# Global drift manager
drift_manager = DriftDetectionManager()


def setup_drift_endpoints(app: FastAPI):
    """Setup drift detection endpoints on FastAPI app."""
    
    @app.post("/api/maestra/session/{session_id}/drift-event")
    async def record_drift_event(
        session_id: str,
        drift_event: DriftEvent
    ) -> Dict[str, Any]:
        """
        Record drift event.
        
        Triggers auto-pause of Tier 2 data access.
        """
        try:
            drift_manager.record_drift_event(session_id, drift_event)
            
            return {
                "session_id": session_id,
                "drift_event": drift_event.dict(),
                "action": "auto_paused_tier2",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to record drift event: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/maestra/session/{session_id}/reconsent")
    async def reconsent(
        session_id: str,
        request: ReConsentRequest
    ) -> Dict[str, Any]:
        """
        Record user re-consent decision.
        
        Called when user responds to re-consent dialog.
        """
        try:
            consent_given = drift_manager.record_reconsent(session_id, request)
            
            return {
                "session_id": session_id,
                "consent_given": consent_given,
                "tier2_enabled": consent_given,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to record re-consent: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/maestra/session/{session_id}/tier2-disable")
    async def disable_tier2(
        session_id: str,
        request: Tier2DisableRequest
    ) -> Dict[str, Any]:
        """
        Disable Tier 2 for session.
        
        Called when user chooses to disable raw data access.
        """
        try:
            drift_manager.disable_tier2(session_id, request)
            
            return {
                "session_id": session_id,
                "tier2_enabled": False,
                "reason": request.reason,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to disable Tier 2: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/maestra/session/{session_id}/tier2-status")
    async def get_tier2_status(session_id: str) -> Dict[str, Any]:
        """Get Tier 2 status for session."""
        return {
            "session_id": session_id,
            "tier2_enabled": drift_manager.is_tier2_enabled(session_id),
            "drift_history": drift_manager.get_drift_history(session_id),
            "reconsent_history": drift_manager.get_reconsent_history(session_id),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @app.get("/api/maestra/session/{session_id}/drift-history")
    async def get_drift_history(session_id: str) -> Dict[str, Any]:
        """Get drift history for session."""
        return {
            "session_id": session_id,
            "drift_events": drift_manager.get_drift_history(session_id),
            "timestamp": datetime.utcnow().isoformat()
        }
