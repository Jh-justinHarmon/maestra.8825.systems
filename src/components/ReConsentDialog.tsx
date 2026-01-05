import React, { useState } from 'react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { AlertTriangle, CheckCircle, XCircle } from 'lucide-react';

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

export const ReConsentDialog: React.FC<ReConsentDialogProps> = ({
  isOpen,
  driftEvent,
  sessionId,
  onConsent,
  onCancel,
}) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleConsent = async () => {
    setIsLoading(true);
    try {
      // Call backend to record re-consent
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
      // Call backend to disable Tier 2 for this session
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

  if (!driftEvent) {
    return null;
  }

  const isDriftHard = driftEvent.drift_type === 'hard';
  const driftTitle = isDriftHard
    ? 'Data Access Level Changed'
    : 'Topic Change Detected';

  const driftDescription = isDriftHard
    ? `We detected that the conversation is now requesting raw data access (Tier 2). This is a significant change from the initial context. Do you want to allow this?`
    : `We detected that the conversation topic has shifted significantly. This may affect what data we can access. Do you want to continue with raw data access (Tier 2)?`;

  const driftExplanation = isDriftHard
    ? 'Hard drift: Your conversation is escalating to request raw, unredacted data. This is a security checkpoint to ensure you intentionally want this level of access.'
    : 'Soft drift: Your conversation topic has changed. We want to make sure you still want raw data access for this new context.';

  return (
    <AlertDialog open={isOpen} onOpenChange={(open) => !open && onCancel()}>
      <AlertDialogContent className="max-w-md">
        <AlertDialogHeader>
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-600" />
            <AlertDialogTitle>{driftTitle}</AlertDialogTitle>
          </div>
          <AlertDialogDescription className="mt-2">
            {driftDescription}
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div className="bg-amber-50 border border-amber-200 rounded-md p-3 my-4">
          <p className="text-sm text-amber-900">{driftExplanation}</p>
          <p className="text-xs text-amber-700 mt-2">
            Drift reason: <code className="bg-amber-100 px-1 rounded">{driftEvent.drift_reason}</code>
          </p>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-md p-3 my-4">
          <p className="text-sm font-medium text-blue-900 mb-2">What happens next?</p>
          <ul className="text-sm text-blue-800 space-y-1">
            <li className="flex items-start gap-2">
              <CheckCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <span>If you consent: Raw data will be accessible for 15 minutes, then auto-deleted</span>
            </li>
            <li className="flex items-start gap-2">
              <XCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <span>If you decline: Only redacted data will be available for the rest of this session</span>
            </li>
          </ul>
        </div>

        <div className="flex gap-3 justify-end">
          <AlertDialogCancel asChild>
            <Button
              variant="outline"
              onClick={handleDisableTier2}
              disabled={isLoading}
            >
              Disable Raw Data
            </Button>
          </AlertDialogCancel>
          <AlertDialogAction asChild>
            <Button
              onClick={handleConsent}
              disabled={isLoading}
              className="bg-amber-600 hover:bg-amber-700"
            >
              {isLoading ? 'Processing...' : 'Allow Raw Data'}
            </Button>
          </AlertDialogAction>
        </div>

        <p className="text-xs text-gray-500 text-center mt-4">
          Session ID: <code className="bg-gray-100 px-1 rounded">{sessionId.slice(0, 8)}...</code>
        </p>
      </AlertDialogContent>
    </AlertDialog>
  );
};

export default ReConsentDialog;
