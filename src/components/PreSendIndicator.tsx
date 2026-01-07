/**
 * PreSendIndicator Component
 * 
 * Shows precompute status before user sends message.
 * Displays: context ready, cost forecast, model selected, optimization status.
 */

import { Loader2, CheckCircle2, AlertCircle, Zap } from 'lucide-react';
import { PrecomputeState, usePrecomputeStatus } from '../hooks/useTypingIntelligence';

interface PreSendIndicatorProps {
  state: PrecomputeState;
  className?: string;
}

export function PreSendIndicator({ state, className = '' }: PreSendIndicatorProps) {
  const status = usePrecomputeStatus(state);

  // Don't show if no text or precompute not started
  if (!state.rawText || (!state.isPrecomputing && !state.precomputeResult)) {
    return null;
  }

  return (
    <div className={`space-y-2 text-sm ${className}`}>
      {/* Loading state */}
      {state.isPrecomputing && (
        <div className="flex items-center gap-2 text-blue-600">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span>Optimizing prompt...</span>
        </div>
      )}

      {/* Ready state */}
      {status.isReady && (
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-green-600">
            <CheckCircle2 className="w-4 h-4" />
            <span>Precompute ready</span>
          </div>

          {/* Context info */}
          {status.contextCount > 0 && (
            <div className="flex items-center gap-2 text-gray-600 ml-6">
              <span className="text-xs">
                📚 {status.contextCount} context doc{status.contextCount !== 1 ? 's' : ''}
              </span>
            </div>
          )}

          {/* Cost forecast */}
          <div className="flex items-center gap-2 text-gray-600 ml-6">
            <Zap className="w-3 h-3" />
            <span className="text-xs">
              Est. cost: <span className="font-mono">{status.costForecast}</span>
            </span>
          </div>

          {/* Model info */}
          {status.model && (
            <div className="flex items-center gap-2 text-gray-600 ml-6">
              <span className="text-xs">
                🤖 {status.model}
              </span>
            </div>
          )}

          {/* Intent info */}
          {status.intent && (
            <div className="flex items-center gap-2 text-gray-600 ml-6">
              <span className="text-xs capitalize">
                Intent: {status.intent}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Error state */}
      {state.error && (
        <div className="flex items-center gap-2 text-amber-600">
          <AlertCircle className="w-4 h-4" />
          <span className="text-xs">{state.error}</span>
        </div>
      )}

      {/* Fallback info */}
      {state.precomputeResult && state.precomputeResult.confidence <= 0.7 && (
        <div className="flex items-center gap-2 text-gray-500">
          <AlertCircle className="w-4 h-4" />
          <span className="text-xs">Low confidence - will use raw prompt</span>
        </div>
      )}
    </div>
  );
}

/**
 * CostBadge Component
 * 
 * Color-coded cost indicator.
 * Green: free, Amber: cheap, Orange: moderate, Red: expensive
 */
interface CostBadgeProps {
  cost: string;
  className?: string;
}

export function CostBadge({ cost, className = '' }: CostBadgeProps) {
  // Parse cost string to number
  const costValue = parseFloat(cost.replace('$', ''));

  let bgColor = 'bg-green-100 text-green-800';
  let label = 'Free';

  if (costValue === 0) {
    bgColor = 'bg-green-100 text-green-800';
    label = 'Free';
  } else if (costValue <= 0.01) {
    bgColor = 'bg-amber-100 text-amber-800';
    label = 'Cheap';
  } else if (costValue <= 0.05) {
    bgColor = 'bg-orange-100 text-orange-800';
    label = 'Moderate';
  } else {
    bgColor = 'bg-red-100 text-red-800';
    label = 'Expensive';
  }

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium ${bgColor} ${className}`}>
      <Zap className="w-3 h-3" />
      {label} ({cost})
    </span>
  );
}

/**
 * ProvenanceTooltip Component
 * 
 * Shows where answer came from (model, context, cost).
 */
interface ProvenanceTooltipProps {
  source: string;
  model: string;
  contextDocs: string[];
  cost: string;
  className?: string;
}

export function ProvenanceTooltip({
  source,
  model,
  contextDocs,
  cost,
  className = '',
}: ProvenanceTooltipProps) {
  return (
    <div className={`text-xs space-y-1 p-2 bg-gray-50 rounded border border-gray-200 ${className}`}>
      <div>
        <span className="font-semibold">Source:</span> {source}
      </div>
      <div>
        <span className="font-semibold">Model:</span> {model}
      </div>
      {contextDocs.length > 0 && (
        <div>
          <span className="font-semibold">Context:</span> {contextDocs.length} doc
          {contextDocs.length !== 1 ? 's' : ''}
        </div>
      )}
      <div>
        <span className="font-semibold">Cost:</span> {cost}
      </div>
    </div>
  );
}
