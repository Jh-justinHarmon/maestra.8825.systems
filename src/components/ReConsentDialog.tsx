import React, { useState } from 'react';

// Feature flag: ReConsentDialog requires shadcn/ui components
// Temporarily disabled while shadcn/ui is being configured
// Re-enable by setting FEATURE_CONSENT_UI = true and installing dependencies
const FEATURE_CONSENT_UI = false;

export interface DriftEvent {
  drift_type: 'hard' | 'soft';
  drift_reason: string;
  action_taken: string;
  timestamp: string;
}

export interface ReConsentDialogProps {
  isOpen: boolean;
  driftEvent: DriftEvent | null;
  sessionId: string;
  onConsent: (tier2Enabled: boolean) => void;
  onCancel: () => void;
}

/**
 * ReConsentDialog - Data access level change confirmation
 * 
 * FEATURE FLAG: FEATURE_CONSENT_UI
 * Status: Disabled (awaiting shadcn/ui setup)
 * 
 * When enabled, this component will:
 * - Detect hard/soft drift in conversation context
 * - Prompt user to re-consent to Tier 2 (raw) data access
 * - Record consent decision to backend
 * 
 * TODO: Re-enable when shadcn/ui components are available
 */
export const ReConsentDialog: React.FC<ReConsentDialogProps> = ({
  isOpen: _isOpen,
  driftEvent,
  sessionId,
  onConsent,
  onCancel: _onCancel,
}) => {
  const [isLoading, setIsLoading] = useState(false);

  // Feature flag check - return null if disabled
  if (!FEATURE_CONSENT_UI) {
    // Suppress unused variable warnings for enabled version
    void isLoading;
    return null;
  }

  if (!driftEvent) {
    return null;
  }

  const handleConsent = async () => {
    setIsLoading(true);
    try {
      await fetch(`/api/maestra/session/${sessionId}/reconsent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          drift_event: driftEvent,
          consent_given: true,
          timestamp: new Date().toISOString(),
        }),
      });
      onConsent(true);
    } catch (error) {
      console.error('Failed to record consent:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDisableTier2 = async () => {
    setIsLoading(true);
    try {
      await fetch(`/api/maestra/session/${sessionId}/tier2-disable`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reason: 'user_disabled_after_drift',
          drift_event: driftEvent,
          timestamp: new Date().toISOString(),
        }),
      });
      onConsent(false);
    } catch (error) {
      console.error('Failed to disable Tier 2:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Placeholder return when feature is disabled
  // All parameters and handlers are used in the enabled version
  void handleConsent;
  void handleDisableTier2;
  
  return null;
};

export default ReConsentDialog;
