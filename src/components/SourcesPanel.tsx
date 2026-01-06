import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { SourceCard, SourceCardProps } from './SourceCard';

/**
 * SourcesPanel Component
 * 
 * Collapsible panel showing all sources used in the current answer
 * Displays library entries, context, conversation history, and routing info
 */

export interface SourcesPanelProps {
  sources: SourceCardProps[];
  className?: string;
}

export const SourcesPanel: React.FC<SourcesPanelProps> = ({
  sources,
  className = '',
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!sources || sources.length === 0) {
    return null;
  }

  const libraryEntries = sources.filter(s => s.type === 'library');
  const otherSources = sources.filter(s => s.type !== 'library');

  return (
    <div className={`mt-4 border-t border-zinc-700 pt-3 ${className}`}>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-xs font-medium text-zinc-400 hover:text-zinc-300 transition-colors"
      >
        {isExpanded ? (
          <ChevronUp size={14} />
        ) : (
          <ChevronDown size={14} />
        )}
        <span>Sources ({sources.length})</span>
      </button>

      {isExpanded && (
        <div className="mt-3 space-y-2">
          {/* Library Entries Section */}
          {libraryEntries.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-zinc-400 mb-2">
                📚 Library Entries ({libraryEntries.length})
              </div>
              <div className="space-y-1 ml-2">
                {libraryEntries.map((source, idx) => (
                  <SourceCard key={`lib-${idx}`} {...source} />
                ))}
              </div>
            </div>
          )}

          {/* Other Sources Section */}
          {otherSources.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-zinc-400 mb-2">
                📌 Other Sources ({otherSources.length})
              </div>
              <div className="space-y-1 ml-2">
                {otherSources.map((source, idx) => (
                  <SourceCard key={`other-${idx}`} {...source} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SourcesPanel;
