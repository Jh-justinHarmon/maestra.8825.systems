import { useState } from 'react';
import { ChevronDown, ChevronUp, Copy, Trash2 } from 'lucide-react';
import { breadcrumbTrail } from '../lib/breadcrumbs';

interface BreadcrumbPanelProps {
  isOpen: boolean;
  onToggle: () => void;
}

export function BreadcrumbPanel({ isOpen, onToggle }: BreadcrumbPanelProps) {
  const [copied, setCopied] = useState(false);
  const trail = breadcrumbTrail.getLastN(10);

  const copyToClipboard = () => {
    const json = breadcrumbTrail.exportAsJSON();
    navigator.clipboard.writeText(json);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const clearTrail = () => {
    breadcrumbTrail.clear();
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'source':
        return 'bg-blue-900/30 text-blue-300 border-blue-700';
      case 'tool':
        return 'bg-purple-900/30 text-purple-300 border-purple-700';
      case 'context':
        return 'bg-cyan-900/30 text-cyan-300 border-cyan-700';
      case 'result':
        return 'bg-green-900/30 text-green-300 border-green-700';
      case 'error':
        return 'bg-red-900/30 text-red-300 border-red-700';
      default:
        return 'bg-zinc-800 text-zinc-300 border-zinc-700';
    }
  };

  const formatDuration = (ms?: number) => {
    if (!ms) return '';
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-zinc-950 border-t border-zinc-800 z-40">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-4 py-2 hover:bg-zinc-900 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-zinc-300">Execution Trail</span>
          <span className="text-xs text-zinc-500">({trail.length} entries)</span>
        </div>
        {isOpen ? (
          <ChevronDown size={16} className="text-zinc-400" />
        ) : (
          <ChevronUp size={16} className="text-zinc-400" />
        )}
      </button>

      {isOpen && (
        <div className="max-h-64 overflow-y-auto border-t border-zinc-800">
          <div className="p-4 space-y-4">
            {trail.length === 0 ? (
              <p className="text-xs text-zinc-500">No execution history yet</p>
            ) : (
              trail.map((execution) => (
                <div key={execution.messageId} className="space-y-2">
                  <div className="text-xs font-medium text-zinc-400">
                    <span className="text-zinc-500">Message:</span> {execution.userInput.substring(0, 50)}
                    {execution.userInput.length > 50 ? '...' : ''}
                  </div>
                  <div className="space-y-1 ml-2">
                    {execution.entries.map((entry) => (
                      <div
                        key={entry.id}
                        className={`text-xs p-2 rounded border ${getTypeColor(entry.type)}`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1">
                            <span className="font-medium">{entry.label}</span>
                            {entry.duration && (
                              <span className="text-zinc-500 ml-2">
                                ({formatDuration(entry.duration)})
                              </span>
                            )}
                            {entry.details && (
                              <div className="text-zinc-400 mt-1 max-h-20 overflow-hidden">
                                <pre className="text-xs whitespace-pre-wrap break-words">
                                  {JSON.stringify(entry.details, null, 2)}
                                </pre>
                              </div>
                            )}
                          </div>
                          <span className="text-zinc-600 text-xs whitespace-nowrap">
                            {new Date(entry.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                  {execution.totalDuration && (
                    <div className="text-xs text-zinc-500 ml-2">
                      Total: {formatDuration(execution.totalDuration)}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          <div className="flex gap-2 p-4 border-t border-zinc-800">
            <button
              onClick={copyToClipboard}
              className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-sm rounded transition-colors"
            >
              <Copy size={14} />
              {copied ? 'Copied!' : 'Export JSON'}
            </button>
            <button
              onClick={clearTrail}
              className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-sm rounded transition-colors"
            >
              <Trash2 size={14} />
              Clear
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
