import React from 'react';
import { AlertCircle, CheckCircle, HelpCircle } from 'lucide-react';

export type EpistemicState = 'grounded' | 'ungrounded' | 'refused';

interface EpistemicBadgeProps {
  state: EpistemicState;
  confidence?: number;
  compact?: boolean;
}

/**
 * EpistemicBadge - Visual indicator of answer grounding status
 * 
 * Shows whether an answer is:
 * - GROUNDED: Based on verified sources
 * - UNGROUNDED: Speculative, not based on verified sources
 * - REFUSED: Cannot answer due to missing required context
 */
export const EpistemicBadge: React.FC<EpistemicBadgeProps> = ({
  state,
  confidence = 0.5,
  compact = false,
}) => {
  const getIcon = () => {
    switch (state) {
      case 'grounded':
        return <CheckCircle className="w-4 h-4" />;
      case 'ungrounded':
        return <HelpCircle className="w-4 h-4" />;
      case 'refused':
        return <AlertCircle className="w-4 h-4" />;
    }
  };

  const getColors = () => {
    switch (state) {
      case 'grounded':
        return 'bg-green-100 text-green-800 border-green-300';
      case 'ungrounded':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'refused':
        return 'bg-red-100 text-red-800 border-red-300';
    }
  };

  const getLabel = () => {
    switch (state) {
      case 'grounded':
        return 'Grounded';
      case 'ungrounded':
        return 'Speculative';
      case 'refused':
        return 'Cannot Answer';
    }
  };

  const getTooltip = () => {
    switch (state) {
      case 'grounded':
        return `Based on verified sources (${Math.round(confidence * 100)}% confidence)`;
      case 'ungrounded':
        return 'Not based on verified sources - this is speculative';
      case 'refused':
        return 'Cannot answer - required context is missing';
    }
  };

  if (compact) {
    return (
      <div
        className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border ${getColors()}`}
        title={getTooltip()}
      >
        {getIcon()}
        <span>{getLabel()}</span>
      </div>
    );
  }

  return (
    <div
      className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium border ${getColors()}`}
      title={getTooltip()}
    >
      {getIcon()}
      <div className="flex flex-col">
        <span>{getLabel()}</span>
        {state === 'grounded' && (
          <span className="text-xs opacity-75">
            Confidence: {Math.round(confidence * 100)}%
          </span>
        )}
      </div>
    </div>
  );
};
