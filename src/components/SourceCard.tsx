import React from 'react';
import { BookOpen } from 'lucide-react';

/**
 * SourceCard Component
 * 
 * Displays a citation card for library entries and other sources used in answers
 * Shows entry title, source, confidence, and entry ID
 */

export interface SourceCardProps {
  title: string;
  entryId?: string;
  source?: string;
  confidence?: number;
  type?: 'library' | 'context' | 'conversation' | 'routing';
  excerpt?: string;
}

export const SourceCard: React.FC<SourceCardProps> = ({
  title,
  entryId,
  source,
  confidence = 0.9,
  type = 'library',
  excerpt,
}) => {
  const getIcon = () => {
    switch (type) {
      case 'library':
        return <BookOpen className="h-4 w-4" />;
      case 'context':
        return <span className="text-sm">📊</span>;
      case 'conversation':
        return <span className="text-sm">💬</span>;
      case 'routing':
        return <span className="text-sm">🔀</span>;
      default:
        return <BookOpen className="h-4 w-4" />;
    }
  };

  const getTypeColor = () => {
    switch (type) {
      case 'library':
        return 'bg-blue-50 border-blue-200';
      case 'context':
        return 'bg-green-50 border-green-200';
      case 'conversation':
        return 'bg-purple-50 border-purple-200';
      case 'routing':
        return 'bg-orange-50 border-orange-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  const getTextColor = () => {
    switch (type) {
      case 'library':
        return 'text-blue-900';
      case 'context':
        return 'text-green-900';
      case 'conversation':
        return 'text-purple-900';
      case 'routing':
        return 'text-orange-900';
      default:
        return 'text-gray-900';
    }
  };

  return (
    <div className={`border rounded-lg p-3 my-2 ${getTypeColor()}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2 flex-1">
          <div className={`mt-0.5 ${getTextColor()}`}>
            {getIcon()}
          </div>
          <div className="flex-1 min-w-0">
            <div className={`text-sm font-semibold ${getTextColor()}`}>
              {title}
            </div>
            {source && (
              <div className={`text-xs ${getTextColor()} opacity-75 mt-0.5`}>
                Source: {source}
              </div>
            )}
            {excerpt && (
              <div className={`text-xs ${getTextColor()} opacity-70 mt-1 line-clamp-2`}>
                {excerpt}
              </div>
            )}
          </div>
        </div>
        {confidence !== undefined && (
          <div className={`text-xs font-medium ${getTextColor()} whitespace-nowrap`}>
            {Math.round(confidence * 100)}%
          </div>
        )}
      </div>
      {entryId && (
        <div className={`text-xs ${getTextColor()} opacity-60 mt-2 font-mono`}>
          ID: {entryId}
        </div>
      )}
    </div>
  );
};

export default SourceCard;
