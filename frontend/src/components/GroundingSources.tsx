import React, { useState } from 'react';
import { ChevronDown, ChevronUp, ExternalLink, BookOpen, Database, Zap } from 'lucide-react';

export interface GroundingSource {
  type: 'library' | 'memory_hub' | 'client_context' | 'api' | 'other';
  identifier: string;
  title: string;
  confidence: number;
  excerpt?: string;
  timestamp?: string;
  url?: string;
}

interface GroundingSourcesProps {
  sources: GroundingSource[];
  expanded?: boolean;
}

/**
 * GroundingSources - Display the sources that grounded an answer
 * 
 * Shows:
 * - Source type (library, memory hub, API, etc.)
 * - Source title and identifier
 * - Confidence score
 * - Excerpt or preview
 * - Timestamp when available
 */
export const GroundingSources: React.FC<GroundingSourcesProps> = ({
  sources,
  expanded: initialExpanded = false,
}) => {
  const [expanded, setExpanded] = useState(initialExpanded);

  if (!sources || sources.length === 0) {
    return null;
  }

  const getSourceIcon = (type: string) => {
    switch (type) {
      case 'library':
        return <BookOpen className="w-4 h-4" />;
      case 'memory_hub':
        return <Database className="w-4 h-4" />;
      case 'api':
        return <Zap className="w-4 h-4" />;
      default:
        return <ExternalLink className="w-4 h-4" />;
    }
  };

  const getSourceColor = (type: string) => {
    switch (type) {
      case 'library':
        return 'bg-blue-50 border-blue-200';
      case 'memory_hub':
        return 'bg-purple-50 border-purple-200';
      case 'api':
        return 'bg-orange-50 border-orange-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  const getSourceLabel = (type: string) => {
    switch (type) {
      case 'library':
        return '8825 Library';
      case 'memory_hub':
        return 'Memory Hub';
      case 'client_context':
        return 'Client Context';
      case 'api':
        return 'External API';
      default:
        return 'Source';
    }
  };

  return (
    <div className="mt-4 border border-gray-200 rounded-lg bg-white">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-gray-700">
            Grounding Sources ({sources.length})
          </span>
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-gray-500" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-500" />
        )}
      </button>

      {expanded && (
        <div className="border-t border-gray-200 divide-y divide-gray-200">
          {sources.map((source, index) => (
            <div
              key={index}
              className={`p-4 ${getSourceColor(source.type)} border-l-4 ${
                source.type === 'library'
                  ? 'border-l-blue-400'
                  : source.type === 'memory_hub'
                  ? 'border-l-purple-400'
                  : source.type === 'api'
                  ? 'border-l-orange-400'
                  : 'border-l-gray-400'
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 flex-1">
                  <div className="mt-1 text-gray-600">
                    {getSourceIcon(source.type)}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-gray-600 uppercase">
                        {getSourceLabel(source.type)}
                      </span>
                      <span className="text-xs text-gray-500">
                        {source.identifier}
                      </span>
                    </div>
                    <h4 className="font-semibold text-gray-900 mt-1">
                      {source.title}
                    </h4>
                    {source.excerpt && (
                      <p className="text-sm text-gray-700 mt-2 line-clamp-2">
                        {source.excerpt}
                      </p>
                    )}
                    {source.timestamp && (
                      <p className="text-xs text-gray-500 mt-2">
                        {new Date(source.timestamp).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <div className="flex items-center gap-1">
                    <span className="text-xs font-semibold text-gray-600">
                      Confidence
                    </span>
                    <span className="text-sm font-bold text-gray-900">
                      {Math.round(source.confidence * 100)}%
                    </span>
                  </div>
                  {source.url && (
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
                    >
                      View
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
