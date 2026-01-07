import React from 'react';
import { EpistemicBadge, EpistemicState } from './EpistemicBadge';
import { GroundingSources, GroundingSource } from './GroundingSources';
import { AlertCircle, Info } from 'lucide-react';

export interface AdvisorResponseData {
  answer: string;
  epistemic_state: EpistemicState;
  grounding_sources: GroundingSource[];
  confidence: number;
  trace_id: string;
  processing_time_ms: number;
}

interface AdvisorResponseProps {
  response: AdvisorResponseData;
  loading?: boolean;
  error?: string;
}

/**
 * AdvisorResponse - Display advisor answer with epistemic integrity
 * 
 * Shows:
 * - Epistemic badge (grounded/ungrounded/refused)
 * - Main answer text
 * - Grounding sources (if available)
 * - Confidence score
 * - Processing time
 * - Trace ID for debugging
 */
export const AdvisorResponse: React.FC<AdvisorResponseProps> = ({
  response,
  loading = false,
  error,
}) => {
  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
          <div>
            <h3 className="font-semibold text-red-900">Error</h3>
            <p className="text-sm text-red-800 mt-1">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <div className="flex items-center gap-3">
          <div className="w-4 h-4 bg-blue-600 rounded-full animate-pulse" />
          <span className="text-sm text-gray-600">Thinking...</span>
        </div>
      </div>
    );
  }

  if (!response) {
    return null;
  }

  const isRefused = response.epistemic_state === 'refused';
  const isUngrounded = response.epistemic_state === 'ungrounded';
  const isGrounded = response.epistemic_state === 'grounded';

  return (
    <div className="space-y-4">
      {/* Epistemic State Badge */}
      <div className="flex items-center justify-between">
        <EpistemicBadge
          state={response.epistemic_state}
          confidence={response.confidence}
        />
        <div className="text-xs text-gray-500">
          {response.processing_time_ms}ms
        </div>
      </div>

      {/* Warning for Refused/Ungrounded */}
      {isRefused && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-red-800">
            This question cannot be answered with the available context. 
            Consider providing more specific information or context.
          </p>
        </div>
      )}

      {isUngrounded && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 flex items-start gap-2">
          <Info className="w-4 h-4 text-yellow-600 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-yellow-800">
            This answer is speculative and not based on verified sources. 
            Use with caution and verify important information independently.
          </p>
        </div>
      )}

      {isGrounded && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3 flex items-start gap-2">
          <Info className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-green-800">
            This answer is grounded in verified sources with{' '}
            <strong>{Math.round(response.confidence * 100)}% confidence</strong>.
          </p>
        </div>
      )}

      {/* Answer Text */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <p className="text-gray-900 leading-relaxed whitespace-pre-wrap">
          {response.answer}
        </p>
      </div>

      {/* Grounding Sources */}
      {response.grounding_sources && response.grounding_sources.length > 0 && (
        <GroundingSources
          sources={response.grounding_sources}
          expanded={isGrounded}
        />
      )}

      {/* Debug Info */}
      <details className="text-xs text-gray-500">
        <summary className="cursor-pointer hover:text-gray-700">
          Debug Info
        </summary>
        <div className="mt-2 bg-gray-50 rounded p-2 font-mono text-gray-600">
          <div>Trace ID: {response.trace_id}</div>
          <div>Confidence: {response.confidence.toFixed(2)}</div>
          <div>Sources: {response.grounding_sources?.length || 0}</div>
        </div>
      </details>
    </div>
  );
};
